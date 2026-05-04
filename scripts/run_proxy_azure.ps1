if (-not $env:AZURE_OPENAI_API_KEY) {
    Write-Error "AZURE_OPENAI_API_KEY is required. Set it before running this script."
    exit 1
}
if (-not $env:AZURE_OPENAI_CHAT_URL) {
    Write-Error "AZURE_OPENAI_CHAT_URL is required. Use your Azure deployment chat completions endpoint."
    exit 1
}

$env:UPSTREAM_LLM_PROVIDER = "azure"
if (-not $env:AZURE_OPENAI_API_VERSION) {
    $env:AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
}
if (-not $env:AZURE_OPENAI_DEPLOYMENT) {
    $env:AZURE_OPENAI_DEPLOYMENT = "azure-deployment"
}
if (-not $env:UPSTREAM_TIMEOUT_SECONDS) {
    $env:UPSTREAM_TIMEOUT_SECONDS = "30"
}
if (-not $env:UPSTREAM_RETRY_COUNT) {
    $env:UPSTREAM_RETRY_COUNT = "1"
}

Write-Output "Starting proxy with Azure OpenAI upstream on http://127.0.0.1:8000 ..."
Write-Output "Azure OpenAI URL: $env:AZURE_OPENAI_CHAT_URL"
Write-Output "Azure deployment: $env:AZURE_OPENAI_DEPLOYMENT"
Write-Output "Azure API version: $env:AZURE_OPENAI_API_VERSION"

python -m uvicorn backend.app.api.proxy:app --host 127.0.0.1 --port 8000
