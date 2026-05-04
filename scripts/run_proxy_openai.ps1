if (-not $env:OPENAI_API_KEY) {
    Write-Error "OPENAI_API_KEY is required. Set it before running this script."
    exit 1
}

$env:UPSTREAM_LLM_PROVIDER = "openai"
if (-not $env:OPENAI_CHAT_URL) {
    $env:OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
}
if (-not $env:OPENAI_MODEL) {
    $env:OPENAI_MODEL = "gpt-4o-mini"
}
if (-not $env:UPSTREAM_TIMEOUT_SECONDS) {
    $env:UPSTREAM_TIMEOUT_SECONDS = "30"
}
if (-not $env:UPSTREAM_RETRY_COUNT) {
    $env:UPSTREAM_RETRY_COUNT = "1"
}

Write-Output "Starting proxy with OpenAI upstream on http://127.0.0.1:8000 ..."
Write-Output "OpenAI URL: $env:OPENAI_CHAT_URL"
Write-Output "OpenAI model: $env:OPENAI_MODEL"

python -m uvicorn backend.app.api.proxy:app --host 127.0.0.1 --port 8000
