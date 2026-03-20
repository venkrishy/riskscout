// RiskScout — Azure infrastructure entry point
// Orchestrates all resource modules

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Azure region for OpenAI (must have gpt-4o quota)')
param openAiLocation string = 'eastus2'

@description('Environment name (dev / staging / prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Azure Container Registry login server')
param containerRegistryServer string

@description('Container image tag to deploy')
param imageTag string = 'latest'

@secure()
@description('Azure OpenAI API key')
param azureOpenAiApiKey string

@secure()
@description('Azure AI Search admin key')
param azureSearchApiKey string

var prefix = 'riskscout-${environment}'
var tags = {
  project: 'riskscout'
  environment: environment
  managedBy: 'bicep'
}

// ---------------------------------------------------------------------------
// Log Analytics + Application Insights
// ---------------------------------------------------------------------------

module monitoring 'monitoring.bicep' = {
  name: 'monitoring'
  params: {
    prefix: prefix
    location: location
    tags: tags
  }
}

// ---------------------------------------------------------------------------
// Azure OpenAI
// ---------------------------------------------------------------------------

module openai 'openai.bicep' = {
  name: 'openai'
  params: {
    prefix: prefix
    location: openAiLocation
    tags: tags
  }
}

// ---------------------------------------------------------------------------
// Azure AI Search
// ---------------------------------------------------------------------------

module aiSearch 'ai-search.bicep' = {
  name: 'ai-search'
  params: {
    prefix: prefix
    location: location
    tags: tags
  }
}

// ---------------------------------------------------------------------------
// Cosmos DB
// ---------------------------------------------------------------------------

module cosmos 'cosmos.bicep' = {
  name: 'cosmos'
  params: {
    prefix: prefix
    location: location
    tags: tags
  }
}

// ---------------------------------------------------------------------------
// Container App
// ---------------------------------------------------------------------------

module containerApp 'container-app.bicep' = {
  name: 'container-app'
  params: {
    prefix: prefix
    location: location
    tags: tags
    containerRegistryServer: containerRegistryServer
    imageTag: imageTag
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    azureOpenAiEndpoint: openai.outputs.endpoint
    azureOpenAiApiKey: azureOpenAiApiKey
    azureSearchEndpoint: aiSearch.outputs.endpoint
    azureSearchApiKey: azureSearchApiKey
    cosmosEndpoint: cosmos.outputs.endpoint
    cosmosKey: cosmos.outputs.primaryKey
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

output containerAppUrl string = containerApp.outputs.url
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString
output cosmosEndpoint string = cosmos.outputs.endpoint
output searchEndpoint string = aiSearch.outputs.endpoint
output openAiEndpoint string = openai.outputs.endpoint
