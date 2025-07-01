# Web Application Generator

A powerful command-line tool for generating and installing Electron-based web application wrappers based on the [lgmail template](https://github.com/gwicho38/lgmail).

## Overview

The `webapp` command allows you to quickly generate desktop applications that wrap any web application with Electron, providing a native desktop experience with performance optimizations.

## Features

- 🚀 **Template-based Generation**: Uses the high-performance lgmail template as a base
- 🎨 **Customizable Branding**: Specify app name, URL, and custom icons
- ⚡ **Performance Optimized**: Includes hardware acceleration and performance optimizations
- 🔒 **Security Focused**: Sandboxed environment with proper security settings
- 📦 **Easy Installation**: Automatic packaging and installation scripts
- 🛠️ **Development Ready**: Includes all necessary build tools and scripts

## Prerequisites

- Node.js 18.0.0 or higher
- npm 8.0.0 or higher
- The lgmail template repository at `~/repos/lgmail`

## Storage Location

All generated web applications are stored in `$HOME/.local/mcli/webapps/` by default. This provides a centralized location for managing all your web applications.

## Commands

### Generate

Generate a new web application from the template.

```bash
mcli workflow webapp generate --url <URL> --name <NAME> [options]
```

**Options:**
- `--url`: URL of the web application to wrap (required)
- `--name`: Name of the application (required)
- `--icon`: Path to the icon file (.icns for macOS)
- `--output-dir`: Output directory for the generated app (default: `./generated-apps`)
- `--install`: Install the app after generation

**Example:**
```bash
# Generate a GitHub desktop app (stored in ~/.local/mcli/webapps/)
mcli workflow webapp generate --url https://github.com --name "GitHub Desktop" --install

# Generate a custom app with icon in custom location
mcli workflow webapp generate --url https://app.example.com --name "My App" --icon ./my-icon.icns --output-dir ./my-apps
```

### Install

Install a previously generated web application.

```bash
mcli workflow webapp install <app-dir>
```

**Example:**
```bash
mcli workflow webapp install ~/.local/mcli/webapps/my_app
```

### Run

Run a generated web application in development mode.

```bash
mcli workflow webapp run <app-dir>
```

**Example:**
```bash
mcli workflow webapp run ~/.local/mcli/webapps/my_app
```

### List

List all generated web applications.

```bash
mcli workflow webapp list [--verbose]
```

**Options:**
- `--verbose, -v`: Show detailed information including creation dates and file paths

**Example:**
```bash
# List all apps
mcli workflow webapp list

# List with detailed information
mcli workflow webapp list --verbose
```

### Delete

Delete a generated web application.

```bash
mcli workflow webapp delete <app-name> [--force]
```

**Options:**
- `--force, -f`: Force deletion without confirmation

**Example:**
```bash
# Delete with confirmation
mcli workflow webapp delete my_app

# Force delete without confirmation
mcli workflow webapp delete my_app --force
```

## Generated Application Structure

When you generate a web application, the following structure is created in `~/.local/mcli/webapps/app-name/`:

```
app-name/
├── main.js                 # Main Electron process
├── preload.js              # Preload script for security
├── renderer.js             # Renderer process script
├── index.html              # Main HTML file with loading screen
├── styles.css              # Application styles
├── package.json            # Project configuration (customized)
├── webpack.main.config.js  # Webpack config for main process
├── webpack.renderer.config.js # Webpack config for renderer
├── electron.config.js      # Electron configuration
├── README.md               # Customized documentation
├── install.sh              # Installation script
├── .gitignore              # Git ignore file
├── .nvmrc                  # Node.js version
└── .env                    # Environment variables
```

## Customization

The generator automatically customizes the following files:

### package.json
- Updates app name and description
- Modifies build scripts for the new app
- Updates repository URL and keywords
- Maintains all dependencies and dev tools

### main.js
- Replaces Gmail-specific URLs with your target URL
- Updates app titles and branding
- Modifies session persistence settings
- Maintains all performance optimizations

### index.html
- Updates page title and meta descriptions
- Customizes loading screen text
- Updates icon references
- Maintains all performance optimizations

### README.md
- Creates comprehensive documentation
- Includes installation and usage instructions
- Customizes feature descriptions
- Provides development guidelines

## Installation Process

The generated `install.sh` script performs the following steps:

1. **Dependency Check**: Verifies Node.js and npm are installed
2. **Install Dependencies**: Runs `npm install`
3. **Build Application**: Runs `npm run build`
4. **Package Application**: Creates distributable package
5. **Install to Applications**: Links the app to `/Applications`

## Development Workflow

1. **Generate**: Create a new app with `mcli workflow webapp generate`
2. **List**: View all apps with `mcli workflow webapp list`
3. **Customize**: Modify the generated files as needed
4. **Test**: Run in development mode with `mcli workflow webapp run`
5. **Build**: Install with `mcli workflow webapp install`
6. **Manage**: Delete apps with `mcli workflow webapp delete`

## Performance Features

The generated applications include:

- **Hardware Acceleration**: GPU-accelerated rendering
- **Session Persistence**: Maintains login sessions
- **Background Processing**: Optimized background tasks
- **Memory Management**: Efficient memory usage
- **Security**: Sandboxed environment with proper permissions

## Troubleshooting

### Template Not Found
If you get an error about the lgmail template not being found:
```bash
# Clone the template repository
git clone https://github.com/gwicho38/lgmail ~/repos/lgmail
```

### Installation Issues
If installation fails:
1. Check Node.js version: `node --version`
2. Check npm version: `npm --version`
3. Ensure you have write permissions to `/Applications`
4. Check the generated `install.sh` script for errors

### Build Issues
If the app doesn't build:
1. Check all dependencies are installed: `npm install`
2. Verify webpack configuration
3. Check for any syntax errors in generated files

## Examples

### Create a Slack Desktop App
```bash
mcli workflow webapp generate --url https://app.slack.com --name "Slack Desktop" --install
```

### Create a Notion Desktop App
```bash
mcli workflow webapp generate --url https://notion.so --name "Notion" --icon ./notion-icon.icns
```

### Create a Custom Web App
```bash
mcli workflow webapp generate --url https://myapp.example.com --name "My Custom App" --output-dir ./custom-apps
```

### List All Applications
```bash
mcli workflow webapp list --verbose
```

### Delete an Application
```bash
mcli workflow webapp delete my_app
```

## Contributing

To contribute to the webapp generator:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with various URLs and configurations
5. Submit a pull request

## License

This tool is part of the mcli project and follows the same license terms. 