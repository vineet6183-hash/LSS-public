# Azure App Service Setup - LSS Invoice Automation

## ✅ What's Been Set Up

- **Flask Web Application** (`app.py`) - Provides HTTP endpoints
- **Startup Script** (`startup.sh`) - Initializes the app on Azure
- **Updated Requirements** - Added Flask, Gunicorn, Azure SDKs
- **GitHub Actions** - Auto-deployment on push to main

## 🚀 Next Steps to Deploy

### Step 1: Push Changes to GitHub

```bash
cd E:\GitHub\LSS
git add app.py startup.sh requirements.txt .deployment
git commit -m "Add Flask WSGI app and Azure startup configuration"
git push origin main
```

This triggers auto-deployment via GitHub Actions.

### Step 2: Configure Azure Portal Settings

1. **Login to Azure Portal**
   - Go to: [portal.azure.com](https://portal.azure.com)
   - Resource Group: `Portal-Extraction`
   - App: `LSS-public`

2. **Set Startup Command**
   - Path: **Configuration** → **General settings**
   - Startup Command:
     ```
     /bin/bash startup.sh
     ```
   - Click **Save**

3. **Add Environment Variables**
   - Path: **Configuration** → **Application settings**
   - Click **+ New application setting** for each:

   | Name | Value |
   |------|-------|
   | `AZURE_TENANT_ID` | Your tenant ID from Azure AD |
   | `AZURE_CLIENT_ID` | Your client ID from app registration |
   | `AZURE_CLIENT_SECRET` | Your client secret (keep secure!) |
   | `USER_EMAIL` | your-email@example.com |
   | `OUTPUT_EMAIL` | output@example.com |
   | `MASTER_TRACKER_ONEDRIVE_PATH` | General - Appeals/LSS/OUTPUT/Master Tracker.xlsx |
   | `PYTHONPATH` | /home/site/wwwroot |

   - Click **Save**
   - Wait for app to restart (2-3 minutes)

### Step 3: Test the Deployment

**Test 1: Health Check**
```bash
curl https://lss-public.azurewebsites.net/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-08-13T10:30:00.000000",
  "app": "LSS Invoice Automation",
  "environment": "App Service"
}
```

**Test 2: Configuration Status**
```bash
curl https://lss-public.azurewebsites.net/api/status
```

Should show all environment variables as `✓`

**Test 3: Manual Trigger**
```bash
curl -X POST https://lss-public.azurewebsites.net/api/run-lss-automation
```

Should return:
```json
{
  "status": "success",
  "message": "LSS automation completed successfully",
  "timestamp": "2026-08-13T10:30:00.000000"
}
```

### Step 4: View Deployment Logs

**Option A: Real-time logs**
```bash
az webapp log tail --name lss-public --resource-group Portal-Extraction
```

**Option B: In Azure Portal**
- Go to **Deployment Center** → **Logs**
- Or **Log Stream** to see live output

---

## 📋 Free Tier Limitations & Solutions

### Problem: No Always-On

The Free Tier (F1) puts the app to sleep after 20 minutes of inactivity.

**Solution 1: Upgrade to Basic B1 (~$10/month)**
```bash
az appservice plan create \
  --name plan-LSS-basic \
  --resource-group Portal-Extraction \
  --sku B1 \
  --is-linux
```

**Solution 2: Keep with Free + Setup Scheduler**
Use Azure Logic Apps or GitHub Actions to ping the app regularly.

### Problem: No Scheduled Tasks

The Free Tier doesn't support built-in scheduling.

**Solution: GitHub Actions Scheduler** (Recommended - FREE)

Create `.github/workflows/lss-scheduler.yml`:
```yaml
name: LSS Automation Scheduler
on:
  schedule:
    - cron: '0 14 * * 1-5'  # 9 AM EST, weekdays
  workflow_dispatch:

jobs:
  trigger:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger App Service
        run: |
          curl -X POST \
            -H "Content-Type: application/json" \
            https://lss-public.azurewebsites.net/api/run-lss-automation
```

---

## 🔧 Troubleshooting

### Issue: "Issues Detected" Still Showing

**Solution**: 
1. Check **Log Stream** for error messages
2. Restart the app: **Restart** button at top
3. Check startup command is set correctly

### Issue: 502 Bad Gateway

**Causes**:
- App crashed
- Missing dependencies
- Startup timeout

**Fix**:
```bash
# Check logs
az webapp log tail --name lss-public --resource-group Portal-Extraction

# Restart
az webapp restart --name lss-public --resource-group Portal-Extraction

# Check deployment
az webapp deployment list --name lss-public --resource-group Portal-Extraction
```

### Issue: Environment Variables Not Working

1. Go to **Configuration** in Portal
2. Verify all variables are present
3. Click **Save** (crucial - don't skip!)
4. Wait 2-3 minutes for app restart
5. Check in browser: `https://lss-public.azurewebsites.net/api/status`

### Issue: Graph API Authentication Error

**Check**:
- ✓ Tenant ID is correct
- ✓ Client ID is correct
- ✓ Client Secret hasn't expired
- ✓ API permissions are granted (Mail.Read, Files.Read.All)
- ✓ Admin consent was given

**Fix**:
1. Go to Azure AD → App Registrations
2. Find your app registration
3. Check **API permissions** tab
4. Ensure all permissions show "✓ Granted for..."
5. If not, click "Grant admin consent"

---

## 📊 Monitoring & Logging

### View Logs in Portal
1. Go to LSS-public App Service
2. Click **Log Stream** (left sidebar)
3. See real-time output

### Use Azure CLI
```bash
# Stream logs (Ctrl+C to stop)
az webapp log tail --name lss-public --resource-group Portal-Extraction

# Get recent logs
az webapp log show --name lss-public --resource-group Portal-Extraction
```

### Check Deployment History
1. **Deployment Center** → **Logs**
2. See GitHub Actions build status
3. Click on builds to see details

---

## 🎯 Performance Tips

### Current Setup (Free Tier)
- Single worker process
- 60-second timeout per request
- 1 GB memory limit
- ✓ Good for scheduled tasks
- ✗ Not great for concurrent requests

### Upgrade Recommendations

**For Better Performance: Basic B1**
```bash
# Costs ~$10/month
# Includes Always-On
# Better CPU/Memory
az appservice plan create \
  --name plan-LSS-basic \
  --resource-group Portal-Extraction \
  --sku B1 \
  --is-linux
```

**Best Option: Azure Functions** (~$0.20/month)
- True serverless
- Auto-scale
- Built-in timer support
- No always-on needed

---

## 📝 Deployment Status Checklist

- [ ] Pushed changes to GitHub (app.py, startup.sh, requirements.txt)
- [ ] GitHub Actions deployment completed successfully
- [ ] Set startup command in Azure Portal
- [ ] Added all environment variables
- [ ] Clicked Save in Configuration
- [ ] App restarted (wait 2-3 minutes)
- [ ] Health check endpoint works
- [ ] Status endpoint shows all variables configured
- [ ] Manual trigger endpoint works
- [ ] Check logs for any errors
- [ ] Set up GitHub Actions scheduler (optional)

---

## 🔐 Security Checklist

- [ ] Client Secret is stored in Application settings (not in code)
- [ ] Client Secret has expiration date noted
- [ ] HTTPS is enabled (default with *.azurewebsites.net)
- [ ] Consider: Upgrade to custom domain with SSL
- [ ] Consider: Use Azure Key Vault for secrets
- [ ] Review: API permissions are minimal necessary
- [ ] Review: Ensure admin consent is granted

---

## 📞 Support Commands

```bash
# Set variables for easy reference
$APP = "lss-public"
$RG = "Portal-Extraction"

# Check deployment status
az deployment group show --name $APP --resource-group $RG

# View configuration
az webapp config show --name $APP --resource-group $RG

# View app settings
az functionapp config appsettings list --name $APP --resource-group $RG

# Stream logs
az webapp log tail --name $APP --resource-group $RG

# Restart app
az webapp restart --name $APP --resource-group $RG

# Stop app (if needed)
az webapp stop --name $APP --resource-group $RG

# Start app (if stopped)
az webapp start --name $APP --resource-group $RG
```

---

## Next: Optional Upgrades

### 1. Set Up Automated Scheduler
Create `lss-scheduler.yml` in `.github/workflows/` (see above)

### 2. Add Application Insights
```bash
# Enable monitoring
az monitor app-insights create \
  --app lss-automation-insights \
  --resource-group $RG \
  --application-type web
```

### 3. Upgrade to Basic Plan
```bash
# For Always-On and better resources
az appservice plan create \
  --name plan-LSS-basic \
  --resource-group $RG \
  --sku B1 \
  --is-linux
```

### 4. Migrate to Azure Functions
More cost-effective for scheduled tasks (~$0.20/month vs $10/month)

---

## ✨ You're Done!

Your LSS Invoice Automation is now deployed on Azure App Service with:
- ✅ HTTP endpoints for manual triggers
- ✅ Health check monitoring
- ✅ Automatic deployment via GitHub
- ✅ Configuration management via Azure Portal
- ✅ Logging and debugging support

**Next**: Set up the scheduler (GitHub Actions) to automatically run at 9 AM EST weekdays!
