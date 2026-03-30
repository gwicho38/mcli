"""Tests for the release notes generator."""

import pytest

from mcli.self.release_notes_cmd import (
    CATEGORY_MAP,
    ParsedCommit,
    ReleaseNotes,
    parse_commits,
    render_markdown,
)


class TestParseCommits:
    """Test conventional commit parsing."""

    def test_parse_feat_commit(self):
        lines = ["abc12345|feat: add new command"]
        result = parse_commits(lines)
        assert len(result) == 1
        assert result[0].type == "feat"
        assert result[0].description == "add new command"

    def test_parse_fix_with_scope(self):
        lines = ["abc12345|fix(config): resolve path issue"]
        result = parse_commits(lines)
        assert result[0].type == "fix"
        assert result[0].scope == "config"
        assert result[0].description == "resolve path issue"

    def test_parse_breaking_change(self):
        lines = ["abc12345|feat!: remove legacy API"]
        result = parse_commits(lines)
        assert result[0].breaking is True

    def test_parse_pr_number(self):
        lines = ["abc12345|fix: resolve issue (#42)"]
        result = parse_commits(lines)
        assert result[0].pr_number == "42"
        assert result[0].description == "resolve issue"

    def test_parse_unconventional_commit(self):
        lines = ["abc12345|some random commit message"]
        result = parse_commits(lines)
        assert result[0].type == ""
        assert result[0].description == "some random commit message"

    def test_parse_multiple_commits(self):
        lines = [
            "aaa11111|feat: feature one",
            "bbb22222|fix: bug fix",
            "ccc33333|docs: update readme",
        ]
        result = parse_commits(lines)
        assert len(result) == 3
        assert result[0].type == "feat"
        assert result[1].type == "fix"
        assert result[2].type == "docs"

    def test_parse_empty_lines(self):
        result = parse_commits([])
        assert result == []

    def test_parse_all_commit_types(self):
        for commit_type in CATEGORY_MAP:
            lines = [f"abc12345|{commit_type}: test commit"]
            result = parse_commits(lines)
            assert result[0].type == commit_type


class TestRenderMarkdown:
    """Test markdown rendering."""

    def test_render_basic(self):
        notes = ReleaseNotes(
            version="1.0.0",
            date="2026-03-23",
            categories={
                "Features": [
                    ParsedCommit(
                        hash="abc12345",
                        type="feat",
                        scope=None,
                        description="add new command",
                    )
                ]
            },
        )
        md = render_markdown(notes)
        assert "# Release 1.0.0" in md
        assert "## Features" in md
        assert "- add new command" in md

    def test_render_with_scope(self):
        notes = ReleaseNotes(
            version="1.0.0",
            date="2026-03-23",
            categories={
                "Bug Fixes": [
                    ParsedCommit(
                        hash="abc12345",
                        type="fix",
                        scope="config",
                        description="fix path",
                    )
                ]
            },
        )
        md = render_markdown(notes)
        assert "**config:** fix path" in md

    def test_render_with_pr_link(self):
        notes = ReleaseNotes(
            version="1.0.0",
            date="2026-03-23",
            categories={
                "Features": [
                    ParsedCommit(
                        hash="abc12345",
                        type="feat",
                        scope=None,
                        description="add feature",
                        pr_number="42",
                    )
                ]
            },
        )
        md = render_markdown(notes, repo_url="https://github.com/gwicho38/mcli")
        assert "[#42](https://github.com/gwicho38/mcli/pull/42)" in md

    def test_render_breaking_changes(self):
        commit = ParsedCommit(
            hash="abc12345",
            type="feat",
            scope=None,
            description="remove old API",
            breaking=True,
        )
        notes = ReleaseNotes(
            version="2.0.0",
            date="2026-03-23",
            categories={"Features": [commit]},
            breaking_changes=[commit],
        )
        md = render_markdown(notes)
        assert "## Breaking Changes" in md

    def test_render_uncategorized(self):
        notes = ReleaseNotes(
            version="1.0.0",
            date="2026-03-23",
            uncategorized=[
                ParsedCommit(
                    hash="abc12345",
                    type="",
                    scope=None,
                    description="misc change",
                )
            ],
        )
        md = render_markdown(notes)
        assert "## Other Changes" in md
        assert "misc change" in md

    def test_total_commits(self):
        notes = ReleaseNotes(
            version="1.0.0",
            date="2026-03-23",
            categories={"Features": [
                ParsedCommit(hash="a", type="feat", scope=None, description="one"),
                ParsedCommit(hash="b", type="feat", scope=None, description="two"),
            ]},
            uncategorized=[
                ParsedCommit(hash="c", type="", scope=None, description="three"),
            ],
        )
        assert notes.total_commits == 3
