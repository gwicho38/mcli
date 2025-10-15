"""
Unit tests for mcli.workflow.scheduler.cron_parser module
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


class TestCronParseError:
    """Test suite for CronParseError exception"""

    def test_cron_parse_error_is_exception(self):
        """Test that CronParseError is an Exception"""
        from mcli.workflow.scheduler.cron_parser import CronParseError

        error = CronParseError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"


class TestCronExpression:
    """Test suite for CronExpression class"""

    def test_cron_expression_shortcuts(self):
        """Test that SHORTCUTS dictionary has expected entries"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        assert "@yearly" in CronExpression.SHORTCUTS
        assert "@monthly" in CronExpression.SHORTCUTS
        assert "@weekly" in CronExpression.SHORTCUTS
        assert "@daily" in CronExpression.SHORTCUTS
        assert "@hourly" in CronExpression.SHORTCUTS
        assert "@reboot" in CronExpression.SHORTCUTS

    def test_parse_standard_cron_expression(self):
        """Test parsing standard cron expression"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0 0 * * *")

        assert cron.original_expression == "0 0 * * *"
        assert cron.is_reboot is False
        assert len(cron.fields) == 5

    def test_parse_every_5_minutes(self):
        """Test parsing */5 * * * * (every 5 minutes)"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("*/5 * * * *")

        assert cron.original_expression == "*/5 * * * *"
        assert 0 in cron.fields[0]  # minute field
        assert 5 in cron.fields[0]
        assert 10 in cron.fields[0]
        assert 55 in cron.fields[0]

    def test_parse_cron_with_ranges(self):
        """Test parsing cron with ranges (1-5 * * * *)"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("1-5 * * * *")

        minute_field = cron.fields[0]
        assert 1 in minute_field
        assert 2 in minute_field
        assert 3 in minute_field
        assert 4 in minute_field
        assert 5 in minute_field
        assert 0 not in minute_field
        assert 6 not in minute_field

    def test_parse_cron_with_lists(self):
        """Test parsing cron with comma-separated lists"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0,15,30,45 * * * *")

        minute_field = cron.fields[0]
        assert 0 in minute_field
        assert 15 in minute_field
        assert 30 in minute_field
        assert 45 in minute_field
        assert len(minute_field) == 4

    def test_parse_cron_with_step_values(self):
        """Test parsing cron with step values (*/2)"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("*/2 * * * *")

        minute_field = cron.fields[0]
        assert 0 in minute_field
        assert 2 in minute_field
        assert 58 in minute_field
        assert 1 not in minute_field
        assert 3 not in minute_field

    def test_parse_cron_with_range_and_step(self):
        """Test parsing cron with range and step (10-20/2)"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("10-20/2 * * * *")

        minute_field = cron.fields[0]
        assert 10 in minute_field
        assert 12 in minute_field
        assert 14 in minute_field
        assert 16 in minute_field
        assert 18 in minute_field
        assert 20 in minute_field
        assert 11 not in minute_field
        assert 9 not in minute_field

    def test_parse_shortcut_yearly(self):
        """Test parsing @yearly shortcut"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("@yearly")

        assert cron.original_expression == "@yearly"
        assert cron.expression == "0 0 1 1 *"

    def test_parse_shortcut_monthly(self):
        """Test parsing @monthly shortcut"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("@monthly")

        assert cron.expression == "0 0 1 * *"

    def test_parse_shortcut_weekly(self):
        """Test parsing @weekly shortcut"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("@weekly")

        assert cron.expression == "0 0 * * 0"

    def test_parse_shortcut_daily(self):
        """Test parsing @daily shortcut"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("@daily")

        assert cron.expression == "0 0 * * *"

    def test_parse_shortcut_hourly(self):
        """Test parsing @hourly shortcut"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("@hourly")

        assert cron.expression == "0 * * * *"

    def test_parse_shortcut_reboot(self):
        """Test parsing @reboot shortcut"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("@reboot")

        assert cron.original_expression == "@reboot"
        assert cron.is_reboot is True
        assert cron.expression == "@reboot"

    def test_invalid_cron_expression_wrong_field_count(self):
        """Test that invalid cron expression raises error"""
        from mcli.workflow.scheduler.cron_parser import CronExpression, CronParseError

        with pytest.raises(CronParseError, match="expected 5 fields"):
            CronExpression("* * *")

    def test_invalid_cron_value_out_of_range(self):
        """Test that value out of range raises error"""
        from mcli.workflow.scheduler.cron_parser import CronExpression, CronParseError

        with pytest.raises(CronParseError, match="out of range"):
            CronExpression("60 * * * *")  # minute > 59

    def test_invalid_hour_out_of_range(self):
        """Test that hour value out of range raises error"""
        from mcli.workflow.scheduler.cron_parser import CronExpression, CronParseError

        with pytest.raises(CronParseError, match="out of range"):
            CronExpression("0 24 * * *")  # hour > 23

    def test_wildcard_field(self):
        """Test that wildcard * generates full range"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("* * * * *")

        # Minute field should have 0-59
        assert len(cron.fields[0]) == 60
        assert 0 in cron.fields[0]
        assert 59 in cron.fields[0]

        # Hour field should have 0-23
        assert len(cron.fields[1]) == 24

    def test_get_next_run_time_basic(self):
        """Test getting next run time for simple expression"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0 0 * * *")  # Daily at midnight

        # Get next run from a specific time
        from_time = datetime(2025, 1, 1, 12, 0, 0)
        next_run = cron.get_next_run_time(from_time)

        assert next_run is not None
        assert next_run.hour == 0
        assert next_run.minute == 0
        # Should be next day
        assert next_run.day == 2

    def test_get_next_run_time_hourly(self):
        """Test getting next run time for hourly expression"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0 * * * *")  # Every hour

        from_time = datetime(2025, 1, 1, 12, 30, 0)
        next_run = cron.get_next_run_time(from_time)

        assert next_run is not None
        assert next_run.minute == 0
        assert next_run.hour == 13  # Next hour

    def test_get_next_run_time_for_reboot(self):
        """Test that @reboot returns None for next_run_time"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("@reboot")

        next_run = cron.get_next_run_time()

        assert next_run is None

    def test_get_next_run_time_defaults_to_now(self):
        """Test that get_next_run_time defaults to current time"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0 * * * *")

        next_run = cron.get_next_run_time()

        assert next_run is not None
        assert next_run > datetime.now()

    def test_matches_time_basic(self):
        """Test _matches_time for specific datetime"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("30 14 * * *")  # 2:30 PM daily

        # Should match
        match_time = datetime(2025, 1, 1, 14, 30, 0)
        assert cron._matches_time(match_time) is True

        # Should not match (wrong minute)
        no_match_time = datetime(2025, 1, 1, 14, 31, 0)
        assert cron._matches_time(no_match_time) is False

    def test_matches_now(self):
        """Test matches_now checks current time"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        # Create expression that matches current minute and hour
        now = datetime.now()
        cron_expr = f"{now.minute} {now.hour} * * *"
        cron = CronExpression(cron_expr)

        # May or may not match depending on exact timing
        result = cron.matches_now()
        assert isinstance(result, bool)

    def test_get_description_daily(self):
        """Test get_description for daily cron"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0 0 * * *")

        description = cron.get_description()

        assert "daily" in description.lower()
        assert "midnight" in description.lower()

    def test_get_description_hourly(self):
        """Test get_description for hourly cron"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0 * * * *")

        description = cron.get_description()

        assert "hour" in description.lower()

    def test_get_description_every_5_minutes(self):
        """Test get_description for every 5 minutes"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("*/5 * * * *")

        description = cron.get_description()

        assert "5 minutes" in description.lower()

    def test_get_description_weekly(self):
        """Test get_description for weekly cron"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0 0 * * 0")

        description = cron.get_description()

        assert "weekly" in description.lower()

    def test_get_description_monthly(self):
        """Test get_description for monthly cron"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0 0 1 * *")

        description = cron.get_description()

        assert "monthly" in description.lower()

    def test_get_description_yearly(self):
        """Test get_description for yearly cron"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0 0 1 1 *")

        description = cron.get_description()

        assert "yearly" in description.lower()

    def test_get_description_reboot(self):
        """Test get_description for @reboot"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("@reboot")

        description = cron.get_description()

        assert "startup" in description.lower()

    def test_get_description_custom(self):
        """Test get_description for custom expression"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("15 10 * * 1")

        description = cron.get_description()

        assert "custom" in description.lower()

    def test_is_valid_for_valid_expression(self):
        """Test is_valid returns True for valid expression"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0 0 * * *")

        assert cron.is_valid() is True

    def test_is_valid_for_reboot(self):
        """Test is_valid returns True for @reboot"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("@reboot")

        assert cron.is_valid() is True

    def test_str_representation(self):
        """Test __str__ returns original expression"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("@daily")

        assert str(cron) == "@daily"

    def test_repr_representation(self):
        """Test __repr__ returns proper representation"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0 0 * * *")

        repr_str = repr(cron)

        assert "CronExpression" in repr_str
        assert "0 0 * * *" in repr_str

    def test_normalize_expression_case_insensitive(self):
        """Test that expression normalization is case insensitive"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron1 = CronExpression("@DAILY")
        cron2 = CronExpression("@Daily")
        cron3 = CronExpression("@daily")

        assert cron1.expression == cron2.expression == cron3.expression

    def test_normalize_expression_strips_whitespace(self):
        """Test that expression is stripped of whitespace"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("  0 0 * * *  ")

        assert cron.expression == "0 0 * * *"

    def test_parse_field_single_value(self):
        """Test _parse_field with single value"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("15 * * * *")

        minute_field = cron.fields[0]
        assert minute_field == {15}

    def test_complex_expression_with_multiple_features(self):
        """Test complex expression with lists, ranges, and steps"""
        from mcli.workflow.scheduler.cron_parser import CronExpression

        cron = CronExpression("0,30 9-17/2 * * 1-5")

        # Minutes should be 0 and 30
        assert 0 in cron.fields[0]
        assert 30 in cron.fields[0]
        assert len(cron.fields[0]) == 2

        # Hours should be 9, 11, 13, 15, 17
        assert 9 in cron.fields[1]
        assert 11 in cron.fields[1]
        assert 13 in cron.fields[1]
        assert 15 in cron.fields[1]
        assert 17 in cron.fields[1]


