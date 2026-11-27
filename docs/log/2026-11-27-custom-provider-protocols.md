# Custom model entry, a provider test and additional API formats (shipped)

Users who know their model ID or deployment name can connect without model discovery, and one
test tells them whether the model can do the agent's work.

## Shipped

- The Providers settings page always offers manual model entry, and one on-demand test per
  model: a streamed tool call, then a streamed reply that uses the tool's result. The error says
  which step failed. Each request has its own 60-second limit, so reasoning models finish.
- Custom providers can use Responses or versioned Azure OpenAI with an API key. Legacy
  configurations use their existing resolution path. See decision 0061 for Azure. The Azure
  form points an `/openai/v1` endpoint to the OpenAI compatible format.

## Verified

- The test passed live against DeepSeek (`deepseek-chat` and `deepseek-reasoner`) and failed with
  the tool-calling message against the stub model, which only answers "OK".

## Not verified

- Live Azure and Responses vendor accounts. The integration tests exercise SDK requests and
  streamed responses for all three formats.
