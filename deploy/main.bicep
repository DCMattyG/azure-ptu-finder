// Global parameters
targetScope = 'subscription'

@description('Deployment Location')
param location string = deployment().location

@description('Resource Group Name')
param resourceGroupName string = 'AOAI-PTU-Finder-RG'

@description('Log Analytics Workspace Name')
param workspaceName string = 'AOAI-PTU-Finder-Workspace'

@description('Storage Account Name')
param storageAccountName string = 'staoaiptufinder01'

@description('Storage Account Container Name')
param storageAccountContainerName string = 'ptufinder'

@description('Function Storage Account Name')
param functionStorageAccountName string = 'staoaiptufinderfunc'

@description('Managed Identity Name')
param managedIdentityName string = 'aoaiptufinder-identity'

@description('Function App Name')
param functionAppName string = 'aoaiptufinderfunc10'

@description('Function App Service Plan Name')
param functionPlanName string = 'aoaiptufinderfunc10-asp'

@description('App Service Name')
param appServiceName string = 'aoaiptufinderapp10'

@description('App Service Plan Name')
param appServicePlanName string = 'aoaiptufinderapp10-asp'

@description('Tags')
param tags object = {}

// Resource Group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  location: location
  name: resourceGroupName
  tags: tags
}

// Log Analytics Workspace
module logAnalyticsWorkspace './modules/logAnalyticsWorkspace.bicep' ={
  name: 'logAnalyticsWorkspaceModule'
  scope: resourceGroup
  params: {
    location: location
    workspaceName: workspaceName
  }
}

// Managed Identity for Secure Access to KeyVault
module managedIdentity './modules/managedIdentity.bicep' = {
    name: 'managedIdentityModule'
    scope: resourceGroup
    params: {
      location: location
      managedIdentityName: managedIdentityName
    }
  }

// Storage Account for Function Metadata
module storageAccount './modules/storageAccount.bicep' = {
  scope: resourceGroup
  name: 'storageAccountModule'
  params: {
    location: location
    storageAccountName: storageAccountName
    storageAccountContainerName: storageAccountContainerName
    workspaceId: logAnalyticsWorkspace.outputs.workspaceId
    managedIdentityPrincipalId: managedIdentity.outputs.principalId
  }
}

// Subscription Level Role Assignments
module roleAssignments './modules/roleAssignments.bicep' = {
    name: 'managedIdentityModule'
    scope: subscription()
    params: {
      managedIdentityPrincipalId: managedIdentity.outputs.principalId
    }
  }

// Function App
module functionApp './modules/functionApp.bicep' = {
  scope: resourceGroup
  name: 'functionAppModule'
  params: {
    location: location
    functionAppName: functionAppName
    functionPlanName: functionPlanName
    managedIdentityId: managedIdentity.outputs.id
    managedIdentityClientId: managedIdentity.outputs.clientId
    storageAccountName: storageAccountName
    storageAccountContainerName: storageAccountContainerName
    functionStorageAccountName: functionStorageAccountName
    workspaceId: logAnalyticsWorkspace.outputs.workspaceId
  }
}

// App Service
module appService './modules/appService.bicep' = {
  scope: resourceGroup
  name: 'appServiceModule'
  params: {
    location: location
    appServiceName: appServiceName
    appServicePlanName: appServicePlanName
    managedIdentityId: managedIdentity.outputs.id
    managedIdentityClientId: managedIdentity.outputs.clientId
    storageAccountName: storageAccountName
    storageAccountContainerName: storageAccountContainerName
    workspaceId: logAnalyticsWorkspace.outputs.workspaceId
  }
}
