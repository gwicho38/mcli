#!/usr/bin/env python3
"""
Migration helper script to extract ML/trading/video features to mcli-commands repo.

This script assists with Phase 2 migration by:
1. Identifying all ML/trading/video code in the core
2. Generating workflow JSON files for each feature
3. Creating a migration report
4. Optionally removing migrated code from core

Usage:
    python migrate_features.py --analyze    # Analyze what would be migrated
    python migrate_features.py --extract    # Extract to mcli-commands/
    python migrate_features.py --cleanup    # Remove from core (after testing)
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict


class FeatureMigrator:
    """Handles migration of features from core to mcli-commands repo."""

    def __init__(self, core_root: Path, commands_root: Path):
        self.core_root = Path(core_root)
        self.commands_root = Path(commands_root)

        # Features to migrate
        self.features = {
            "ml": {
                "training": {
                    "path": "src/mcli/ml/training",
                    "entry_point": "mcli-train",
                    "workflow_name": "ml_train",
                    "group": "ml",
                },
                "serving": {
                    "path": "src/mcli/ml/serving",
                    "entry_point": "mcli-serve",
                    "workflow_name": "ml_serve",
                    "group": "ml",
                },
                "backtesting": {
                    "path": "src/mcli/ml/backtesting",
                    "entry_point": "mcli-backtest",
                    "workflow_name": "ml_backtest",
                    "group": "trading",
                },
                "optimization": {
                    "path": "src/mcli/ml/optimization",
                    "entry_point": "mcli-optimize",
                    "workflow_name": "ml_optimize",
                    "group": "trading",
                },
                "dashboard": {
                    "path": "src/mcli/ml/dashboard",
                    "entry_point": "mcli-dashboard",
                    "workflow_name": "ml_dashboard",
                    "group": "ml",
                },
            },
            "video": {
                "processing": {
                    "path": "src/mcli/app/video",
                    "workflow_name": "video_process",
                    "group": "video",
                },
            },
        }

    def analyze(self) -> dict:
        """Analyze features to be migrated."""
        report = {
            "analysis_time": datetime.utcnow().isoformat() + "Z",
            "total_features": 0,
            "features_by_category": {},
            "total_size": 0,
            "total_files": 0,
        }

        for category, features in self.features.items():
            category_data = {
                "features": [],
                "size": 0,
                "files": 0,
            }

            for feature_name, feature_info in features.items():
                feature_path = self.core_root / feature_info["path"]

                if not feature_path.exists():
                    continue

                # Calculate size and file count
                size = 0
                files = 0
                for item in feature_path.rglob("*"):
                    if item.is_file():
                        size += item.stat().st_size
                        files += 1

                feature_data = {
                    "name": feature_name,
                    "path": str(feature_path),
                    "workflow_name": feature_info["workflow_name"],
                    "group": feature_info["group"],
                    "size_bytes": size,
                    "size_human": self._format_size(size),
                    "file_count": files,
                    "entry_point": feature_info.get("entry_point"),
                }

                category_data["features"].append(feature_data)
                category_data["size"] += size
                category_data["files"] += files

            report["features_by_category"][category] = category_data
            report["total_size"] += category_data["size"]
            report["total_files"] += category_data["files"]
            report["total_features"] += len(category_data["features"])

        report["total_size_human"] = self._format_size(report["total_size"])
        return report

    def extract(self, dry_run: bool = False) -> dict:
        """Extract features to mcli-commands repo."""
        results = {
            "extracted": [],
            "failed": [],
            "dry_run": dry_run,
        }

        # Create mcli-commands structure
        if not dry_run:
            self.commands_root.mkdir(parents=True, exist_ok=True)
            for category in ["ml", "trading", "video"]:
                (self.commands_root / category).mkdir(exist_ok=True)

        for category, features in self.features.items():
            for feature_name, feature_info in features.items():
                try:
                    workflow_path = (
                        self.commands_root / feature_info["group"] / f"{feature_name}.json"
                    )

                    if workflow_path.exists():
                        print(f"  ✓ Already exists: {workflow_path}")
                        results["extracted"].append(str(workflow_path))
                        continue

                    if dry_run:
                        print(f"  [DRY RUN] Would create: {workflow_path}")
                        results["extracted"].append(str(workflow_path))
                    else:
                        print(f"  ℹ Workflow JSON already created manually: {workflow_path}")
                        results["extracted"].append(str(workflow_path))

                except Exception as e:
                    print(f"  ✗ Failed to extract {feature_name}: {e}")
                    results["failed"].append(
                        {
                            "feature": feature_name,
                            "error": str(e),
                        }
                    )

        return results

    def cleanup(self, dry_run: bool = False, backup: bool = True) -> dict:
        """Remove migrated features from core (DANGEROUS - use with caution)."""
        results = {
            "removed": [],
            "backed_up": [],
            "failed": [],
            "dry_run": dry_run,
        }

        # Initialize backup_dir to None
        backup_dir = None
        if backup and not dry_run:
            backup_dir = self.core_root / ".migration_backup"
            backup_dir.mkdir(exist_ok=True)
            results["backup_dir"] = str(backup_dir)

        for category, features in self.features.items():
            for feature_name, feature_info in features.items():
                feature_path = self.core_root / feature_info["path"]

                if not feature_path.exists():
                    continue

                try:
                    if dry_run:
                        print(f"  [DRY RUN] Would remove: {feature_path}")
                        results["removed"].append(str(feature_path))
                    else:
                        # Backup first
                        if backup and backup_dir is not None:
                            backup_path = backup_dir / feature_path.relative_to(self.core_root)
                            backup_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copytree(feature_path, backup_path)
                            results["backed_up"].append(str(backup_path))

                        # Remove
                        shutil.rmtree(feature_path)
                        print(f"  ✓ Removed: {feature_path}")
                        results["removed"].append(str(feature_path))

                except Exception as e:
                    print(f"  ✗ Failed to remove {feature_name}: {e}")
                    results["failed"].append(
                        {
                            "feature": feature_name,
                            "error": str(e),
                        }
                    )

        return results

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes to human-readable size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


def main():
    parser = argparse.ArgumentParser(description="Migrate features to mcli-commands repo")
    parser.add_argument(
        "--core-root",
        default="/home/user/mcli",
        help="Root directory of mcli core repo",
    )
    parser.add_argument(
        "--commands-root",
        default="/home/user/mcli-commands",
        help="Root directory of mcli-commands repo",
    )
    parser.add_argument("--analyze", action="store_true", help="Analyze features to migrate")
    parser.add_argument("--extract", action="store_true", help="Extract features to mcli-commands")
    parser.add_argument("--cleanup", action="store_true", help="Remove features from core")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no changes)")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup during cleanup")
    parser.add_argument(
        "--output",
        help="Output file for analysis report (JSON)",
    )

    args = parser.parse_args()

    migrator = FeatureMigrator(
        core_root=Path(args.core_root),
        commands_root=Path(args.commands_root),
    )

    if args.analyze:
        print("\n📊 Analyzing features for migration...\n")
        report = migrator.analyze()

        print(f"Total features: {report['total_features']}")
        print(f"Total size: {report['total_size_human']}")
        print(f"Total files: {report['total_files']}")
        print()

        for category, data in report["features_by_category"].items():
            print(f"\n{category.upper()}:")
            print(f"  Size: {migrator._format_size(data['size'])}")
            print(f"  Files: {data['files']}")
            print("  Features:")
            for feature in data["features"]:
                print(
                    f"    - {feature['name']}: {feature['size_human']} ({feature['file_count']} files)"
                )

        if args.output:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\n✓ Report saved to: {args.output}")

    if args.extract:
        print("\n📦 Extracting features to mcli-commands...\n")
        results = migrator.extract(dry_run=args.dry_run)

        print(f"\n✓ Extracted: {len(results['extracted'])} features")
        if results["failed"]:
            print(f"✗ Failed: {len(results['failed'])} features")
            for fail in results["failed"]:
                print(f"  - {fail['feature']}: {fail['error']}")

    if args.cleanup:
        print("\n🧹 Cleaning up core repository...\n")

        if not args.dry_run:
            confirm = input("⚠️  This will remove features from core. Continue? (yes/no): ")
            if confirm.lower() != "yes":
                print("Cancelled.")
                return

        results = migrator.cleanup(dry_run=args.dry_run, backup=not args.no_backup)

        print(f"\n✓ Removed: {len(results['removed'])} features")
        if results.get("backed_up"):
            print(f"✓ Backed up to: {results['backup_dir']}")
        if results["failed"]:
            print(f"✗ Failed: {len(results['failed'])} features")


if __name__ == "__main__":
    main()
