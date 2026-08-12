# Azure Deployment Script for LSS Invoice Automation
# This script sets up all necessary Azure resources and deploys the function app

param(
    [string]$ResourceGroup = "lss-automation-rg",
    [string]$Location = "eastus",
    [string]$FunctionAppName = "lss-automation-func",
    [string]$StorageAccountName = "lssautostg$((Get-Random -Minimum 1000 -Maximum 9999))"
)

Write-Host "Starting Azure deployment..." -ForegroundColor Green

# Check if Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "Azure CLI is not installed. Please install it first:" -ForegroundColor Red
    Write-Host "https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
}

# Login to Azure
Write-Host "`nLogging in to Azure..." -ForegroundColor Cyan
az login

# Create resource group
Write-Host "`nCreating resource group: $ResourceGroup" -ForegroundColor Cyan
az group create --name $ResourceGroup --location $Location

# Create storage account
Write-Host "`nCreating storage account: $StorageAccountName" -ForegroundColor Cyan
az storage account create `
    --resource-group $ResourceGroup `
    --name $StorageAccountName `
    --location $Location `
    --sku Standard_LRS

# Get storage connection string
$StorageConnectionString = (az storage account show-connection-string `
    --resource-group $ResourceGroup `
    --name $StorageAccountName `
    --query connectionString -o tsv)

# Create Function App
Write-Host "`nCreating Function App: $FunctionAppName" -ForegroundColor Cyan
az functionapp create `
    --resource-group $ResourceGroup `
    --consumption-plan-location $Location `
    --runtime python `
    --runtime-version 3.11 `
    --functions-version 4 `
    --name $FunctionAppName `
    --storage-account $StorageAccountName `
    --os-type Linux

Write-Host "`n✓ Azure resources created successfully!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Update local.settings.json with your Azure AD credentials"
Write-Host "2. Run: func azure functionapp publish $FunctionAppName --build remote"
Write-Host "3. Configure environment variables in Azure Portal"
Write-Host "`nResource Group: $ResourceGroup"
Write-Host "Function App: $FunctionAppName"
Write-Host "Storage Account: $StorageAccountName"
