$env:UPSTREAM_LLM_PROVIDER = "ollama"
$env:OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
$env:OLLAMA_MODEL = "llama3"
$env:UPSTREAM_TIMEOUT_SECONDS = "30"
$env:UPSTREAM_RETRY_COUNT = "1"

Write-Output "Starting proxy with Ollama upstream on http://127.0.0.1:8000 ..."
Write-Output "Ollama URL: $env:OLLAMA_CHAT_URL"
Write-Output "Ollama model: $env:OLLAMA_MODEL"

python -m uvicorn backend.app.api.proxy:app --host 127.0.0.1 --port 8000 --reload
