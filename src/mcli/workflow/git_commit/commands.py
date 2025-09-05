import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class GitCommitWorkflow:
    """Workflow for automatic git commit message generation"""

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.validate_git_repo()

    def validate_git_repo(self):
        """Validate that we're in a git repository"""
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def get_git_status(self) -> Dict[str, Any]:
        """Get current git status"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            status_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

            changes = {"modified": [], "added": [], "deleted": [], "renamed": [], "untracked": []}

            for line in status_lines:
                if len(line) < 3:
                    continue

                status_code = line[:2]
                filename = line[3:]

                if status_code[0] == "M" or status_code[1] == "M":
                    changes["modified"].append(filename)
                elif status_code[0] == "A":
                    changes["added"].append(filename)
                elif status_code[0] == "D":
                    changes["deleted"].append(filename)
                elif status_code[0] == "R":
                    changes["renamed"].append(filename)
                elif status_code == "??":
                    changes["untracked"].append(filename)

            return {
                "has_changes": len(status_lines) > 0,
                "changes": changes,
                "total_files": len(status_lines),
            }

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get git status: {e}")

    def get_git_diff(self) -> str:
        """Get git diff for all changes"""
        try:
            # Get diff for staged and unstaged changes
            staged_result = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            unstaged_result = subprocess.run(
                ["git", "diff"], cwd=self.repo_path, capture_output=True, text=True, check=True
            )

            diff_content = ""
            if staged_result.stdout:
                diff_content += "=== STAGED CHANGES ===\n" + staged_result.stdout + "\n"
            if unstaged_result.stdout:
                diff_content += "=== UNSTAGED CHANGES ===\n" + unstaged_result.stdout + "\n"

            return diff_content

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get git diff: {e}")

    def stage_all_changes(self) -> bool:
        """Stage all changes for commit"""
        try:
            subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
            logger.info("All changes staged successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stage changes: {e}")
            return False

    def generate_commit_message(self, changes: Dict[str, Any], diff_content: str) -> str:
        """Generate a commit message using AI based on changes and diff"""

        # For now, we'll create a simple rule-based commit message
        # In a real implementation, you'd integrate with your AI model here

        summary_parts = []

        # Analyze file changes
        if changes["changes"]["added"]:
            if len(changes["changes"]["added"]) == 1:
                summary_parts.append(f"Add {changes['changes']['added'][0]}")
            else:
                summary_parts.append(f"Add {len(changes['changes']['added'])} new files")

        if changes["changes"]["modified"]:
            if len(changes["changes"]["modified"]) == 1:
                summary_parts.append(f"Update {changes['changes']['modified'][0]}")
            else:
                summary_parts.append(f"Update {len(changes['changes']['modified'])} files")

        if changes["changes"]["deleted"]:
            if len(changes["changes"]["deleted"]) == 1:
                summary_parts.append(f"Remove {changes['changes']['deleted'][0]}")
            else:
                summary_parts.append(f"Remove {len(changes['changes']['deleted'])} files")

        if changes["changes"]["renamed"]:
            summary_parts.append(f"Rename {len(changes['changes']['renamed'])} files")

        # Create commit message
        if not summary_parts:
            commit_message = "Update repository files"
        else:
            commit_message = ", ".join(summary_parts)

        # Add more context based on file patterns
        modified_files = changes["changes"]["modified"] + changes["changes"]["added"]

        # Check for specific file types
        if any(".py" in f for f in modified_files):
            commit_message += " (Python changes)"
        elif any(".js" in f or ".ts" in f for f in modified_files):
            commit_message += " (JavaScript/TypeScript changes)"
        elif any(".md" in f for f in modified_files):
            commit_message += " (Documentation changes)"
        elif any(
            "requirements" in f or "package.json" in f or "Cargo.toml" in f for f in modified_files
        ):
            commit_message += " (Dependencies changes)"

        return commit_message

    def create_commit(self, message: str) -> bool:
        """Create a git commit with the given message"""
        try:
            subprocess.run(["git", "commit", "-m", message], cwd=self.repo_path, check=True)
            logger.info(f"Commit created successfully: {message}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create commit: {e}")
            return False

    def run_auto_commit(self) -> Dict[str, Any]:
        """Run the complete auto-commit workflow"""
        result = {
            "success": False,
            "message": "",
            "commit_hash": None,
            "changes_summary": {},
            "error": None,
        }

        try:
            # Check git status
            status = self.get_git_status()
            result["changes_summary"] = status

            if not status["has_changes"]:
                result["message"] = "No changes to commit"
                result["success"] = True
                return result

            # Get diff content
            diff_content = self.get_git_diff()

            # Stage all changes
            if not self.stage_all_changes():
                result["error"] = "Failed to stage changes"
                return result

            # Generate commit message
            commit_message = self.generate_commit_message(status, diff_content)
            result["message"] = commit_message

            # Create commit
            if self.create_commit(commit_message):
                # Get commit hash
                try:
                    hash_result = subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    result["commit_hash"] = hash_result.stdout.strip()
                except:
                    pass

                result["success"] = True
            else:
                result["error"] = "Failed to create commit"

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Auto-commit workflow failed: {e}")

        return result


@click.group(name="git-commit")
def git_commit_cli():
    """AI-powered git commit message generation"""
    pass


@git_commit_cli.command()
@click.option(
    "--repo-path", type=click.Path(), help="Path to git repository (default: current directory)"
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be committed without actually committing"
)
def auto(repo_path: Optional[str], dry_run: bool):
    """Automatically stage changes and create commit with AI-generated message"""

    try:
        workflow = GitCommitWorkflow(repo_path)

        if dry_run:
            # Just show what would happen
            status = workflow.get_git_status()

            if not status["has_changes"]:
                click.echo("No changes to commit")
                return

            click.echo("Changes that would be staged and committed:")
            changes = status["changes"]

            if changes["untracked"]:
                click.echo(f"  New files ({len(changes['untracked'])}):")
                for file in changes["untracked"]:
                    click.echo(f"    + {file}")

            if changes["modified"]:
                click.echo(f"  Modified files ({len(changes['modified'])}):")
                for file in changes["modified"]:
                    click.echo(f"    M {file}")

            if changes["deleted"]:
                click.echo(f"  Deleted files ({len(changes['deleted'])}):")
                for file in changes["deleted"]:
                    click.echo(f"    - {file}")

            # Generate and show commit message
            diff_content = workflow.get_git_diff()
            commit_message = workflow.generate_commit_message(status, diff_content)
            click.echo(f"\nProposed commit message: {commit_message}")

        else:
            # Actually run the workflow
            result = workflow.run_auto_commit()

            if result["success"]:
                if result["commit_hash"]:
                    click.echo(f"✅ Commit created successfully: {result['commit_hash'][:8]}")
                else:
                    click.echo("✅ Commit created successfully")

                click.echo(f"Message: {result['message']}")

                # Show summary
                changes = result["changes_summary"]["changes"]
                total = sum(len(files) for files in changes.values())
                click.echo(f"Files changed: {total}")

            else:
                click.echo(f"❌ Failed to create commit: {result.get('error', 'Unknown error')}")

    except Exception as e:
        click.echo(f"❌ Error: {e}")


@git_commit_cli.command()
@click.option(
    "--repo-path", type=click.Path(), help="Path to git repository (default: current directory)"
)
def status(repo_path: Optional[str]):
    """Show current git repository status"""

    try:
        workflow = GitCommitWorkflow(repo_path)
        status_info = workflow.get_git_status()

        if not status_info["has_changes"]:
            click.echo("✅ Working tree is clean")
            return

        click.echo("📋 Repository Status:")
        changes = status_info["changes"]

        if changes["untracked"]:
            click.echo(f"\n📄 Untracked files ({len(changes['untracked'])}):")
            for file in changes["untracked"]:
                click.echo(f"  ?? {file}")

        if changes["modified"]:
            click.echo(f"\n✏️  Modified files ({len(changes['modified'])}):")
            for file in changes["modified"]:
                click.echo(f"  M  {file}")

        if changes["added"]:
            click.echo(f"\n➕ Added files ({len(changes['added'])}):")
            for file in changes["added"]:
                click.echo(f"  A  {file}")

        if changes["deleted"]:
            click.echo(f"\n🗑️  Deleted files ({len(changes['deleted'])}):")
            for file in changes["deleted"]:
                click.echo(f"  D  {file}")

        if changes["renamed"]:
            click.echo(f"\n🔄 Renamed files ({len(changes['renamed'])}):")
            for file in changes["renamed"]:
                click.echo(f"  R  {file}")

        click.echo(f"\nTotal files with changes: {status_info['total_files']}")

    except Exception as e:
        click.echo(f"❌ Error: {e}")


@git_commit_cli.command()
@click.argument("message")
@click.option(
    "--repo-path", type=click.Path(), help="Path to git repository (default: current directory)"
)
@click.option("--stage-all", is_flag=True, help="Stage all changes before committing")
def commit(message: str, repo_path: Optional[str], stage_all: bool):
    """Create a commit with a custom message"""

    try:
        workflow = GitCommitWorkflow(repo_path)

        if stage_all:
            if not workflow.stage_all_changes():
                click.echo("❌ Failed to stage changes")
                return

        if workflow.create_commit(message):
            click.echo(f"✅ Commit created: {message}")
        else:
            click.echo("❌ Failed to create commit")

    except Exception as e:
        click.echo(f"❌ Error: {e}")


if __name__ == "__main__":
    git_commit_cli()
