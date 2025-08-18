"""
Cron expression parser for the MCLI scheduler

Supports standard cron expressions with some extensions:
- Standard: minute hour day month weekday
- Extensions: @yearly, @monthly, @weekly, @daily, @hourly
- Special: @reboot (run at scheduler start)
"""

import re
from datetime import datetime, timedelta
from typing import List, Optional, Set

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class CronParseError(Exception):
    """Exception raised when cron expression cannot be parsed"""

    pass


class CronExpression:
    """Parser and calculator for cron expressions"""

    # Predefined cron shortcuts
    SHORTCUTS = {
        "@yearly": "0 0 1 1 *",
        "@annually": "0 0 1 1 *",
        "@monthly": "0 0 1 * *",
        "@weekly": "0 0 * * 0",
        "@daily": "0 0 * * *",
        "@midnight": "0 0 * * *",
        "@hourly": "0 * * * *",
        "@reboot": "@reboot",  # Special case
    }

    def __init__(self, expression: str):
        self.original_expression = expression.strip()
        self.expression = self._normalize_expression(expression)
        self.is_reboot = self.expression == "@reboot"

        if not self.is_reboot:
            self.fields = self._parse_expression()
            self._validate_fields()

    def _normalize_expression(self, expression: str) -> str:
        """Convert shortcuts to standard cron format"""
        expression = expression.strip().lower()

        if expression in self.SHORTCUTS:
            return self.SHORTCUTS[expression]

        return expression

    def _parse_expression(self) -> List[Set[int]]:
        """Parse cron expression into field sets"""
        if self.is_reboot:
            return []

        parts = self.expression.split()
        if len(parts) != 5:
            raise CronParseError(f"Invalid cron expression: expected 5 fields, got {len(parts)}")

        fields = []
        ranges = [
            (0, 59),  # minute
            (0, 23),  # hour
            (1, 31),  # day
            (1, 12),  # month
            (0, 6),  # weekday (0=Sunday)
        ]

        for i, (part, (min_val, max_val)) in enumerate(zip(parts, ranges)):
            field_values = self._parse_field(part, min_val, max_val)
            fields.append(field_values)

        return fields

    def _parse_field(self, field: str, min_val: int, max_val: int) -> Set[int]:
        """Parse a single cron field"""
        if field == "*":
            return set(range(min_val, max_val + 1))

        values = set()

        # Handle comma-separated values
        for part in field.split(","):
            part = part.strip()

            if "/" in part:
                # Handle step values (e.g., */5, 10-20/2)
                range_part, step_part = part.split("/", 1)
                step = int(step_part)

                if range_part == "*":
                    start, end = min_val, max_val
                elif "-" in range_part:
                    start, end = map(int, range_part.split("-", 1))
                else:
                    start = end = int(range_part)

                values.update(range(start, end + 1, step))

            elif "-" in part:
                # Handle ranges (e.g., 1-5)
                start, end = map(int, part.split("-", 1))
                values.update(range(start, end + 1))

            else:
                # Handle single values
                values.add(int(part))

        # Validate values are within range
        for value in values:
            if not (min_val <= value <= max_val):
                raise CronParseError(f"Value {value} out of range [{min_val}, {max_val}]")

        return values

    def _validate_fields(self):
        """Validate parsed cron fields"""
        if len(self.fields) != 5:
            raise CronParseError("Invalid number of parsed fields")

    def get_next_run_time(self, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """Calculate the next time this cron expression should run"""
        if self.is_reboot:
            return None  # @reboot jobs run only at scheduler start

        if from_time is None:
            from_time = datetime.now()

        # Start from the next minute to avoid immediate execution
        next_time = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Search for the next valid time (with safety limit)
        max_iterations = 366 * 24 * 60  # One year worth of minutes
        iterations = 0

        while iterations < max_iterations:
            if self._matches_time(next_time):
                return next_time

            next_time += timedelta(minutes=1)
            iterations += 1

        logger.warning(f"Could not find next run time for cron expression: {self.expression}")
        return None

    def _matches_time(self, dt: datetime) -> bool:
        """Check if datetime matches this cron expression"""
        if self.is_reboot:
            return False

        minute, hour, day, month, weekday = self.fields

        return (
            dt.minute in minute
            and dt.hour in hour
            and dt.day in day
            and dt.month in month
            and dt.weekday() + 1 % 7 in weekday  # Convert Python weekday to cron weekday
        )

    def matches_now(self) -> bool:
        """Check if cron expression matches current time"""
        return self._matches_time(datetime.now())

    def get_description(self) -> str:
        """Get human-readable description of cron expression"""
        if self.is_reboot:
            return "Run at scheduler startup"

        # Basic descriptions for common patterns
        if self.expression == "0 0 * * *":
            return "Run daily at midnight"
        elif self.expression == "0 * * * *":
            return "Run every hour"
        elif self.expression == "*/5 * * * *":
            return "Run every 5 minutes"
        elif self.expression == "0 0 * * 0":
            return "Run weekly on Sunday at midnight"
        elif self.expression == "0 0 1 * *":
            return "Run monthly on the 1st at midnight"
        elif self.expression == "0 0 1 1 *":
            return "Run yearly on January 1st at midnight"
        else:
            return f"Custom schedule: {self.original_expression}"

    def is_valid(self) -> bool:
        """Check if cron expression is valid"""
        try:
            if self.is_reboot:
                return True
            return len(self.fields) == 5
        except:
            return False

    def __str__(self) -> str:
        return self.original_expression

    def __repr__(self) -> str:
        return f"CronExpression('{self.original_expression}')"


def validate_cron_expression(expression: str) -> bool:
    """Validate a cron expression without creating a full object"""
    try:
        cron = CronExpression(expression)
        return cron.is_valid()
    except:
        return False


def get_next_run_times(expression: str, count: int = 5) -> List[datetime]:
    """Get the next N run times for a cron expression"""
    try:
        cron = CronExpression(expression)
        if cron.is_reboot:
            return []

        times = []
        current_time = datetime.now()

        for _ in range(count):
            next_time = cron.get_next_run_time(current_time)
            if next_time is None:
                break
            times.append(next_time)
            current_time = next_time

        return times
    except Exception as e:
        logger.error(f"Error getting next run times: {e}")
        return []
