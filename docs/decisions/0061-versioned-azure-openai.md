# 0061: Custom providers can use versioned Azure OpenAI deployments

Status proposed 2026-11-27.

## Context

[Decision 0055](0055-a-provider-has-a-protocol-and-many-models-described-by-a-bundled-catalog.md)
reserves a decision for Azure. A versioned Azure endpoint routes chat requests by deployment
name and API version. A gateway can expose that endpoint without model discovery.

## Decision

Offer versioned Azure OpenAI as an explicit API format in Custom Provider. Use the resource
endpoint, API version, and API key to configure the Azure SDK adapter. Each model ID in the
app names a deployment. Display manual model entry for Azure. Model settings without an API
format continue to use the existing OpenAI-compatible adapter.

## Consequences

Azure deployments use the same picker, key storage and on-demand tests as other providers.
The tests use the selected deployment. The Azure option supports API-key authentication.
