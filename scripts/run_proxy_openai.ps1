if (-not $env:OPENAI_API_KEY) {
    Write-Error "OPENAI_API_KEY is required. Set it before running this script."
    exit 1
}
if (-not $env:OPENAI_MODEL) {
    Write-Error "OPENAI_MODEL is required. Set it to a model available to your OpenAI project."
    exit 1
}

$env:LLM_PROVIDER = "openai"
if (-not $env:OPENAI_TIMEOUT_SECONDS) {
    $env:OPENAI_TIMEOUT_SECONDS = "30"
}
if (-not $env:OPENAI_MAX_OUTPUT_TOKENS) {
    $env:OPENAI_MAX_OUTPUT_TOKENS = "1000"
}

Write-Output "Starting proxy with OpenAI upstream on http://127.0.0.1:8000 ..."
Write-Output "OpenAI model: $env:OPENAI_MODEL"
Write-Output "Responses are requested with store=False and SDK retries disabled."

python -m uvicorn backend.app.api.proxy:app --host 127.0.0.1 --port 8000
