import click
import os
import shutil
import subprocess
import json
import tarfile
import tempfile
from pathlib import Path
from typing import Optional, List
import re
from datetime import datetime

# Import the template manager
from .templates import get_template_manager


@click.group(name="webapp")
def webapp():
    """Web application generation and installation commands"""
    pass


def get_webapps_dir() -> Path:
    """Get the central webapps directory"""
    return Path.home() / ".local" / "mcli" / "webapps"


def ensure_webapps_dir() -> Path:
    """Ensure the webapps directory exists"""
    webapps_dir = get_webapps_dir()
    webapps_dir.mkdir(parents=True, exist_ok=True)
    return webapps_dir


def generate_default_name() -> str:
    """Generate a default application name using current timestamp"""
    return datetime.now().strftime("%Y%m%d.%H%M")


def find_app_by_name(app_name: str) -> Optional[Path]:
    """Find an application by name in the webapps directory"""
    webapps_dir = get_webapps_dir()
    if not webapps_dir.exists():
        return None
    
    # First try exact match
    app_dir = webapps_dir / app_name
    if app_dir.exists() and app_dir.is_dir():
        return app_dir
    
    # Then try partial match
    for potential_dir in webapps_dir.iterdir():
        if potential_dir.is_dir():
            app_info = get_app_info(potential_dir)
            if app_info and app_info['name'] == app_name:
                return potential_dir
    
    return None


def get_latest_app() -> Optional[Path]:
    """Get the most recently created application"""
    webapps_dir = get_webapps_dir()
    if not webapps_dir.exists():
        return None
    
    apps = []
    for app_dir in webapps_dir.iterdir():
        if app_dir.is_dir():
            app_info = get_app_info(app_dir)
            if app_info:
                app_info['path'] = app_dir
                apps.append(app_info)
    
    if not apps:
        return None
    
    # Sort by creation time (newest first)
    apps.sort(key=lambda x: x['created'], reverse=True)
    return apps[0]['path']


def get_app_info(app_dir: Path) -> dict:
    """Get information about a webapp from its package.json"""
    package_json = app_dir / "package.json"
    if not package_json.exists():
        return {}
    
    try:
        with open(package_json, 'r') as f:
            data = json.load(f)
        
        return {
            'name': data.get('name', app_dir.name),
            'description': data.get('description', ''),
            'version': data.get('version', ''),
            'url': 'Unknown',  # We'll need to extract this from main.js
            'created': app_dir.stat().st_ctime if app_dir.exists() else 0,
            'modified': app_dir.stat().st_mtime if app_dir.exists() else 0
        }
    except Exception:
        return {}


def extract_url_from_main_js(app_dir: Path) -> str:
    """Extract the target URL from main.js"""
    main_js = app_dir / "main.js"
    if not main_js.exists():
        return "Unknown"
    
    try:
        with open(main_js, 'r') as f:
            content = f.read()
        
        # Look for the URL in the loadURL call
        import re
        match = re.search(r'loadURL\("([^"]+)"', content)
        if match:
            return match.group(1)
        
        return "Unknown"
    except Exception:
        return "Unknown"


def auto_fix_electron_installation(app_path: Path) -> bool:
    """Automatically fix common Electron installation issues"""
    click.echo("🔧 Auto-fixing Electron installation...")
    
    try:
        # Change to the app directory
        original_dir = os.getcwd()
        os.chdir(app_path)
        
        # Step 1: Clean up corrupted Electron installation
        electron_path = app_path / "node_modules" / "electron"
        electron_bin = app_path / "node_modules" / ".bin" / "electron"
        
        if electron_path.exists():
            click.echo("  Cleaning up corrupted Electron installation...")
            try:
                shutil.rmtree(electron_path)
                click.echo("  ✓ Removed corrupted Electron")
            except Exception as e:
                click.echo(f"  ⚠ Could not remove Electron: {e}")
        
        if electron_bin.exists():
            try:
                electron_bin.unlink()
                click.echo("  ✓ Removed corrupted Electron binary")
            except Exception as e:
                click.echo(f"  ⚠ Could not remove Electron binary: {e}")
        
        # Step 2: Clear npm cache for Electron
        click.echo("  Clearing npm cache for Electron...")
        try:
            subprocess.run(['npm', 'cache', 'clean', '--force'], 
                         capture_output=True, text=True, check=True)
            click.echo("  ✓ Cleared npm cache")
        except subprocess.CalledProcessError:
            click.echo("  ⚠ Could not clear npm cache")
        
        # Step 3: Reinstall Electron with specific version
        click.echo("  Reinstalling Electron...")
        try:
            # First try to install a specific stable version
            subprocess.run(['npm', 'install', 'electron@^28.0.0', '--save-dev', '--force'], 
                         capture_output=True, text=True, check=True)
            click.echo("  ✓ Installed Electron v28")
        except subprocess.CalledProcessError:
            click.echo("  ⚠ Failed to install specific version, trying latest...")
            try:
                subprocess.run(['npm', 'install', 'electron', '--save-dev', '--force'], 
                             capture_output=True, text=True, check=True)
                click.echo("  ✓ Installed latest Electron")
            except subprocess.CalledProcessError as e:
                click.echo(f"  ❌ Failed to install Electron: {e}")
                return False
        
        # Step 4: Verify Electron installation
        electron_path = app_path / "node_modules" / "electron"
        electron_dist = electron_path / "dist"
        
        if not electron_path.exists():
            click.echo("  ❌ Electron not found after installation")
            return False
        
        if not electron_dist.exists():
            click.echo("  ⚠ Electron dist directory missing, attempting to download...")
            try:
                # Try to trigger Electron download
                subprocess.run(['npx', 'electron', '--version'], 
                             capture_output=True, text=True, timeout=30)
                click.echo("  ✓ Electron download triggered")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                click.echo("  ⚠ Electron download failed, but continuing...")
        
        # Step 5: Fix package.json scripts if needed
        package_json = app_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    package_data = json.load(f)
                
                scripts = package_data.get('scripts', {})
                needs_update = False
                
                # Ensure dev script exists and uses correct Electron path
                if 'dev' not in scripts:
                    scripts['dev'] = 'electron . --dev'
                    needs_update = True
                    click.echo("  ✓ Added missing dev script")
                
                if needs_update:
                    package_data['scripts'] = scripts
                    with open(package_json, 'w') as f:
                        json.dump(package_data, f, indent=2)
                    click.echo("  ✓ Updated package.json scripts")
                
            except Exception as e:
                click.echo(f"  ⚠ Could not update package.json: {e}")
        
        click.echo("✅ Electron installation auto-fix completed")
        return True
        
    except Exception as e:
        click.echo(f"❌ Auto-fix failed: {e}")
        return False
    finally:
        # Change back to original directory
        os.chdir(original_dir)


