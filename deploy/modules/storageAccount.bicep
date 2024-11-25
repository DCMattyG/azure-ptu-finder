@description('Deployment Location')
param location string = resourceGroup().location

@description('Storage Account Name')
param storageAccountName string

@description('Storage Account Container Name')
param storageAccountContainerName string

@description('Log Analytics Workspace ID')
param workspaceId string

@description('Managed Identity Principal ID')
param managedIdentityPrincipalId string

var storageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var storageBlobDataContributorId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributor)
var storageBlobDataContributorRoleAssignmentId = guid(resourceGroup().id, storageBlobDataContributor, managedIdentityPrincipalId)

resource storageAccount 'Microsoft.Storage/storageAccounts@2021-06-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2021-06-01' = {
  name: 'default'
  parent: storageAccount
}

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-06-01' =  {
  parent: blobService
  name: storageAccountContainerName
  properties: {
    publicAccess: 'None'
    metadata: {}
  }
}

resource diagnosticSettingsAccount 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagSettingsAccount'
  scope: storageAccount
  properties: {
    metrics: [
      {
        category: 'Transaction'
        enabled: true
        retentionPolicy: {
          days: 0
          enabled: false
        }
      }
    ]
    workspaceId: workspaceId
  }
}

resource diagnosticSettingsBlob 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagSettingsBlob'
  scope: blobService
  properties: {
    logs: [
      {
        category: 'StorageRead'
        enabled: true
        retentionPolicy: {
          days: 0
          enabled: false 
        }
      }
      {
        category: 'StorageWrite'
        enabled: true
        retentionPolicy: {
          days: 0
          enabled: false 
        }
      }
      {
        category: 'StorageDelete'
        enabled: true
        retentionPolicy: {
          days: 0
          enabled: false 
        }
      }
    ]
    metrics: [
      {
        category: 'Transaction'
        enabled: true
        retentionPolicy: {
          days: 0
          enabled: false
        }
      }
    ]
    workspaceId: workspaceId
  }
}

resource storageBlobDataContributorAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: storageBlobDataContributorRoleAssignmentId
  scope: storageAccount
  properties: {
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataContributorId
    principalId: managedIdentityPrincipalId
  }
}

output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
