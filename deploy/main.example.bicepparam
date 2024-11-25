using './main.bicep'

param resourceGroupName = 'AOAI-PTU-Finder-RG'
param workspaceName = 'AOAI-PTU-Finder-Workspace'
param storageAccountName = 'staoaiptufinder'
param storageAccountContainerName = 'ptufinder'
param functionStorageAccountName = 'staoaiptufinderfunc'
param managedIdentityName = 'aoaiptufinder-identity'
param functionAppName = 'aoaiptufinderfunc'
param functionPlanName = 'aoaiptufinderfunc-asp'
param appServiceName = 'aoaiptufinderapp'
param appServicePlanName = 'aoaiptufinderapp-asp'
param tags = {
  CostCenter: '0123456789'
}
