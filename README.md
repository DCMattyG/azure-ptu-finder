# Azure PTU Finder App

## Prerequisites

- Either Azure PowerShell or Azure CLI installed
- Bicep support enabled for either Azure PowerShell or Azure CLI

## Deployment Steps

1. Clone GitHub repo
2. Make sure you are using the `main` branch
3. Make a copy of `main.example.bicepparam` and rename to `main.bicepparam`
4. Customize desired Bicep deployment variables
5. Deploy using steps below

> NOTE: None of the Variables are required

## Clone GitHub Repo

If you haven't yet cloned the Azure PTU Finder repo, please do so using the following steps.

```bash
git clone github.com/dcmattyg/azure-ptu-finder

cd azure-ptu-finder
```

## Switch to Main Branch

Make sure you are working with the `main` branch prior to deploying the Azure PTU Finder.

```bash
git checkout main
```

## Pull Latest Code

If you've already clone the Azure PTU Finder repo and need to fetch the latest code, please do so using the following steps.

```bash
cd <azure-ptu-finder-directory>

git pull
```

## Deploy the Azure PTU Finder Solution

You may deploy the Azure PTU Finder uding either Azure PowerShell or Azure CLI by following the instructions below.

### Azure PowerShell Deployment

```pwsh
Connect-AzAccount -UseDeviceAuthentication

Set-AzContext -Subscription <Target Subscription ID>

cd deploy

New-AzSubscriptionDeployment -Name "AzurePTUFinder" -Location <Location> -TemplateParameterFile .\main.bicepparam

cd assets

Publish-AzWebApp -ResourceGroupName <Resource Group Name> -Name <Function App Name> -ArchivePath .\functionapp.zip -Restart -Force

Publish-AzWebApp -ResourceGroupName <Resource Group Name> -Name <App Service Name> -ArchivePath .\webapp.zip -Restart -Force
```

### Azure CLI Deployment

```bash
az login --use-device-code

az account set -s <subscription-id>

cd deploy

az deployment sub create --location <location> --template-file .\main.bicepparam

cd assets

az webapp deploy --resource-group <resource-group-name> --name <func-app-name> --type zip --src-path .\functionapp.zip --restart

az webapp deploy --resource-group <resource-group-name> --name <app-service-name> --type zip --src-path .\webapp.zip --restart
```
