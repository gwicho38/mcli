import click
import os
import shutil
import subprocess
import json
from pathlib import Path
from typing import Optional, List
import re


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


@webapp.command()
@click.option('--url', help='URL of the web application to wrap (for lgmail template)')
@click.option('--name', required=True, help='Name of the application')
@click.option('--icon', help='Path to the icon file (.icns for macOS)')
@click.option('--output-dir', help='Output directory for the generated app (defaults to central webapps directory)')
@click.option('--install', is_flag=True, help='Install the app after generation')
@click.option('--template', type=click.Choice(['lgmail', 'vector-store']), default='lgmail', help='Template to use for generation')
def generate(url: str, name: str, icon: Optional[str], output_dir: Optional[str], install: bool, template: str):
    """Generate a template web application based on available templates"""
    
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
        if template == 'lgmail':
            generate_lgmail_app(url, name, safe_name, output_path, icon)
        elif template == 'vector-store':
            generate_vector_store_app(name, safe_name, output_path, icon)
        
        if install:
            click.echo("Installing the generated application...")
            install_app(str(output_path))
        
        click.echo(f"✓ Successfully generated '{name}' application")
        
    except Exception as e:
        click.echo(f"Error generating application: {e}", err=True)
        return


def generate_lgmail_app(url: str, name: str, safe_name: str, output_path: Path, icon: Optional[str]):
    """Generate application using lgmail template"""
    # Validate URL
    if not url or not url.startswith(('http://', 'https://')):
        click.echo("Error: URL must start with http:// or https://", err=True)
        return
    
    # Copy template files from lgmail
    template_dir = Path.home() / "repos" / "lgmail"
    if not template_dir.exists():
        click.echo("Error: lgmail template not found at ~/repos/lgmail", err=True)
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
    # Copy template files from vector-store-app template
    template_dir = Path(__file__).parent / "templates" / "vector-store-app"
    if not template_dir.exists():
        click.echo("Error: vector-store-app template not found", err=True)
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
            result = subprocess.run(
                ["npm", "install"],
                cwd=app_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                click.echo("✓ Dependencies installed successfully")
            else:
                click.echo(f"Installation failed: {result.stderr}", err=True)
                
        except Exception as e:
            click.echo(f"Error installing dependencies: {e}", err=True)


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
@click.argument('app-dir', type=click.Path(exists=True))
def run(app_dir: str):
    """Run a generated web application in development mode"""
    
    app_path = Path(app_dir)
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
            subprocess.run(['npm', 'install'], check=True)
        
        # Run the application
        click.echo("Starting application...")
        subprocess.run(['npm', 'run', 'dev'], check=True)
        
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
    
    # Sort by name
    apps.sort(key=lambda x: x['name'])
    
    click.echo(f"Found {len(apps)} web application(s):")
    click.echo()
    
    for app in apps:
        click.echo(f"📱 {app['name']}")
        click.echo(f"   Description: {app['description']}")
        click.echo(f"   URL: {app['url']}")
        click.echo(f"   Version: {app['version']}")
        
        if verbose:
            from datetime import datetime
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


if __name__ == '__main__':
    webapp() 