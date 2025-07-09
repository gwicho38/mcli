#!/usr/bin/env python3
"""
Template packaging script for mcli webapp templates.

This script creates immutable tar.gz archives of templates with SHA256 hashes
for integrity verification.
"""

import hashlib
import json
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import click


class TemplatePackager:
    """Packages templates into immutable archives with integrity checks."""
    
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.archives_dir = templates_dir / "archives"
        self.archives_dir.mkdir(exist_ok=True)
        
    def get_template_directories(self) -> List[Path]:
        """Get all template directories."""
        templates = []
        for item in self.templates_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.') and item.name != 'archives':
                templates.append(item)
        return templates
    
    def compute_directory_hash(self, directory: Path) -> str:
        """Compute SHA256 hash of a directory."""
        sha256_hash = hashlib.sha256()
        
        # Walk through all files in the directory
        for file_path in sorted(directory.rglob('*')):
            if file_path.is_file():
                # Add relative path to hash
                rel_path = file_path.relative_to(directory)
                sha256_hash.update(str(rel_path).encode('utf-8'))
                
                # Add file content to hash
                with open(file_path, 'rb') as f:
                    sha256_hash.update(f.read())
        
        return sha256_hash.hexdigest()
    
    def create_template_archive(self, template_dir: Path) -> Optional[Path]:
        """Create a tar.gz archive of a template."""
        template_name = template_dir.name
        archive_path = self.archives_dir / f"{template_name}.tar.gz"
        
        try:
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(template_dir, arcname=template_name)
            
            return archive_path
        except Exception as e:
            click.echo(f"Error creating archive for {template_name}: {e}", err=True)
            return None
    
    def compute_archive_hash(self, archive_path: Path) -> str:
        """Compute SHA256 hash of an archive file."""
        sha256_hash = hashlib.sha256()
        with open(archive_path, 'rb') as f:
            sha256_hash.update(f.read())
        return sha256_hash.hexdigest()
    
    def create_manifest(self, template_archives: Dict[str, Path]) -> Dict[str, dict]:
        """Create a manifest of all template archives."""
        manifest = {}
        
        for template_name, archive_path in template_archives.items():
            if archive_path and archive_path.exists():
                # Compute hash of the original template directory
                template_dir = self.templates_dir / template_name
                directory_hash = self.compute_directory_hash(template_dir)
                
                # Compute hash of the archive
                archive_hash = self.compute_archive_hash(archive_path)
                
                # Get archive size
                archive_size = archive_path.stat().st_size
                
                manifest[template_name] = {
                    'version': '1.0.0',
                    'directory_hash': f"sha256:{directory_hash}",
                    'archive_hash': f"sha256:{archive_hash}",
                    'archive_size': archive_size,
                    'archive_path': str(archive_path.relative_to(self.templates_dir)),
                    'description': self.get_template_description(template_name)
                }
        
        return manifest
    
    def get_template_description(self, template_name: str) -> str:
        """Get description for a template."""
        descriptions = {
            'vector-store': 'Vector Store Manager with Python backend and Electron frontend',
            'lgmail': 'High-performance Gmail wrapper built with Electron'
        }
        return descriptions.get(template_name, f'{template_name} template')
    
    def package_all_templates(self) -> bool:
        """Package all templates into archives."""
        click.echo("🔧 Packaging templates into immutable archives...")
        
        template_dirs = self.get_template_directories()
        if not template_dirs:
            click.echo("No templates found to package", err=True)
            return False
        
        template_archives = {}
        
        for template_dir in template_dirs:
            template_name = template_dir.name
            click.echo(f"📦 Packaging {template_name}...")
            
            archive_path = self.create_template_archive(template_dir)
            if archive_path:
                template_archives[template_name] = archive_path
                click.echo(f"  ✓ Created {archive_path.name}")
            else:
                click.echo(f"  ❌ Failed to create archive for {template_name}", err=True)
        
        # Create manifest
        manifest = self.create_manifest(template_archives)
        manifest_path = self.archives_dir / "manifest.json"
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        click.echo(f"📋 Created manifest: {manifest_path}")
        
        # Display summary
        click.echo("\n📊 Packaging Summary:")
        for template_name, info in manifest.items():
            click.echo(f"  {template_name}:")
            click.echo(f"    Version: {info['version']}")
            click.echo(f"    Description: {info['description']}")
            click.echo(f"    Archive: {info['archive_path']}")
            click.echo(f"    Size: {info['archive_size']:,} bytes")
            click.echo(f"    Hash: {info['archive_hash']}")
            click.echo()
        
        return True
    
    def verify_archive_integrity(self, template_name: str) -> bool:
        """Verify the integrity of a template archive."""
        manifest_path = self.archives_dir / "manifest.json"
        if not manifest_path.exists():
            click.echo("Manifest not found. Run package_all_templates first.", err=True)
            return False
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        if template_name not in manifest:
            click.echo(f"Template {template_name} not found in manifest.", err=True)
            return False
        
        template_info = manifest[template_name]
        archive_path = self.archives_dir / template_info['archive_path']
        
        if not archive_path.exists():
            click.echo(f"Archive {archive_path} not found.", err=True)
            return False
        
        # Verify archive hash
        current_hash = self.compute_archive_hash(archive_path)
        expected_hash = template_info['archive_hash'].replace('sha256:', '')
        
        if current_hash == expected_hash:
            click.echo(f"✅ {template_name} archive integrity verified")
            return True
        else:
            click.echo(f"❌ {template_name} archive integrity check failed", err=True)
            return False


@click.command()
@click.option('--verify', '-v', help='Verify integrity of a specific template')
@click.option('--list', '-l', is_flag=True, help='List available templates')
def main(verify: Optional[str], list: bool):
    """Package mcli webapp templates into immutable archives."""
    templates_dir = Path(__file__).parent
    packager = TemplatePackager(templates_dir)
    
    if list:
        templates = packager.get_template_directories()
        click.echo("Available templates:")
        for template in templates:
            click.echo(f"  - {template.name}")
        return
    
    if verify:
        if packager.verify_archive_integrity(verify):
            return 0
        else:
            return 1
    
    # Package all templates
    if packager.package_all_templates():
        click.echo("✅ Template packaging completed successfully!")
        return 0
    else:
        click.echo("❌ Template packaging failed!", err=True)
        return 1


if __name__ == '__main__':
    main() 