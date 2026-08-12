# Azure Deployment Quick Start

## 5-Minute Setup

### Prerequisites
- Azure Subscription (free tier OK)
- Azure CLI installed ([download](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli))
- Python 3.11+
- Azure Functions Core Tools ([download](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local))

### Step 1: Prepare Credentials (5 min)

Get your Azure AD app credentials:

1. Go to **Azure Portal** → **Azure Active Directory** → **App Registrations**
2. Create new app or use existing
3. Get: **Tenant ID, Client ID**
4. Create **Client Secret** (copy immediately, can't retrieve later)
5. Add **API Permissions**:
   - Mail.Read
   - Mail.Read.Shared  
   - Files.Read.All
   - Sites.Read.All
6. Grant admin consent

### Step 2: Deploy Azure Resources (2 min)

```powershell
# Run deployment script
.\azure-deploy.ps1
```

Or manually:

```bash
# Login
az login

# Set variables
$RG = "lss-automation-rg"
$LOCATION = "eastus"
$FUNC = "lss-automation-func"
$STORAGE = "lssautostg$(Get-Random -Minimum 1000 -Maximum 9999)"

# Create resources
az group create --name $RG --location $LOCATION

az storage account create `
  --resource-group $RG `
  --name $STORAGE `
  --sku Standard_LRS

az functionapp create `
  --resource-group $RG `
  --consumption-plan-location $LOCATION `
  --runtime python `
  --runtime-version 3.11 `
  --functions-version 4 `
  --name $FUNC `
  --storage-account $STORAGE
```

### Step 3: Configure & Deploy (3 min)

```bash
# Copy template and edit
Copy-Item local.settings.json.template local.settings.json

# Edit local.settings.json with your credentials
# Then deploy
func azure functionapp publish $FUNC --build remote
```

### Step 4: Set Environment Variables in Azure Portal

1. Go to **Function App** → **Configuration** → **Application settings**
2. Add these variables:
   - `AZURE_TENANT_ID` = your-tenant-id
   - `AZURE_CLIENT_ID` = your-client-id
   - `AZURE_CLIENT_SECRET` = your-client-secret
   - `USER_EMAIL` = your-email@example.com
   - `OUTPUT_EMAIL` = output@example.com
   - `MASTER_TRACKER_ONEDRIVE_PATH` = General - Appeals/LSS/OUTPUT/Master Tracker.xlsx

3. Click **Save**

### Step 5: Test

```bash
# Test locally
func start

# Visit in browser
http://localhost:7071/api/health

# Trigger manually
curl -X POST http://localhost:7071/api/run-lss-automation
```

### Step 6: Monitor

In Azure Portal:
- **Function App** → **Monitor** - see execution history
- **Function App** → **Logs** - view output

---

## Deployment Checklist

- [ ] Azure Subscription created
- [ ] Azure CLI installed
- [ ] Azure AD app registered
- [ ] API permissions granted (Mail.Read, Files.Read.All, etc.)
- [ ] Credentials copied (Tenant ID, Client ID, Client Secret)
- [ ] Azure resources deployed
- [ ] Environment variables configured
- [ ] Code deployed to Function App
- [ ] Local test passed (func start)
- [ ] Health check verified
- [ ] Manual trigger tested
- [ ] Timer schedule verified (9 AM EST weekdays)
- [ ] Monitor dashboard checked

---

## Troubleshooting

### "AzureWebJobsStorage connection string error"
- Update `local.settings.json` with correct storage connection string
- Regenerate storage account key if needed

### "AZURE_TENANT_ID not found"
- Check that environment variables are set in Function App Configuration
- Wait 30 seconds after saving for changes to propagate

### "Authentication failed with Graph API"
- Verify Client Secret is correct and not expired
- Check that API permissions are granted
- Verify admin consent was given

### Function not triggering on schedule
- Check timer trigger settings in Azure Portal
- Verify cron expression: `0 14 * * 1-5`
- Check that function app is running (not stopped)

### "Permission denied" for OneDrive files
- Ensure file path exists in OneDrive
- Check Graph API has Files.Read.All permission
- Verify user account has access to shared OneDrive

---

## Architecture

```
GitHub Repository
    ↓
    ├── Code pushed to GitHub
    ├── Webhook to Azure Function
    ↓
Azure Function App (Timer Trigger)
    ├── Runs on schedule (9 AM EST weekdays)
    ├── Or manually via HTTP endpoint
    ↓
Microsoft Graph API
    ├── Connect to Outlook (Mail.Read)
    ├── Download attachments
    ├── Read from OneDrive (Files.Read.All)
    ↓
LSS Automation Logic
    ├── Parse PDF invoices
    ├── Extract line items
    ├── Generate Excel reports
    ↓
OneDrive/SharePoint
    ├── Upload output Excel file
    ├── Update Master Tracker
```

---

## Next Steps

1. **Monitoring Setup**
   - Enable Application Insights for detailed logs
   - Set up email alerts for failures

2. **Security Hardening**
   - Use Azure Key Vault for secrets
   - Enable managed identity
   - Restrict network access

3. **Advanced Features**
   - Add Logic Apps for notifications
   - Set up automated backups
   - Configure retry policies

---

## Useful Commands

```bash
# View function logs
func azure functionapp logstream $FUNC

# Get function status
az functionapp show --name $FUNC --resource-group $RG

# Restart function app
az functionapp restart --name $FUNC --resource-group $RG

# View application settings
az functionapp config appsettings list --name $FUNC --resource-group $RG

# Delete all resources (cleanup)
az group delete --name $RG --yes
```

---

## Cost Breakdown (Monthly Estimate)

| Service | Cost |
|---------|------|
| Azure Functions (500K executions) | $0.20 |
| Storage Account (5 GB) | $0.10 |
| Data Transfer (1 GB) | $0.01 |
| **Total** | **~$0.31** |

---

## Support

- [Azure Functions Documentation](https://learn.microsoft.com/en-us/azure/azure-functions/)
- [Microsoft Graph API Guide](https://learn.microsoft.com/en-us/graph/overview)
- [Python Azure Functions Guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-develop-python)

For issues specific to this app, check `lss_automation.log` in the Azure Portal Logs section.
