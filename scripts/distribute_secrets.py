#!/usr/bin/env python3
"""
MCLI Secrets Distribution Script
Securely distribute environment variables to different deployment targets

Usage:
    python distribute_secrets.py --target [streamlit|flyio|vm|docker|verify]
    python distribute_secrets.py --target streamlit --output streamlit_secrets.toml
    python distribute_secrets.py --target flyio --app mcli-lsh-daemon
    python distribute_secrets.py --target vm --host user@host --path /opt/mcli
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import json


class SecretsDistributor:
    """Distribute environment secrets to various deployment targets"""

    def __init__(self, env_file: str = ".env.production"):
        self.env_file = Path(env_file)
        self.secrets: Dict[str, str] = {}

        if not self.env_file.exists():
            raise FileNotFoundError(f"Environment file not found: {env_file}")

        self._load_secrets()

    def _load_secrets(self):
        """Load environment variables from .env file"""
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    self.secrets[key.strip()] = value.strip()

        print(f"✓ Loaded {len(self.secrets)} environment variables")

    def get_critical_secrets(self) -> List[str]:
        """Return list of critical secret keys that must not be exposed"""
        return [
            'SUPABASE_SERVICE_ROLE_KEY',
            'DATABASE_URL',
            'LSH_API_KEY',
            'ALPACA_SECRET_KEY',
            'API_SECRET_KEY',
            'SECURITY_ADMIN_PASSWORD',
            'UK_COMPANIES_HOUSE_API_KEY',
        ]

    def verify_secrets(self):
        """Verify all critical secrets are present and valid"""
        print("\n=== Verifying Secrets ===\n")

        critical = self.get_critical_secrets()
        missing = []
        placeholder = []

        for key in critical:
            if key not in self.secrets:
                missing.append(key)
                print(f"✗ {key}: MISSING")
            elif any(x in self.secrets[key].lower() for x in ['your_', 'change', 'placeholder', 'here']):
                placeholder.append(key)
                print(f"⚠ {key}: PLACEHOLDER VALUE")
            else:
                print(f"✓ {key}: OK ({len(self.secrets[key])} chars)")

        print(f"\n=== Summary ===")
        print(f"Total secrets: {len(self.secrets)}")
        print(f"Critical secrets: {len(critical)}")
        print(f"Missing: {len(missing)}")
        print(f"Placeholders: {len(placeholder)}")

        if missing or placeholder:
            print("\n⚠ WARNING: Some secrets are missing or using placeholders!")
            return False

        print("\n✓ All critical secrets are properly configured!")
        return True

    def generate_streamlit_toml(self, output_file: str = "streamlit_secrets.toml"):
        """Generate Streamlit secrets.toml format"""
        print(f"\n=== Generating Streamlit Secrets ===\n")

        output_path = Path(output_file)

        with open(output_path, 'w') as f:
            f.write("# MCLI Streamlit Cloud Secrets\n")
            f.write("# Copy these values to Streamlit Cloud > App Settings > Secrets\n")
            f.write("# https://share.streamlit.io/\n\n")

            for key, value in sorted(self.secrets.items()):
                # Handle JSON arrays/objects
                if value.startswith('[') or value.startswith('{'):
                    f.write(f'{key} = \'\'\'{value}\'\'\'\n')
                else:
                    f.write(f'{key} = "{value}"\n')

        print(f"✓ Streamlit secrets written to: {output_path}")
        print(f"\nTo deploy:")
        print(f"1. Go to https://share.streamlit.io/")
        print(f"2. Select your app > Settings > Secrets")
        print(f"3. Copy contents of {output_file}")
        print(f"4. Paste into the secrets editor")
        print(f"5. Save and restart app")

        return output_path

    def generate_flyio_commands(self, app_name: str, output_file: str = "flyio_secrets.sh"):
        """Generate fly.io secrets set commands"""
        print(f"\n=== Generating fly.io Secrets Commands ===\n")

        output_path = Path(output_file)

        with open(output_path, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write(f"# MCLI fly.io Secrets Setup\n")
            f.write(f"# Run this script to set secrets for app: {app_name}\n\n")
            f.write("set -e\n\n")

            # Set secrets in batches (fly has limits)
            batch_size = 10
            keys = list(self.secrets.keys())

            for i in range(0, len(keys), batch_size):
                batch = keys[i:i+batch_size]
                f.write(f"# Batch {i//batch_size + 1}\n")
                f.write(f"fly secrets set \\\n")

                for j, key in enumerate(batch):
                    value = self.secrets[key]
                    # Escape special characters
                    value = value.replace('"', '\\"').replace('$', '\\$')

                    if j < len(batch) - 1:
                        f.write(f'  {key}="{value}" \\\n')
                    else:
                        f.write(f'  {key}="{value}" \\\n')

                f.write(f"  -a {app_name}\n\n")

        # Make executable
        os.chmod(output_path, 0o755)

        print(f"✓ fly.io secrets script written to: {output_path}")
        print(f"\nTo deploy:")
        print(f"1. Make sure you're logged in: fly auth login")
        print(f"2. Run: ./{output_file}")
        print(f"3. Verify: fly secrets list -a {app_name}")

        return output_path

    def generate_docker_env(self, output_file: str = ".env.docker"):
        """Generate Docker-compatible .env file"""
        print(f"\n=== Generating Docker Environment File ===\n")

        output_path = Path(output_file)

        with open(output_path, 'w') as f:
            f.write("# MCLI Docker Environment Configuration\n")
            f.write("# Use with: docker run --env-file .env.docker\n\n")

            for key, value in sorted(self.secrets.items()):
                # Docker env files don't support multi-line values well
                # So keep them on one line
                f.write(f'{key}={value}\n')

        # Secure permissions
        os.chmod(output_path, 0o600)

        print(f"✓ Docker env file written to: {output_path}")
        print(f"\nTo use:")
        print(f"1. docker run --env-file {output_file} your-image")
        print(f"2. Or add to docker-compose.yml:")
        print(f"   env_file:")
        print(f"     - {output_file}")

        return output_path

    def deploy_to_vm(self, host: str, remote_path: str = "/opt/mcli"):
        """Deploy .env file to remote VM via scp"""
        print(f"\n=== Deploying to VM: {host} ===\n")

        remote_env = f"{remote_path}/.env"

        try:
            # Copy file
            print(f"Copying {self.env_file} to {host}:{remote_env}")
            result = subprocess.run(
                ["scp", str(self.env_file), f"{host}:{remote_env}"],
                check=True,
                capture_output=True,
                text=True
            )

            # Set secure permissions
            print(f"Setting secure permissions (600)")
            subprocess.run(
                ["ssh", host, f"chmod 600 {remote_env}"],
                check=True,
                capture_output=True,
                text=True
            )

            print(f"✓ Successfully deployed to {host}:{remote_env}")
            print(f"\nTo verify:")
            print(f"  ssh {host} 'cat {remote_env} | grep -v \"^#\" | grep -v \"^$\" | wc -l'")

        except subprocess.CalledProcessError as e:
            print(f"✗ Deployment failed: {e}")
            if e.stderr:
                print(f"Error: {e.stderr}")
            sys.exit(1)

    def generate_kubernetes_secret(self, namespace: str = "default", secret_name: str = "mcli-secrets",
                                   output_file: str = "k8s_secret.yaml"):
        """Generate Kubernetes Secret manifest"""
        print(f"\n=== Generating Kubernetes Secret ===\n")

        import base64

        output_path = Path(output_file)

        with open(output_path, 'w') as f:
            f.write("apiVersion: v1\n")
            f.write("kind: Secret\n")
            f.write("metadata:\n")
            f.write(f"  name: {secret_name}\n")
            f.write(f"  namespace: {namespace}\n")
            f.write("type: Opaque\n")
            f.write("data:\n")

            for key, value in sorted(self.secrets.items()):
                # Base64 encode values
                encoded = base64.b64encode(value.encode()).decode()
                f.write(f"  {key}: {encoded}\n")

        print(f"✓ Kubernetes secret written to: {output_path}")
        print(f"\nTo deploy:")
        print(f"  kubectl apply -f {output_file}")
        print(f"\nTo use in pod:")
        print(f"  envFrom:")
        print(f"    - secretRef:")
        print(f"        name: {secret_name}")

        return output_path

    def print_summary(self):
        """Print summary of secrets"""
        print("\n=== Secrets Summary ===\n")

        categories = {
            'Database': ['SUPABASE', 'DATABASE_URL'],
            'LSH Daemon': ['LSH_'],
            'Trading': ['ALPACA_', 'UK_COMPANIES'],
            'API': ['API_'],
            'ML': ['MODEL_', 'MLFLOW_', 'PYTORCH_', 'OMP_', 'MKL_'],
            'Security': ['SECURITY_'],
            'Monitoring': ['MONITORING_'],
        }

        for category, prefixes in categories.items():
            matches = [k for k in self.secrets.keys()
                      if any(k.startswith(p) for p in prefixes)]
            if matches:
                print(f"{category}: {len(matches)} vars")
                for key in matches:
                    is_critical = key in self.get_critical_secrets()
                    marker = "🔒" if is_critical else "  "
                    print(f"  {marker} {key}")


def main():
    parser = argparse.ArgumentParser(
        description="Distribute MCLI secrets to deployment targets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify secrets are valid
  python distribute_secrets.py --target verify

  # Generate Streamlit secrets
  python distribute_secrets.py --target streamlit

  # Generate fly.io commands
  python distribute_secrets.py --target flyio --app mcli-lsh-daemon

  # Deploy to VM
  python distribute_secrets.py --target vm --host user@host --path /opt/mcli

  # Generate Docker env file
  python distribute_secrets.py --target docker

  # Generate Kubernetes secret
  python distribute_secrets.py --target k8s --namespace production
        """
    )

    parser.add_argument(
        '--target',
        required=True,
        choices=['verify', 'streamlit', 'flyio', 'vm', 'docker', 'k8s', 'summary'],
        help='Deployment target'
    )

    parser.add_argument(
        '--env-file',
        default='.env.production',
        help='Environment file to read (default: .env.production)'
    )

    parser.add_argument(
        '--output',
        help='Output file path'
    )

    parser.add_argument(
        '--app',
        help='fly.io app name'
    )

    parser.add_argument(
        '--host',
        help='VM hostname (user@host)'
    )

    parser.add_argument(
        '--path',
        default='/opt/mcli',
        help='Remote path on VM (default: /opt/mcli)'
    )

    parser.add_argument(
        '--namespace',
        default='default',
        help='Kubernetes namespace (default: default)'
    )

    parser.add_argument(
        '--secret-name',
        default='mcli-secrets',
        help='Kubernetes secret name (default: mcli-secrets)'
    )

    args = parser.parse_args()

    try:
        distributor = SecretsDistributor(args.env_file)

        if args.target == 'verify':
            distributor.verify_secrets()

        elif args.target == 'summary':
            distributor.print_summary()

        elif args.target == 'streamlit':
            output = args.output or 'streamlit_secrets.toml'
            distributor.generate_streamlit_toml(output)

        elif args.target == 'flyio':
            if not args.app:
                print("Error: --app is required for fly.io target")
                sys.exit(1)
            output = args.output or 'flyio_secrets.sh'
            distributor.generate_flyio_commands(args.app, output)

        elif args.target == 'docker':
            output = args.output or '.env.docker'
            distributor.generate_docker_env(output)

        elif args.target == 'vm':
            if not args.host:
                print("Error: --host is required for VM target")
                sys.exit(1)
            distributor.deploy_to_vm(args.host, args.path)

        elif args.target == 'k8s':
            output = args.output or 'k8s_secret.yaml'
            distributor.generate_kubernetes_secret(
                args.namespace,
                args.secret_name,
                output
            )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
