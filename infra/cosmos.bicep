// Azure Cosmos DB — serverless NoSQL for run history and audit trail

param prefix string
param location string
param tags object

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: '${prefix}-cosmos'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    publicNetworkAccess: 'Enabled'
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmosAccount
  name: 'riskscout'
  properties: {
    resource: {
      id: 'riskscout'
    }
  }
}

resource runsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'runs'
  properties: {
    resource: {
      id: 'runs'
      partitionKey: {
        paths: ['/partitionKey']
        kind: 'Hash'
      }
      defaultTtl: -1  // No TTL — retain all records
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          { path: '/*' }
        ]
      }
    }
  }
}

output endpoint string = cosmosAccount.properties.documentEndpoint
output accountName string = cosmosAccount.name
output primaryKey string = cosmosAccount.listKeys().primaryMasterKey
