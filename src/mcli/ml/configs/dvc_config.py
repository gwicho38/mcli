"""DVC Configuration for Data Versioning and Pipeline Management"""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class DVCConfig:
    """Configuration class for DVC data versioning and pipeline management"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent.parent.parent
        self.dvc_dir = self.project_root / ".dvc"
        self.data_dir = self.project_root / "data"
        self.models_dir = self.project_root / "models"

    def setup_data_directories(self) -> None:
        """Create and configure data directories for DVC tracking"""
        directories = [
            self.data_dir / "raw",
            self.data_dir / "processed",
            self.data_dir / "features",
            self.models_dir / "pytorch",
            self.models_dir / "sklearn",
            self.models_dir / "ensemble",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {directory}")

    def add_data_to_dvc(self, data_path: Path, message: Optional[str] = None) -> None:
        """Add data file or directory to DVC tracking"""
        try:
            # Add to DVC
            cmd = ["dvc", "add", str(data_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if result.returncode != 0:
                raise Exception(f"DVC add failed: {result.stderr}")

            print(f"Added to DVC: {data_path}")

            # Add .dvc file to git
            dvc_file = data_path.with_suffix(data_path.suffix + ".dvc")
            if dvc_file.exists():
                git_cmd = ["git", "add", str(dvc_file)]
                subprocess.run(git_cmd, cwd=self.project_root)
                print(f"Added to git: {dvc_file}")

        except Exception as e:
            print(f"Error adding data to DVC: {e}")
            raise

    def create_pipeline_stage(
        self,
        stage_name: str,
        command: str,
        dependencies: List[str],
        outputs: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        metrics: Optional[List[str]] = None,
    ) -> None:
        """Create a DVC pipeline stage"""
        try:
            cmd = [
                "dvc",
                "stage",
                "add",
                "-n",
                stage_name,
                "-d",
                *dependencies,
                "-o",
                *outputs,
                command,
            ]

            if parameters:
                for param_file in parameters:
                    cmd.extend(["-p", param_file])

            if metrics:
                for metric_file in metrics:
                    cmd.extend(["-M", metric_file])

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if result.returncode != 0:
                raise Exception(f"DVC stage creation failed: {result.stderr}")

            print(f"Created DVC pipeline stage: {stage_name}")

        except Exception as e:
            print(f"Error creating pipeline stage: {e}")
            raise

    def run_pipeline(self, stage_name: Optional[str] = None) -> None:
        """Run DVC pipeline or specific stage"""
        try:
            cmd = ["dvc", "repro"]
            if stage_name:
                cmd.append(stage_name)

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if result.returncode != 0:
                raise Exception(f"DVC pipeline run failed: {result.stderr}")

            print(f"DVC pipeline completed successfully")
            if result.stdout:
                print(result.stdout)

        except Exception as e:
            print(f"Error running pipeline: {e}")
            raise

    def get_data_version(self, data_path: Path) -> Optional[str]:
        """Get the current version hash of a data file"""
        try:
            dvc_file = data_path.with_suffix(data_path.suffix + ".dvc")
            if not dvc_file.exists():
                return None

            with open(dvc_file, "r") as f:
                dvc_data = yaml.safe_load(f)
                return dvc_data.get("outs", [{}])[0].get("md5")

        except Exception as e:
            print(f"Error getting data version: {e}")
            return None

    def pull_data(self, path: Optional[str] = None) -> None:
        """Pull data from DVC remote storage"""
        try:
            cmd = ["dvc", "pull"]
            if path:
                cmd.append(path)

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if result.returncode != 0:
                raise Exception(f"DVC pull failed: {result.stderr}")

            print("DVC data pull completed successfully")

        except Exception as e:
            print(f"Error pulling data: {e}")
            raise

    def push_data(self, path: Optional[str] = None) -> None:
        """Push data to DVC remote storage"""
        try:
            cmd = ["dvc", "push"]
            if path:
                cmd.append(path)

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if result.returncode != 0:
                print(f"DVC push warning: {result.stderr}")
                # Don't raise exception for push failures (remote might not be configured)

            print("DVC data push completed")

        except Exception as e:
            print(f"Note: DVC push failed (remote storage may not be configured): {e}")

    def configure_remote_storage(
        self, remote_name: str, storage_url: str, default: bool = True
    ) -> None:
        """Configure DVC remote storage"""
        try:
            # Add remote
            cmd = ["dvc", "remote", "add", remote_name, storage_url]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if result.returncode != 0 and "already exists" not in result.stderr:
                raise Exception(f"DVC remote add failed: {result.stderr}")

            # Set as default if requested
            if default:
                cmd = ["dvc", "remote", "default", remote_name]
                subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            print(f"Configured DVC remote: {remote_name}")

        except Exception as e:
            print(f"Error configuring remote storage: {e}")
            raise

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get status of DVC pipeline"""
        try:
            cmd = ["dvc", "status"]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except Exception as e:
            print(f"Error getting pipeline status: {e}")
            return {"error": str(e)}


# Global configuration instance
dvc_config = DVCConfig()


def get_dvc_config() -> DVCConfig:
    """Get the global DVC configuration instance"""
    return dvc_config


def setup_dvc() -> None:
    """Setup DVC data directories and configuration"""
    dvc_config.setup_data_directories()
    print(f"DVC project root: {dvc_config.project_root}")
    print(f"Data directory: {dvc_config.data_dir}")
    print(f"Models directory: {dvc_config.models_dir}")


if __name__ == "__main__":
    setup_dvc()
