#!/usr/bin/env python3
"""Documentation link validator for MCLI.

Validates all markdown links in README.md and docs/ directory:
- Internal links (checks files exist)
- External links (HTTP HEAD requests)
- Anchor links (checks heading exists)

Usage:
    python tools/validate_doc_links.py [--external] [--verbose] [path...]

Examples:
    python tools/validate_doc_links.py                    # Validate all docs
    python tools/validate_doc_links.py README.md          # Validate single file
    python tools/validate_doc_links.py --external         # Include external URLs
    python tools/validate_doc_links.py docs/ --verbose    # Verbose output
"""

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import NamedTuple, Optional
from urllib.parse import urlparse

# Optional: requests for external link checking
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class LinkError(NamedTuple):
    """Represents a broken link."""

    file: str
    line: int
    link: str
    error: str


class LinkValidator:
    """Validates markdown links."""

    # Regex to find markdown links: [text](url) or [text][ref]
    LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
    # Regex to find reference-style links: [ref]: url
    REF_PATTERN = re.compile(r"^\[([^\]]+)\]:\s*(.+)$", re.MULTILINE)
    # Regex to find headings for anchor validation
    HEADING_PATTERN = re.compile(r"^#+\s+(.+)$", re.MULTILINE)

    def __init__(
        self,
        check_external: bool = False,
        verbose: bool = False,
        timeout: int = 10,
    ) -> None:
        """Initialize the link validator.

        Args:
            check_external: Whether to check external HTTP links.
            verbose: Whether to print verbose output.
            timeout: Timeout for HTTP requests in seconds.
        """
        self.check_external = check_external
        self.verbose = verbose
        self.timeout = timeout
        self.errors: list[LinkError] = []
        self.checked_urls: dict[str, bool] = {}
        self.file_cache: dict[str, bool] = {}

    def log(self, msg: str) -> None:
        """Print verbose message."""
        if self.verbose:
            print(f"  {msg}")

    def slugify(self, heading: str) -> str:
        """Convert heading to anchor slug (GitHub style)."""
        slug = heading.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s]+", "-", slug)
        return slug

    def get_headings(self, content: str) -> set[str]:
        """Extract all heading anchors from markdown content."""
        headings: set[str] = set()
        for match in self.HEADING_PATTERN.finditer(content):
            heading = match.group(1).strip()
            headings.add(self.slugify(heading))
        return headings

    def check_internal_link(self, link: str, source_file: Path) -> Optional[str]:
        """Check if internal link target exists.

        Returns error message or None if valid.
        """
        # Parse link and anchor
        if "#" in link:
            path_part, anchor = link.split("#", 1)
        else:
            path_part, anchor = link, None

        # Empty path means same file anchor
        if not path_part:
            target_file = source_file
        else:
            # Resolve relative path
            if path_part.startswith("/"):
                # Absolute from repo root
                target_file = Path.cwd() / path_part.lstrip("/")
            else:
                # Relative to source file
                target_file = source_file.parent / path_part

        # Normalize path
        try:
            target_file = target_file.resolve()
        except (OSError, ValueError):
            return f"Invalid path: {link}"

        # Check cache first
        cache_key = str(target_file)
        if cache_key in self.file_cache:
            exists = self.file_cache[cache_key]
        else:
            exists = target_file.exists()
            self.file_cache[cache_key] = exists

        if not exists:
            return f"File not found: {path_part or source_file.name}"

        # Check anchor if present
        if anchor:
            try:
                content = target_file.read_text(encoding="utf-8", errors="ignore")
                headings = self.get_headings(content)
                if anchor.lower() not in headings:
                    return f"Anchor not found: #{anchor}"
            except Exception as e:
                return f"Cannot read file for anchor check: {e}"

        return None

    def check_external_link(self, url: str) -> Optional[str]:
        """Check if external URL is reachable.

        Returns error message or None if valid.
        """
        if not REQUESTS_AVAILABLE:
            return None  # Skip if requests not installed

        # Check cache
        if url in self.checked_urls:
            return None if self.checked_urls[url] else f"Previously failed: {url}"

        try:
            # Use HEAD request first (faster)
            response = requests.head(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                headers={"User-Agent": "MCLI-LinkValidator/1.0"},
            )

            # Some servers don't support HEAD, try GET
            if response.status_code == 405:
                response = requests.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    headers={"User-Agent": "MCLI-LinkValidator/1.0"},
                    stream=True,
                )
                response.close()

            if response.status_code >= 400:
                self.checked_urls[url] = False
                return f"HTTP {response.status_code}"

            self.checked_urls[url] = True
            return None

        except requests.exceptions.Timeout:
            self.checked_urls[url] = False
            return "Timeout"
        except requests.exceptions.SSLError:
            self.checked_urls[url] = False
            return "SSL Error"
        except requests.exceptions.ConnectionError:
            self.checked_urls[url] = False
            return "Connection failed"
        except Exception as e:
            self.checked_urls[url] = False
            return str(e)

    def validate_file(self, file_path: Path) -> list[LinkError]:
        """Validate all links in a markdown file."""
        errors: list[LinkError] = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            errors.append(LinkError(str(file_path), 0, "", f"Cannot read file: {e}"))
            return errors

        # Find all links with line numbers
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for match in self.LINK_PATTERN.finditer(line):
                link_text, link_url = match.groups()

                # Skip empty links
                if not link_url.strip():
                    continue

                # Skip mailto and javascript links
                if link_url.startswith(("mailto:", "javascript:", "tel:")):
                    continue

                # Determine link type
                parsed = urlparse(link_url)

                if parsed.scheme in ("http", "https"):
                    # External link
                    if self.check_external:
                        self.log(f"Checking external: {link_url}")
                        error = self.check_external_link(link_url)
                        if error:
                            errors.append(LinkError(str(file_path), line_num, link_url, error))
                else:
                    # Internal link
                    self.log(f"Checking internal: {link_url}")
                    error = self.check_internal_link(link_url, file_path)
                    if error:
                        errors.append(LinkError(str(file_path), line_num, link_url, error))

        return errors

    def validate_paths(self, paths: list[Path]) -> list[LinkError]:
        """Validate all markdown files in given paths."""
        files_to_check: list[Path] = []

        for path in paths:
            if path.is_file():
                if path.suffix.lower() == ".md":
                    files_to_check.append(path)
            elif path.is_dir():
                files_to_check.extend(path.rglob("*.md"))

        # Filter out common exclusions
        files_to_check = [
            f
            for f in files_to_check
            if ".venv" not in str(f) and "node_modules" not in str(f) and ".git" not in str(f)
        ]

        print(f"Validating {len(files_to_check)} markdown files...")

        all_errors: list[LinkError] = []

        # Check external links in parallel for speed
        if self.check_external and REQUESTS_AVAILABLE:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(self.validate_file, f): f for f in files_to_check}
                for future in as_completed(futures):
                    errors = future.result()
                    all_errors.extend(errors)
        else:
            for file_path in files_to_check:
                errors = self.validate_file(file_path)
                all_errors.extend(errors)

        return all_errors


def main() -> None:
    """Entry point for the documentation link validator."""
    parser = argparse.ArgumentParser(description="Validate markdown documentation links")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["README.md", "docs/"],
        help="Files or directories to validate (default: README.md docs/)",
    )
    parser.add_argument(
        "--external",
        "-e",
        action="store_true",
        help="Also check external HTTP links (slower)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=10,
        help="Timeout for external requests in seconds (default: 10)",
    )

    args = parser.parse_args()

    # Convert paths
    paths = [Path(p) for p in args.paths]

    # Validate paths exist
    for path in paths:
        if not path.exists():
            print(f"Warning: Path not found: {path}")

    # Run validation
    validator = LinkValidator(
        check_external=args.external,
        verbose=args.verbose,
        timeout=args.timeout,
    )

    errors = validator.validate_paths(paths)

    # Report results
    if errors:
        print(f"\nFound {len(errors)} broken link(s):\n")
        for error in sorted(errors, key=lambda e: (e.file, e.line)):
            print(f"  {error.file}:{error.line}")
            print(f"    Link: {error.link}")
            print(f"    Error: {error.error}")
            print()
        sys.exit(1)
    else:
        print("\nAll links valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
