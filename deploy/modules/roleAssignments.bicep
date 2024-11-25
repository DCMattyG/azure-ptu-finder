targetScope = 'subscription'

@description('Managed Identity Principal ID')
param managedIdentityPrincipalId string

var reader = 'acdd72a7-3385-48ef-bd42-f606fba81ae7'
var readerId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', reader)
var readerRoleAssignmentId = guid(subscription().id, reader, managedIdentityPrincipalId)

resource readerAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: readerRoleAssignmentId
  properties: {
    principalType: 'ServicePrincipal'
    roleDefinitionId: readerId
    principalId: managedIdentityPrincipalId
  }
}
