if (-not $env:OLLAMA_MODEL) {
    Write-Error "OLLAMA_MODEL is required. Set it to a model available in your local Ollama installation."
    exit 1
}

if (-not $env:OLLAMA_BASE_URL) {
    $env:OLLAMA_BASE_URL = "http://localhost:11434"
}
if (-not $env:OLLAMA_TIMEOUT_SECONDS) {
    $env:OLLAMA_TIMEOUT_SECONDS = "120"
}
if (-not $env:OLLAMA_MAX_OUTPUT_TOKENS) {
    $env:OLLAMA_MAX_OUTPUT_TOKENS = "1000"
}

$env:LLM_PROVIDER = "ollama"
Write-Output "Starting proxy with local Ollama upstream on $env:OLLAMA_BASE_URL ..."
Write-Output "Ollama model: $env:OLLAMA_MODEL"
Write-Output "Input and output continue through the existing policy and Validator Agent."

python -m uvicorn backend.app.api.proxy:app --host 127.0.0.1 --port 8000
