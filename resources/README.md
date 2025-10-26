# MCLI Framework Resources

This directory contains branding assets and resources for the MCLI Framework project.

## 🎨 Logo Files

### MCLI Framework Logo

**Vector Format (Recommended)**
- `mcli-logo.svg` - Scalable vector graphic (4.7 KB)
  - Use for: Web, print, any size scaling
  - Format: SVG with gradients and filters
  - Colors: Purple (#667eea) to Pink (#f093fb) gradient

**Raster Formats**
- `mcli-logo-512.png` - 512x512 (62 KB) - High resolution, documentation
- `mcli-logo-256.png` - 256x256 (42 KB) - Medium resolution, web
- `mcli-logo-128.png` - 128x128 (18 KB) - VSCode extension icon ⭐
- `mcli-logo-64.png` - 64x64 (9 KB) - Small icons, favicons
- `mcli-logo-32.png` - 32x32 (4.6 KB) - Tiny icons, UI elements

## 📐 Logo Design

The MCLI Framework logo features:

### Visual Elements
- **Notebook Pages**: Stacked pages representing Jupyter-like notebooks
- **Code Cells**: Horizontal bars with orange execution indicators
- **Play Button**: Orange circle with play icon (execution/run)
- **Terminal Badge**: CLI indicator with `$_` prompt
- **MCLI Badge**: Purple rounded rectangle with white text
- **Workflow Arrows**: Directional flow indicators

### Color Palette
```
Primary Gradient:
  - Start: #667eea (Purple)
  - Mid: #764ba2 (Deep Purple)
  - End: #f093fb (Pink)

Accent Colors:
  - Orange: #f97316 (Play button, execution indicators)
  - Terminal: #1e293b (Dark slate)
  - Success: #10b981 (Green terminal text)
```

### Design Principles
- **Modern**: Gradient backgrounds, soft shadows, glowing effects
- **Technical**: Monospace font, terminal elements, code representation
- **Interactive**: Play button suggests execution capability
- **Professional**: Clean lines, balanced composition, appropriate spacing

## 📝 Usage Guidelines

### VSCode Extension
- Use `mcli-logo-128.png` as the extension icon
- Referenced in `package.json` as `icon.png`
- Automatically included in VSIX package

### Documentation
- Use `mcli-logo-512.png` for high-quality documentation headers
- Use `mcli-logo-256.png` for README badges and medium-size displays
- Use SVG format for web pages that support it

### GitHub
- Use `mcli-logo-256.png` for repository social preview
- Use `mcli-logo-64.png` for small GitHub badges
- Use SVG in README for crisp display at any size

### Print Materials
- Always use `mcli-logo.svg` for print to ensure quality at any size
- Export to appropriate DPI (300+ for print) as needed

## 🔧 Regenerating Logos

If you need to regenerate the PNG files from the SVG source:

```bash
cd /Users/lefv/repos/mcli/resources

# Generate all sizes
magick mcli-logo.svg -resize 512x512 mcli-logo-512.png
magick mcli-logo.svg -resize 256x256 mcli-logo-256.png
magick mcli-logo.svg -resize 128x128 mcli-logo-128.png
magick mcli-logo.svg -resize 64x64 mcli-logo-64.png
magick mcli-logo.svg -resize 32x32 mcli-logo-32.png

# Update extension icon
cp mcli-logo-128.png ../vscode-extension/icon.png
cp mcli-logo.svg ../vscode-extension/icon.svg
```

## 🎯 Logo Variants

The current logo is the primary brand mark. Future variants may include:

- **Dark Mode**: Inverted colors for dark backgrounds
- **Monochrome**: Single-color version for print or simple contexts
- **Icon Only**: Just the notebook/play button without text
- **Horizontal**: Wide format with text beside logo
- **Favicon**: Simplified 16x16 version for browser tabs

## 📦 File Sizes

| File | Size | Use Case |
|------|------|----------|
| mcli-logo.svg | 4.7 KB | Source, web, print, any size |
| mcli-logo-512.png | 62 KB | High-res documentation |
| mcli-logo-256.png | 42 KB | Medium displays, social media |
| mcli-logo-128.png | 18 KB | VSCode extension icon ⭐ |
| mcli-logo-64.png | 9 KB | Small icons, GitHub badges |
| mcli-logo-32.png | 4.6 KB | Tiny UI elements |

## 🖼️ Logo Features

### Technical Implementation
- **Format**: SVG 1.1 compatible
- **Viewbox**: 512x512
- **Gradients**: Linear gradients with multiple stops
- **Filters**: Shadow and glow effects for depth
- **Layers**: Organized groups for easy editing

### Editing the Logo

To modify the logo, edit `mcli-logo.svg` with:
- **Vector Editors**: Inkscape (free), Adobe Illustrator, Figma
- **Code Editors**: Any text editor (it's XML-based SVG)

Key editable elements:
- Line 5-9: Main background gradient colors
- Line 12-16: Notebook page gradient
- Line 88-103: Code cell positions and colors
- Line 106-114: Play button position and color
- Line 123-126: MCLI text badge

## 🎨 Brand Consistency

When using the logo:
- ✅ DO maintain aspect ratio (always square)
- ✅ DO use provided color variants
- ✅ DO ensure adequate padding around logo
- ✅ DO use high-resolution versions for large displays

- ❌ DON'T stretch or distort the logo
- ❌ DON'T change the color scheme arbitrarily
- ❌ DON'T add effects that obscure the design
- ❌ DON'T use low-resolution versions for large displays

## 📄 License

These logo files are part of the MCLI Framework project and are licensed under the same MIT license as the project.

## 🔗 Related Files

- Extension icon: `../vscode-extension/icon.png` (symlinked to `mcli-logo-128.png`)
- Extension icon source: `../vscode-extension/icon.svg` (symlinked to `mcli-logo.svg`)
- Package manifest: `../vscode-extension/package.json`

---

**Created**: 2025-10-26
**Format**: SVG with PNG exports
**Designer**: MCLI Framework Team
**Version**: 1.0.0