@webapp.command()
@click.option('--url', help='URL of the web application to wrap (for webmail template)')
@click.option('--name', help='Name of the application (defaults to current timestamp YYYYMMDD.HHMM)')
@click.option('--icon', help='Path to the icon file (.icns for macOS)')
@click.option('--output-dir', help='Output directory for the generated app (defaults to central webapps directory)')
@click.option('--install', is_flag=True, help='Install the app after generation')
@click.option('--template', type=click.Choice(['webmail', 'vector-store', 'my-vector-store']), default='vector-store', help='Template to use for generation')
def generate(url: str, name: Optional[str], icon: Optional[str], output_dir: Optional[str], install: bool, template: str):
    """Generate a template web application based on available templates"""
    
    # Use default name if not provided
    if name is None:
        name = generate_default_name()
        click.echo(f"Using default name: {name}")
    
    # Sanitize name for filesystem
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    
    # Use central webapps directory if no output directory specified
    if output_dir is None:
        webapps_dir = ensure_webapps_dir()
        output_path = webapps_dir / safe_name
    else:
        output_path = Path(output_dir) / safe_name
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"Generating web application '{name}' using {template} template")
    click.echo(f"Output directory: {output_path}")
    
    try:
        if template == 'webmail':
            generate_webmail_app(url, name, safe_name, output_path, icon)
        elif template == 'vector-store':
            generate_vector_store_app(name, safe_name, output_path, icon)
        elif template == 'my-vector-store':
            generate_my_vector_store_app(name, safe_name, output_path, icon)
        
        if install:
            click.echo("Installing the generated application...")
            install_app(str(output_path))
        
        click.echo(f"✓ Successfully generated '{name}' application")
        
    except Exception as e:
        click.echo(f"Error generating application: {e}", err=True)
        return


def generate_webmail_app(url: str, name: str, safe_name: str, output_path: Path, icon: Optional[str]):
    """Generate application using webmail template"""
    # Validate URL
    if not url or not url.startswith(('http://', 'https://')):
        click.echo("Error: URL must start with http:// or https://", err=True)
        return
    
    # Get template from embedded templates
    template_manager = get_template_manager()
    template_dir = template_manager.get_template_path('webmail')
    if not template_dir:
        click.echo("Error: webmail template not found in embedded templates", err=True)
        return
    
    # Files to copy
    files_to_copy = [
        'main.js', 'preload.js', 'renderer.js', 'index.html', 
        'styles.css', 'webpack.main.config.js', 'webpack.renderer.config.js',
        'electron.config.js', '.gitignore', '.nvmrc', '.env'
    ]
    
    for file_name in files_to_copy:
        src_file = template_dir / file_name
        dst_file = output_path / file_name
        if src_file.exists():
            shutil.copy2(src_file, dst_file)
            click.echo(f"  ✓ Copied {file_name}")
    
    # Copy package.json and modify it
    package_json_src = template_dir / "package.json"
    if package_json_src.exists():
        with open(package_json_src, 'r') as f:
            package_data = json.load(f)
        
        # Update package.json for the new app
        package_data['name'] = safe_name.lower()
        package_data['description'] = f"A high-performance {name} wrapper built with Electron"
        package_data['main'] = "main.js"
        
        # Update scripts
        package_data['scripts']['package'] = f"npm run build && electron-packager dist {safe_name} --platform=darwin --arch=x64 --app-version=1.0.0 --overwrite --icon={safe_name}_icon.icns --ignore=node_modules/electron-packager --out=build --prune=true"
        package_data['scripts']['link'] = f"ln -fs build/{safe_name}-darwin-x64/{safe_name}.app /Applications/{safe_name}.app"
        package_data['scripts']['distribute'] = f"npm run build && npm run package && npm run link"
        
        # Update repository URL
        package_data['repository']['url'] = f"https://github.com/yourusername/{safe_name}.git"
        
        # Update keywords
        package_data['keywords'] = [
            "Electron", name, "Desktop", "App", "Web", "Wrapper"
        ]
        
        with open(output_path / "package.json", 'w') as f:
            json.dump(package_data, f, indent=2)
        
        click.echo("  ✓ Created package.json")
    
    # Copy icon if provided
    if icon:
        icon_path = Path(icon)
        if icon_path.exists():
            dst_icon = output_path / f"{safe_name}_icon.icns"
            shutil.copy2(icon_path, dst_icon)
            click.echo(f"  ✓ Copied icon: {icon}")
        else:
            click.echo(f"  ⚠ Icon file not found: {icon}", err=True)
    
    # Modify main.js for the new app
    main_js_path = output_path / "main.js"
    if main_js_path.exists():
        with open(main_js_path, 'r') as f:
            main_js_content = f.read()
        
        # Replace Gmail-specific content with generic content
        main_js_content = main_js_content.replace(
            'https://mail.google.com/mail/u/0/#inbox',
            url
        )
        main_js_content = main_js_content.replace(
            'Gmail - luis.e',
            f'{name} - {safe_name}'
        )
        main_js_content = main_js_content.replace(
            'Gmail',
            name
        )
        main_js_content = main_js_content.replace(
            'luis-gmail',
            f'{safe_name}-app'
        )
        main_js_content = main_js_content.replace(
            'persist:gmail',
            f'persist:{safe_name}'
        )
        
        with open(main_js_path, 'w') as f:
            f.write(main_js_content)
        
        click.echo("  ✓ Updated main.js")
    
    # Modify index.html for the new app
    index_html_path = output_path / "index.html"
    if index_html_path.exists():
        with open(index_html_path, 'r') as f:
            html_content = f.read()
        
        # Replace Gmail-specific content
        html_content = html_content.replace(
            'High-performance Gmail wrapper built with Electron',
            f'High-performance {name} wrapper built with Electron'
        )
        html_content = html_content.replace(
            'Gmail - lefv',
            f'{name} - {safe_name}'
        )
        html_content = html_content.replace(
            'Gmail',
            name
        )
        html_content = html_content.replace(
            'Loading your inbox...',
            f'Loading {name}...'
        )
        html_content = html_content.replace(
            'Please wait while we connect to your account',
            f'Please wait while we connect to {name}'
        )
        
        # Update icon reference
        if icon:
            html_content = html_content.replace(
                './lefv_app_icon.icns',
                f'./{safe_name}_icon.icns'
            )
        
        with open(index_html_path, 'w') as f:
            f.write(html_content)
        
        click.echo("  ✓ Updated index.html")