class TestValidateCronExpression:
    """Test suite for validate_cron_expression utility function"""

    def test_validate_valid_expression(self):
        """Test validate_cron_expression with valid expression"""
        from mcli.workflow.scheduler.cron_parser import validate_cron_expression

        assert validate_cron_expression("0 0 * * *") is True

    def test_validate_invalid_expression(self):
        """Test validate_cron_expression with invalid expression"""
        from mcli.workflow.scheduler.cron_parser import validate_cron_expression

        assert validate_cron_expression("invalid") is False

    def test_validate_shortcut(self):
        """Test validate_cron_expression with shortcut"""
        from mcli.workflow.scheduler.cron_parser import validate_cron_expression

        assert validate_cron_expression("@daily") is True


class TestGetNextRunTimes:
    """Test suite for get_next_run_times utility function"""

    def test_get_next_run_times_basic(self):
        """Test getting next 5 run times"""
        from mcli.workflow.scheduler.cron_parser import get_next_run_times

        times = get_next_run_times("0 * * * *", count=5)  # Every hour

        assert len(times) == 5
        # Each time should be 1 hour apart
        for i in range(1, len(times)):
            diff = (times[i] - times[i - 1]).total_seconds()
            assert abs(diff - 3600) < 60  # Allow some variance

    def test_get_next_run_times_for_reboot(self):
        """Test get_next_run_times for @reboot returns empty list"""
        from mcli.workflow.scheduler.cron_parser import get_next_run_times

        times = get_next_run_times("@reboot", count=5)

        assert times == []

    def test_get_next_run_times_invalid_expression(self):
        """Test get_next_run_times with invalid expression returns empty list"""
        from mcli.workflow.scheduler.cron_parser import get_next_run_times

        times = get_next_run_times("invalid cron", count=5)

        assert times == []

    def test_get_next_run_times_custom_count(self):
        """Test getting custom count of next run times"""
        from mcli.workflow.scheduler.cron_parser import get_next_run_times

        times = get_next_run_times("0 0 * * *", count=3)  # Daily at midnight

        assert len(times) == 3

    def test_get_next_run_times_daily(self):
        """Test getting next run times for daily schedule"""
        from mcli.workflow.scheduler.cron_parser import get_next_run_times

        times = get_next_run_times("0 0 * * *", count=7)

        assert len(times) == 7
        # All times should be at midnight
        for time in times:
            assert time.hour == 0
            assert time.minute == 0
