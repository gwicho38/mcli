# Publishing MCLI Workflow Notebooks to VSCode Marketplace

## Prerequisites

To publish this extension to the VSCode Marketplace, you need:

1. **Microsoft Account** - Any Microsoft account (Outlook, Hotmail, etc.)
2. **Azure DevOps Organization** - Free account at https://dev.azure.com
3. **Personal Access Token (PAT)** - Generated from Azure DevOps
4. **Publisher Account** - Created at https://marketplace.visualstudio.com/manage

## Step-by-Step Publishing Process

### 1. Create Azure DevOps Account (if you don't have one)

1. Go to https://dev.azure.com
2. Sign in with your Microsoft account
3. Create a new organization (e.g., "lefv" or "mcli-framework")

### 2. Create Personal Access Token (PAT)

1. In Azure DevOps, click on your profile icon (top right)
2. Select "Personal access tokens"
3. Click "+ New Token"
4. Configure:
   - **Name**: `vscode-marketplace` (or any descriptive name)
   - **Organization**: All accessible organizations
   - **Expiration**: Custom defined (e.g., 90 days, 1 year)
   - **Scopes**:
     - Select "Custom defined"
     - Under "Marketplace", check "Acquire" and "Manage"
5. Click "Create"
6. **IMPORTANT**: Copy the token immediately - you won't be able to see it again!

### 3. Create Publisher Account

1. Go to https://marketplace.visualstudio.com/manage
2. Sign in with the same Microsoft account
3. Click "Create publisher"
4. Fill in:
   - **Publisher ID**: `lefv` (must match package.json)
   - **Display Name**: Your name or organization
   - **Description**: Optional
5. Click "Create"

### 4. Login to VSCE (Command Line)

```bash
cd /Users/lefv/repos/mcli/vscode-extension
vsce login gwicho38
```

When prompted, paste your Personal Access Token.

### 5. Publish the Extension

```bash
# First time publish
vsce publish

# Or specify version
vsce publish 1.0.0

# Or publish a pre-packaged VSIX
vsce publish -p <your-PAT> mcli-workflow-notebooks-1.0.0.vsix
```

### 6. Verify Publication

1. Go to https://marketplace.visualstudio.com/manage/publishers/gwicho38
2. You should see "MCLI Framework" listed
3. Click on it to view the listing
4. The extension will be available at: https://marketplace.visualstudio.com/items?itemName=gwicho38.mcli-framework

## Environment Variables (Optional)

You can store your PAT in an environment variable to avoid typing it:

```bash
# Add to ~/.zshrc or ~/.bashrc
export VSCE_PAT="your-personal-access-token-here"

# Then publish without login prompt
vsce publish
```

## Updating the Extension

When you make changes and want to publish an update:

1. Update version in `package.json` (e.g., `1.0.0` → `1.0.1`)
2. Update `CHANGELOG.md` with changes
3. Run tests and rebuild:
   ```bash
   npm run package
   vsce package
   ```
4. Publish:
   ```bash
   vsce publish
   ```

## Versioning Convention

Follow semantic versioning (MAJOR.MINOR.PATCH):

- **PATCH** (1.0.0 → 1.0.1): Bug fixes, small improvements
- **MINOR** (1.0.0 → 1.1.0): New features, backward compatible
- **MAJOR** (1.0.0 → 2.0.0): Breaking changes

Or use vsce's built-in version bumping:

```bash
vsce publish patch  # 1.0.0 → 1.0.1
vsce publish minor  # 1.0.0 → 1.1.0
vsce publish major  # 1.0.0 → 2.0.0
```

## Troubleshooting

### "Publisher 'gwicho38' not found"

You need to create the publisher account first (see Step 3).

### "Invalid Personal Access Token"

- Make sure the token has "Marketplace: Acquire, Manage" scopes
- Check that the token hasn't expired
- Try creating a new token

### "Extension validation failed"

- Check `package.json` for required fields
- Ensure icon exists and is valid PNG/SVG
- Verify README.md is present
- Run `vsce package` to see validation errors

### "Extension already published with this version"

Bump the version in `package.json` before publishing again.

## Security Notes

- **NEVER commit your PAT to git**
- Store PAT in environment variable or password manager
- Use short expiration periods (90 days recommended)
- Regenerate PAT if compromised

## Resources

- [VSCode Publishing Extensions Guide](https://code.visualstudio.com/api/working-with-extensions/publishing-extension)
- [Azure DevOps PAT Documentation](https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate)
- [Marketplace Publisher Portal](https://marketplace.visualstudio.com/manage)
- [VSCE CLI Documentation](https://github.com/microsoft/vscode-vsce)

## Current Status

- ✅ Extension packaged: `mcli-framework-1.0.0.vsix`
- ✅ Icon created: `icon.png` (128x128)
- ✅ README, CHANGELOG, LICENSE included
- ⏳ Publisher account setup required
- ⏳ PAT creation required
- ⏳ Publishing to marketplace pending

## Manual Publishing Alternative

If automated publishing doesn't work, you can manually upload the VSIX:

1. Go to https://marketplace.visualstudio.com/manage/publishers/gwicho38
2. Click "..." menu → "Upload Extension"
3. Select `mcli-framework-1.0.0.vsix`
4. Fill in any additional metadata
5. Click "Upload"