def generate_vector_store_app(name: str, safe_name: str, output_path: Path, icon: Optional[str]):
    """Generate vector store application"""
    # Get template from embedded templates
    template_manager = get_template_manager()
    template_dir = template_manager.get_template_path('vector-store')
    if not template_dir:
        click.echo("Error: vector-store template not found in embedded templates", err=True)
        return
    
    # Copy all files from template
    for item in template_dir.rglob('*'):
        if item.is_file():
            # Calculate relative path from template directory
            rel_path = item.relative_to(template_dir)
            dst_path = output_path / rel_path
            
            # Create parent directories if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(item, dst_path)
            click.echo(f"  ✓ Copied {rel_path}")
    
    # Update package.json for the new app
    package_json_path = output_path / "package.json"
    if package_json_path.exists():
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)
        
        # Update package.json for the new app
        package_data['name'] = safe_name.lower()
        package_data['description'] = f"Vector Store Manager for {name}"
        package_data['productName'] = f"{name} Vector Store"
        
        # Update build configuration
        package_data['build']['appId'] = f"com.mcli.{safe_name}"
        package_data['build']['productName'] = f"{name} Vector Store"
        
        with open(package_json_path, 'w') as f:
            json.dump(package_data, f, indent=2)
        
        click.echo("  ✓ Updated package.json")
    
    # Copy icon if provided
    if icon:
        icon_path = Path(icon)
        if icon_path.exists():
            dst_icon = output_path / "assets" / "icon.png"
            dst_icon.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(icon_path, dst_icon)
            click.echo(f"  ✓ Copied icon: {icon}")
        else:
            click.echo(f"  ⚠ Icon file not found: {icon}", err=True)
    
    click.echo("  ✓ Vector Store application generated successfully")
    click.echo("  ✓ Run './install.sh' to set up the Python environment and dependencies")


def generate_my_vector_store_app(name: str, safe_name: str, output_path: Path, icon: Optional[str]):
    """Generate My_Vector_Store application"""
    # Get template from embedded templates (use vector-store as base)
    template_manager = get_template_manager()
    template_dir = template_manager.get_template_path('vector-store')
    if not template_dir:
        click.echo("Error: vector-store template not found in embedded templates", err=True)
        return
    
    # Copy all files from template
    for item in template_dir.rglob('*'):
        if item.is_file():
            # Calculate relative path from template directory
            rel_path = item.relative_to(template_dir)
            dst_path = output_path / rel_path
            
            # Create parent directories if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(item, dst_path)
            click.echo(f"  ✓ Copied {rel_path}")
    
    # Update package.json for the new app
    package_json_path = output_path / "package.json"
    if package_json_path.exists():
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)
        
        # Update package.json for the new app
        package_data['name'] = safe_name.lower()
        package_data['description'] = f"Vector Store Manager for {name}"
        package_data['productName'] = f"{name} Vector Store"
        
        # Update build configuration
        package_data['build']['appId'] = f"com.mcli.{safe_name}"
        package_data['build']['productName'] = f"{name} Vector Store"
        
        # Remove better-sqlite3 and keep only sqlite3 for compatibility with Express backend
        if 'better-sqlite3' in package_data.get('dependencies', {}):
            package_data['dependencies'].pop('better-sqlite3')
            click.echo("  ✓ Removed better-sqlite3 dependency for Express backend compatibility")
        
        # Ensure sqlite3 is present
        if 'sqlite3' not in package_data.get('dependencies', {}):
            package_data['dependencies']['sqlite3'] = '^5.1.6'
            click.echo("  ✓ Added sqlite3 dependency for Express backend compatibility")
        
        with open(package_json_path, 'w') as f:
            json.dump(package_data, f, indent=2)
        
        click.echo("  ✓ Updated package.json")
    
    # Copy icon if provided
    if icon:
        icon_path = Path(icon)
        if icon_path.exists():
            dst_icon = output_path / "assets" / "icon.png"
            dst_icon.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(icon_path, dst_icon)
            click.echo(f"  ✓ Copied icon: {icon}")
        else:
            click.echo(f"  ⚠ Icon file not found: {icon}", err=True)
    
    click.echo("  ✓ Vector Store application generated successfully")
    click.echo("  ✓ Run './install.sh' to set up the Python environment and dependencies")


