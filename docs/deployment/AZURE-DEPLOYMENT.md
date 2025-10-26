# MCLI Framework - Azure Deployment

**Deployment Status**: ✅ In Progress
**Date**: 2025-10-26

## Deployment Details

### Azure Resources

**Deployment Information**:
- **Deployment Name**: `deploy-mcli-1761475339830`
- **Subscription**: Azure subscription 1
- **Resource Group**: `mcli-framework`
- **Start Time**: 10/26/2025, 11:42:23 AM
- **Correlation ID**: `fd93ec56-4499-4365-a2d9-1622aadd64b3`
- **Icon**: Offering icon deployed

### Resource Group

**Name**: `mcli-framework`
**Purpose**: Houses all MCLI Framework Azure resources
**Location**: (To be confirmed)

## Azure DevOps Integration

With this Azure deployment, we now have:

1. **Azure Subscription**: Active and provisioned
2. **Resource Group**: `mcli-framework` - matches extension name
3. **Deployment**: In progress

### VSCode Marketplace Publishing

This Azure setup provides the foundation for VSCode Marketplace publishing:

**Benefits**:
- ✅ Azure subscription active
- ✅ Resource group created with matching name
- ✅ Azure account authenticated
- ✅ Ready for Azure DevOps organization setup

### Next Steps for Marketplace Publishing

Now that Azure is set up:

1. **Create Azure DevOps Organization** (if not already done)
   - Name: `gwicho38` (to match publisher ID)
   - Link to this Azure subscription

2. **Create Azure DevOps Project**
   - Name: `mcli-framework` (matches resource group)
   - Link to git repository

3. **Generate Personal Access Token**
   - From Azure DevOps
   - Scopes: Marketplace (Acquire, Manage)

4. **Publish Extension**
   ```bash
   cd vscode-extension
   vsce login gwicho38
   vsce publish
   ```

## Azure Resources Deployed

The `mcli-framework` resource group may contain:

- App Services
- Storage Accounts
- Databases
- Container Registries
- Key Vaults (for secrets management via lsh-framework)
- Other Azure resources

## Monitoring

**Azure Portal**: https://portal.azure.com
**Resource Group**: https://portal.azure.com/#@/resource/subscriptions/{subscription-id}/resourceGroups/mcli-framework

**Deployment ID**: `fd93ec56-4499-4365-a2d9-1622aadd64b3`

## Integration with lsh-framework

For secrets management in Azure deployment, use the lsh-framework:

```bash
# Store Azure secrets
lsh set AZURE_SUBSCRIPTION_ID "your-subscription-id"
lsh set AZURE_RESOURCE_GROUP "mcli-framework"
lsh set AZURE_DEPLOYMENT_ID "fd93ec56-4499-4365-a2d9-1622aadd64b3"

# Retrieve for automation
lsh get AZURE_SUBSCRIPTION_ID
```

## Deployment Timeline

- **10/26/2025 11:42:23 AM**: Deployment started
- **Status**: In progress
- **Next Update**: TBD

## Related Documentation

- **VSCode Extension Publishing**: `vscode-extension/PUBLISHING.md`
- **GitHub Issue**: [#86 - Publish Extension](https://github.com/gwicho38/mcli/issues/86)
- **Marketplace Ready**: `vscode-extension/MARKETPLACE-READY.md`

## Notes

- Azure subscription is active and provisioned
- Resource group name matches extension name (good for consistency)
- This deployment completes the Azure infrastructure prerequisite for marketplace publishing
- Ready to proceed with Azure DevOps setup for VSCode Marketplace

---

**Deployment Status**: ✅ Active
**Last Updated**: 2025-10-26 11:42:23 AM
**Correlation ID**: fd93ec56-4499-4365-a2d9-1622aadd64b3