def install_app(app_dir: str):
    """Install a generated web application"""
    app_path = Path(app_dir)
    if not app_path.exists():
        click.echo(f"Error: Application directory not found: {app_dir}", err=True)
        return
    
    # Check if it's a vector store app
    if (app_path / "python" / "requirements.txt").exists():
        click.echo("Detected vector store application, running installation script...")
        try:
            # Run the installation script
            result = subprocess.run(
                ["./install.sh"],
                cwd=app_path,
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.returncode == 0:
                click.echo("✓ Vector store application installed successfully")
                click.echo("You can now run the application with: ./start.sh")
            else:
                click.echo(f"Installation failed: {result.stderr}", err=True)
                
        except Exception as e:
            click.echo(f"Error running installation script: {e}", err=True)
    else:
        # Standard npm install for other apps
        click.echo("Installing Node.js dependencies...")
        try:
            # First install without scripts to avoid native compilation issues
            result = subprocess.run(
                ["npm", "install", "--ignore-scripts"],
                cwd=app_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                click.echo("✓ Dependencies installed successfully (without native modules)")
                click.echo("Note: Some native modules may need manual installation")
            else:
                click.echo(f"Installation failed: {result.stderr}", err=True)
                return
                
        except Exception as e:
            click.echo(f"Error installing dependencies: {e}", err=True)
            return
        
        # Auto-fix Electron installation after npm install
        click.echo("Auto-fixing Electron installation...")
        if auto_fix_electron_installation(app_path):
            click.echo("✓ Application ready to run")
        else:
            click.echo("⚠ Electron installation may need manual fixing")
            click.echo("Run 'mcli workflow webapp fix-electron' if you encounter issues")


@webapp.command()
@click.argument('app-dir', type=click.Path(exists=True))
def install(app_dir: str):
    """Install a generated web application"""
    
    app_path = Path(app_dir)
    install_script = app_path / "install.sh"
    
    if not install_script.exists():
        click.echo("Error: install.sh not found in the specified directory", err=True)
        return
    
    click.echo(f"Installing application from: {app_path}")
    
    try:
        # Change to the app directory
        original_dir = os.getcwd()
        os.chdir(app_path)
        
        # Run installation script
        result = subprocess.run(['./install.sh'], capture_output=True, text=True)
        
        if result.returncode == 0:
            click.echo("✅ Application installed successfully!")
        else:
            click.echo(f"❌ Installation failed: {result.stderr}", err=True)
            
    except Exception as e:
        click.echo(f"❌ Installation error: {e}", err=True)
    finally:
        # Change back to original directory
        os.chdir(original_dir)


@webapp.command()
@click.argument('app-identifier', required=False)
@click.option('--latest', '-l', is_flag=True, help='Run the most recently created application')
def run(app_identifier: Optional[str], latest: bool):
    """Run a generated web application in development mode"""
    
    app_path = None
    
    if latest:
        app_path = get_latest_app()
        if app_path is None:
            click.echo("Error: No applications found", err=True)
            return
        click.echo(f"Running latest application: {app_path.name}")
    elif app_identifier:
        # Try to find the app by name or path
        if Path(app_identifier).exists():
            app_path = Path(app_identifier)
        else:
            app_path = find_app_by_name(app_identifier)
        
        if app_path is None:
            click.echo(f"Error: Application '{app_identifier}' not found", err=True)
            click.echo("Use 'list' to see available applications")
            return
    else:
        # No identifier provided, try to run the latest
        app_path = get_latest_app()
        if app_path is None:
            click.echo("Error: No applications found", err=True)
            click.echo("Use 'generate' to create your first application")
            return
        click.echo(f"Running latest application: {app_path.name}")
    
    package_json = app_path / "package.json"
    
    if not package_json.exists():
        click.echo("Error: package.json not found in the specified directory", err=True)
        return
    
    click.echo(f"Running application from: {app_path}")
    
    try:
        # Change to the app directory
        original_dir = os.getcwd()
        os.chdir(app_path)
        
        # Check if node_modules exists, if not install dependencies
        if not (app_path / "node_modules").exists():
            click.echo("Installing dependencies...")
            subprocess.run(['npm', 'install', '--ignore-scripts'], check=True)
        
        # Ensure Electron is properly installed
        electron_path = app_path / "node_modules" / "electron"
        if not electron_path.exists() or not (electron_path / "dist").exists():
            click.echo("Electron installation incomplete, running auto-fix...")
            if not auto_fix_electron_installation(app_path):
                click.echo("❌ Failed to fix Electron installation", err=True)
                return
        
        # Try to run the application
        click.echo("Starting application...")
        try:
            subprocess.run(['npm', 'run', 'dev'], check=True)
        except subprocess.CalledProcessError as e:
            # If the first attempt fails, try auto-fixing Electron
            if "Cannot find module" in str(e) or "MODULE_NOT_FOUND" in str(e):
                click.echo("⚠️  Electron module error detected, attempting auto-fix...")
                if auto_fix_electron_installation(app_path):
                    click.echo("Retrying application startup...")
                    subprocess.run(['npm', 'run', 'dev'], check=True)
                else:
                    raise e
            else:
                raise e
        
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Error running application: {e}", err=True)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
    finally:
        # Change back to original directory
        os.chdir(original_dir)


@webapp.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
def list(verbose: bool):
    """List all generated web applications"""
    
    webapps_dir = get_webapps_dir()
    
    if not webapps_dir.exists():
        click.echo("No web applications found. Use 'generate' to create your first app.")
        return
    
    apps = []
    for app_dir in webapps_dir.iterdir():
        if app_dir.is_dir():
            app_info = get_app_info(app_dir)
            if app_info:
                app_info['url'] = extract_url_from_main_js(app_dir)
                app_info['path'] = app_dir
                apps.append(app_info)
    
    if not apps:
        click.echo("No web applications found. Use 'generate' to create your first app.")
        return
    
    # Sort by creation time (newest first)
    apps.sort(key=lambda x: x['created'], reverse=True)
    
    click.echo(f"Found {len(apps)} web application(s):")
    click.echo()
    
    for i, app in enumerate(apps):
        # Mark the latest app
        latest_indicator = " 🆕" if i == 0 else ""
        click.echo(f"📱 {app['name']}{latest_indicator}")
        click.echo(f"   Description: {app['description']}")
        click.echo(f"   URL: {app['url']}")
        click.echo(f"   Version: {app['version']}")
        
        if verbose:
            created = datetime.fromtimestamp(app['created']).strftime('%Y-%m-%d %H:%M:%S')
            modified = datetime.fromtimestamp(app['modified']).strftime('%Y-%m-%d %H:%M:%S')
            click.echo(f"   Created: {created}")
            click.echo(f"   Modified: {modified}")
            click.echo(f"   Path: {app['path']}")
        
        click.echo()


@webapp.command()
@click.argument('app-name', type=str)
@click.option('--force', '-f', is_flag=True, help='Force deletion without confirmation')
def delete(app_name: str, force: bool):
    """Delete a generated web application"""
    
    webapps_dir = get_webapps_dir()
    
    if not webapps_dir.exists():
        click.echo("No web applications found.")
        return
    
    # Find the app by name
    app_dir = None
    for potential_dir in webapps_dir.iterdir():
        if potential_dir.is_dir():
            app_info = get_app_info(potential_dir)
            if app_info and app_info['name'] == app_name:
                app_dir = potential_dir
                break
    
    if not app_dir:
        click.echo(f"Error: Web application '{app_name}' not found.")
        click.echo("Use 'list' to see available applications.")
        return
    
    app_info = get_app_info(app_dir)
    app_url = extract_url_from_main_js(app_dir)
    
    if not force:
        click.echo(f"Are you sure you want to delete '{app_name}'?")
        click.echo(f"   Description: {app_info.get('description', 'N/A')}")
        click.echo(f"   URL: {app_url}")
        click.echo(f"   Path: {app_dir}")
        click.echo()
        
        if not click.confirm("This action cannot be undone. Continue?"):
            click.echo("Deletion cancelled.")
            return
    
    try:
        # Check if the app is installed in Applications
        app_name_safe = re.sub(r'[^a-zA-Z0-9._-]', '_', app_info.get('name', app_name))
        installed_app = Path(f"/Applications/{app_name_safe}.app")
        
        if installed_app.exists():
            click.echo(f"⚠️  Found installed app at {installed_app}")
            if not force and not click.confirm("Remove the installed app as well?"):
                click.echo("Keeping installed app. Only removing source files.")
            else:
                try:
                    # Remove the symlink or app
                    if installed_app.is_symlink():
                        installed_app.unlink()
                    else:
                        shutil.rmtree(installed_app)
                    click.echo(f"✅ Removed installed app from {installed_app}")
                except Exception as e:
                    click.echo(f"⚠️  Could not remove installed app: {e}")
        
        # Remove the source directory
        shutil.rmtree(app_dir)
        click.echo(f"✅ Successfully deleted web application '{app_name}'")
        
    except Exception as e:
        click.echo(f"❌ Error deleting application: {e}", err=True)


@webapp.command()
@click.argument('app-name', type=str)
@click.option('--test-type', type=click.Choice(['basic', 'advanced', 'api', 'ui', 'all']), default='all', help='Type of tests to run')
@click.option('--report', '-r', is_flag=True, help='Generate test report')
@click.option('--check', '-c', is_flag=True, help='Check environment only')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def test(app_name: str, test_type: str, report: bool, check: bool, verbose: bool):
    """Run Puppeteer tests for a generated web application"""
    
    webapps_dir = get_webapps_dir()
    
    if not webapps_dir.exists():
        click.echo("No web applications found.")
        return
    
    # Find the app by name
    app_dir = None
    for potential_dir in webapps_dir.iterdir():
        if potential_dir.is_dir():
            app_info = get_app_info(potential_dir)
            if app_info and app_info['name'] == app_name:
                app_dir = potential_dir
                break
    
    if not app_dir:
        click.echo(f"Error: Web application '{app_name}' not found.")
        click.echo("Use 'list' to see available applications.")
        return
    
    # Check if test directory exists
    test_dir = app_dir / "test"
    if not test_dir.exists():
        click.echo(f"Error: Test directory not found for '{app_name}'.")
        click.echo("This application may not support testing.")
        return
    
    test_runner = test_dir / "run-tests.sh"
    if not test_runner.exists():
        click.echo(f"Error: Test runner not found for '{app_name}'.")
        click.echo("This application may not support testing.")
        return
    
    click.echo(f"Running tests for '{app_name}'...")
    click.echo(f"Test type: {test_type}")
    click.echo(f"App directory: {app_dir}")
    
    try:
        # Change to the app directory
        original_dir = os.getcwd()
        os.chdir(app_dir)
        
        # Build command arguments
        cmd = [str(test_runner)]
        
        if report:
            cmd.append('--report')
        
        if check:
            cmd.append('--check')
        
        if verbose:
            cmd.append('--verbose')
        
        if test_type != 'all':
            cmd.append(test_type)
        
        # Run the test runner
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            click.echo("✅ Tests completed successfully!")
            if result.stdout:
                click.echo(result.stdout)
        else:
            click.echo(f"❌ Tests failed: {result.stderr}", err=True)
            if result.stdout:
                click.echo(result.stdout)
            
    except Exception as e:
        click.echo(f"❌ Error running tests: {e}", err=True)
    finally:
        # Change back to original directory
        os.chdir(original_dir)


@webapp.command()
@click.argument('app-dir', type=click.Path(exists=True))
def install_native_deps(app_dir: str):
    """Install native dependencies for a generated web application"""
    
    app_path = Path(app_dir)
    package_json = app_path / "package.json"
    
    if not package_json.exists():
        click.echo("Error: package.json not found in the specified directory", err=True)
        return
    
    click.echo(f"Installing native dependencies for: {app_path}")
    
    try:
        # Change to the app directory
        original_dir = os.getcwd()
        os.chdir(app_path)
        
        # Check if node_modules exists
        if not (app_path / "node_modules").exists():
            click.echo("Installing all dependencies first...")
            subprocess.run(['npm', 'install', '--ignore-scripts'], check=True)
        
        # Try to install native dependencies with specific focus on sqlite3
        click.echo("Installing native dependencies...")
        try:
            # First try to rebuild sqlite3 specifically
            click.echo("Rebuilding sqlite3...")
            subprocess.run(['npm', 'rebuild', 'sqlite3'], check=True)
            click.echo("✓ sqlite3 rebuilt successfully")
        except subprocess.CalledProcessError:
            click.echo("⚠ sqlite3 rebuild failed, trying alternative approach...")
            try:
                # Try installing sqlite3 with specific flags
                subprocess.run(['npm', 'install', 'sqlite3', '--build-from-source'], check=True)
                click.echo("✓ sqlite3 installed from source")
            except subprocess.CalledProcessError:
                click.echo("⚠ sqlite3 installation failed, trying better-sqlite3...")
                try:
                    # Try installing better-sqlite3 as alternative
                    subprocess.run(['npm', 'uninstall', 'sqlite3'], check=True)
                    subprocess.run(['npm', 'install', 'better-sqlite3', '--ignore-scripts'], check=True)
                    click.echo("✓ Installed better-sqlite3 as alternative")
                except subprocess.CalledProcessError:
                    click.echo("⚠ Native SQLite installation failed")
                    click.echo("The application may have limited functionality")
        
        # Try to rebuild other native dependencies
        try:
            subprocess.run(['npm', 'rebuild'], check=True)
            click.echo("✓ Other native dependencies rebuilt successfully")
        except subprocess.CalledProcessError:
            click.echo("⚠ Some native dependencies failed to rebuild")
            click.echo("This is normal for some packages on certain systems")
        
        # Ensure Electron is properly installed
        electron_path = app_path / "node_modules" / "electron"
        if not electron_path.exists() or not (electron_path / "dist").exists():
            click.echo("Reinstalling Electron...")
            subprocess.run(['npm', 'install', 'electron', '--save-dev'], check=True)
            click.echo("✓ Electron reinstalled successfully")
        
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Error installing native dependencies: {e}", err=True)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
    finally:
        # Change back to original directory
        os.chdir(original_dir)


@webapp.command()
@click.argument('app-dir', type=click.Path(exists=True))
def fix_sqlite3(app_dir: str):
    """Fix SQLite3 native binding issues in a generated web application"""
    
    app_path = Path(app_dir)
    package_json = app_path / "package.json"
    
    if not package_json.exists():
        click.echo("Error: package.json not found in the specified directory", err=True)
        return
    
    click.echo(f"Fixing SQLite3 issues for: {app_path}")
    
    try:
        # Change to the app directory
        original_dir = os.getcwd()
        os.chdir(app_path)
        
        # Check if sqlite3 is in dependencies
        with open(package_json, 'r') as f:
            package_data = json.load(f)
        
        if 'sqlite3' in package_data.get('dependencies', {}):
            click.echo("Found sqlite3 dependency, replacing with better-sqlite3...")
            
            # Remove sqlite3 and install better-sqlite3
            subprocess.run(['npm', 'uninstall', 'sqlite3'], check=True)
            subprocess.run(['npm', 'install', 'better-sqlite3@^9.2.2'], check=True)
            
            # Update package.json
            sqlite3_version = package_data['dependencies'].pop('sqlite3')
            package_data['dependencies']['better-sqlite3'] = '^9.2.2'
            
            with open(package_json, 'w') as f:
                json.dump(package_data, f, indent=2)
            
            click.echo("✓ Successfully replaced sqlite3 with better-sqlite3")
        else:
            click.echo("No sqlite3 dependency found, checking for better-sqlite3...")
            if 'better-sqlite3' not in package_data.get('dependencies', {}):
                click.echo("Installing better-sqlite3...")
                subprocess.run(['npm', 'install', 'better-sqlite3@^9.2.2'], check=True)
                click.echo("✓ Installed better-sqlite3")
            else:
                click.echo("✓ better-sqlite3 already installed")
        
        # Update JavaScript files to use better-sqlite3 instead of sqlite3
        js_files_to_update = ['main.js', 'renderer.js']
        for js_file in js_files_to_update:
            js_path = app_path / js_file
            if js_path.exists():
                with open(js_path, 'r') as f:
                    content = f.read()
                
                # Replace sqlite3 require statements with better-sqlite3
                if 'sqlite3' in content:
                    content = content.replace(
                        "const sqlite3 = require('sqlite3').verbose();",
                        "const Database = require('better-sqlite3');"
                    )
                    content = content.replace(
                        "new sqlite3.Database(",
                        "new Database("
                    )
                    content = content.replace(
                        "sqlite3.OPEN_READWRITE",
                        "Database.OPEN_READWRITE"
                    )
                    content = content.replace(
                        "sqlite3.OPEN_CREATE",
                        "Database.OPEN_CREATE"
                    )
                    
                    with open(js_path, 'w') as f:
                        f.write(content)
                    
                    click.echo(f"✓ Updated {js_file} to use better-sqlite3")
        
        # Try to rebuild if node_modules exists
        if (app_path / "node_modules").exists():
            click.echo("Rebuilding native dependencies...")
            try:
                subprocess.run(['npm', 'rebuild'], check=True)
                click.echo("✓ Native dependencies rebuilt successfully")
            except subprocess.CalledProcessError:
                click.echo("⚠ Some native dependencies failed to rebuild")
                click.echo("This is normal and the application should still work")
        
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Error fixing SQLite3: {e}", err=True)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
    finally:
        # Change back to original directory
        os.chdir(original_dir)


@webapp.command()
@click.argument('app-identifier', required=False)
@click.option('--latest', '-l', is_flag=True, help='Fix the most recently created application')
def fix_electron(app_identifier: Optional[str], latest: bool):
    """Automatically fix Electron installation issues in a generated web application"""
    
    app_path = None
    
    if latest:
        app_path = get_latest_app()
        if app_path is None:
            click.echo("Error: No applications found", err=True)
            return
        click.echo(f"Fixing latest application: {app_path.name}")
    elif app_identifier:
        # Try to find the app by name or path
        if Path(app_identifier).exists():
            app_path = Path(app_identifier)
        else:
            app_path = find_app_by_name(app_identifier)
        
        if app_path is None:
            click.echo(f"Error: Application '{app_identifier}' not found", err=True)
            click.echo("Use 'list' to see available applications")
            return
    else:
        # No identifier provided, try to fix the latest
        app_path = get_latest_app()
        if app_path is None:
            click.echo("Error: No applications found", err=True)
            click.echo("Use 'generate' to create your first application")
            return
        click.echo(f"Fixing latest application: {app_path.name}")
    
    package_json = app_path / "package.json"
    
    if not package_json.exists():
        click.echo("Error: package.json not found in the specified directory", err=True)
        return
    
    click.echo(f"Fixing Electron installation for: {app_path}")
    
    if auto_fix_electron_installation(app_path):
        click.echo("✅ Electron installation fixed successfully!")
        click.echo("You can now run the application with: mcli workflow webapp run")
    else:
        click.echo("❌ Failed to fix Electron installation", err=True)


@webapp.command()
@click.argument('app-identifier', required=False)
@click.option('--latest', '-l', is_flag=True, help='Hard reinstall the most recently created application')
@click.option('--force', '-f', is_flag=True, help='Force deletion without confirmation')
def hard_reinstall(app_identifier: Optional[str], latest: bool, force: bool):
    """Hard reinstall a generated web application (delete node_modules, lock files, venv, cache, and reinstall)"""
    import shutil
    import glob
    import getpass
    
    app_path = None
    if latest:
        app_path = get_latest_app()
        if app_path is None:
            click.echo("Error: No applications found", err=True)
            return
        click.echo(f"Hard reinstalling latest application: {app_path.name}")
    elif app_identifier:
        if Path(app_identifier).exists():
            app_path = Path(app_identifier)
        else:
            app_path = find_app_by_name(app_identifier)
        if app_path is None:
            click.echo(f"Error: Application '{app_identifier}' not found", err=True)
            click.echo("Use 'list' to see available applications")
            return
    else:
        app_path = get_latest_app()
        if app_path is None:
            click.echo("Error: No applications found", err=True)
            click.echo("Use 'generate' to create your first application")
            return
        click.echo(f"Hard reinstalling latest application: {app_path.name}")

    # Confirm with user
    if not force:
        click.echo(f"This will DELETE the following in {app_path}:")
        click.echo("  - node_modules/")
        click.echo("  - package-lock.json")
        click.echo("  - .venv/")
        click.echo("  - build/ and dist/ (if present)")
        click.echo("  - Electron cache and userData (if present)")
        click.echo("  - Reinstall all dependencies")
        click.echo()
        if not click.confirm("Continue?"):
            click.echo("Cancelled.")
            return

    # Delete node_modules
    nm = app_path / "node_modules"
    if nm.exists():
        click.echo("Deleting node_modules...")
        shutil.rmtree(nm)
    # Delete package-lock.json
    plock = app_path / "package-lock.json"
    if plock.exists():
        click.echo("Deleting package-lock.json...")
        plock.unlink()
    # Delete .venv
    venv = app_path / "python" / ".venv"
    if venv.exists():
        click.echo("Deleting python/.venv...")
        shutil.rmtree(venv)
    # Delete build/ and dist/
    for d in ["build", "dist"]:
        dpath = app_path / d
        if dpath.exists():
            click.echo(f"Deleting {d}/ directory...")
            shutil.rmtree(dpath)
    # Delete Electron cache/userData
    user = getpass.getuser()
    app_name = app_path.name
    user_data_dir = Path.home() / "Library" / "Application Support" / f"{app_name} Vector Store"
    if user_data_dir.exists():
        click.echo(f"Deleting Electron userData: {user_data_dir}")
        shutil.rmtree(user_data_dir)
    # Reinstall
    install_sh = app_path / "install.sh"
    if install_sh.exists():
        click.echo("Running install.sh...")
        subprocess.run(["bash", str(install_sh)], cwd=app_path)
    else:
        click.echo("Running npm install --ignore-scripts...")
        subprocess.run(["npm", "install", "--ignore-scripts"], cwd=app_path)
        click.echo("Auto-fixing Electron installation...")
        auto_fix_electron_installation(app_path)
    click.echo("✅ Hard reinstall complete. You can now run the app again.")


@webapp.command()
@click.option('--template', type=click.Choice(['webmail', 'vector-store', 'my-vector-store']), default='vector-store', help='Template to use for generation')
@click.option('--url', help='URL of the web application to wrap (for webmail template)')
@click.option('--icon', help='Path to the icon file (.icns for macOS)')
@click.option('--output-dir', help='Output directory for the generated app (defaults to central webapps directory)')
def fresh_app(template: str, url: Optional[str], icon: Optional[str], output_dir: Optional[str]):
    """Generate a fresh web application with datetime name and force reinstall it"""
    
    # Generate timestamp-based name
    name = generate_default_name()
    click.echo(f"🎯 Generating fresh application with name: {name}")
    
    # Use central webapps directory if no output directory specified
    if output_dir is None:
        webapps_dir = ensure_webapps_dir()
        output_path = webapps_dir / name
    else:
        output_path = Path(output_dir) / name
    
    # Check if app already exists
    if output_path.exists():
        click.echo(f"⚠️  App directory already exists: {output_path}")
        if not click.confirm("Delete existing app and create fresh?"):
            click.echo("Cancelled.")
            return
        click.echo("🗑️  Removing existing app directory...")
        shutil.rmtree(output_path)
    
    click.echo(f"📦 Generating web application '{name}' using {template} template")
    click.echo(f"📁 Output directory: {output_path}")
    
    try:
        # Generate the app
        if template == 'webmail':
            if not url:
                click.echo("Error: URL is required for webmail template", err=True)
                return
            generate_webmail_app(url, name, name, output_path, icon)
        elif template == 'vector-store':
            generate_vector_store_app(name, name, output_path, icon)
        elif template == 'my-vector-store':
            generate_my_vector_store_app(name, name, output_path, icon)
        
        click.echo(f"✅ Successfully generated '{name}' application")
        
        # Now force reinstall it
        click.echo("🔄 Starting force reinstall...")
        
        # Delete node_modules if it exists
        nm = output_path / "node_modules"
        if nm.exists():
            click.echo("🗑️  Deleting node_modules...")
            shutil.rmtree(nm)
        
        # Delete package-lock.json if it exists
        plock = output_path / "package-lock.json"
        if plock.exists():
            click.echo("🗑️  Deleting package-lock.json...")
            plock.unlink()
        
        # Delete .venv if it exists
        venv = output_path / "python" / ".venv"
        if venv.exists():
            click.echo("🗑️  Deleting python/.venv...")
            shutil.rmtree(venv)
        
        # Delete build/ and dist/ if they exist
        for d in ["build", "dist"]:
            dpath = output_path / d
            if dpath.exists():
                click.echo(f"🗑️  Deleting {d}/ directory...")
                shutil.rmtree(dpath)
        
        # Delete Electron cache/userData if it exists
        import getpass
        user_data_dir = Path.home() / "Library" / "Application Support" / f"{name} Vector Store"
        if user_data_dir.exists():
            click.echo(f"🗑️  Deleting Electron userData: {user_data_dir}")
            shutil.rmtree(user_data_dir)
        
        # Reinstall
        install_sh = output_path / "install.sh"
        if install_sh.exists():
            click.echo("🔧 Running install.sh...")
            result = subprocess.run(["bash", str(install_sh)], cwd=output_path, capture_output=True, text=True)
            if result.returncode == 0:
                click.echo("✅ install.sh completed successfully")
            else:
                click.echo(f"⚠️  install.sh had issues: {result.stderr}")
        else:
            click.echo("🔧 Running npm install --ignore-scripts...")
            result = subprocess.run(["npm", "install", "--ignore-scripts"], cwd=output_path, capture_output=True, text=True)
            if result.returncode == 0:
                click.echo("✅ npm install completed successfully")
            else:
                click.echo(f"⚠️  npm install had issues: {result.stderr}")
            
            click.echo("🔧 Auto-fixing Electron installation...")
            if auto_fix_electron_installation(output_path):
                click.echo("✅ Electron auto-fix completed")
            else:
                click.echo("⚠️  Electron auto-fix had issues")
        
        click.echo(f"🎉 Fresh app '{name}' is ready!")
        click.echo(f"🚀 Run it with: mcli workflow webapp run {name}")
        click.echo(f"📁 App location: {output_path}")
        
    except Exception as e:
        click.echo(f"❌ Error creating fresh app: {e}", err=True)
        return


if __name__ == '__main__':
    webapp() 