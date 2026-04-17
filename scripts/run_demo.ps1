$mock = Start-Process -FilePath "python" -ArgumentList "tools/mock_llm.py" -PassThru
Start-Sleep -Seconds 2

Write-Output "Mock LLM PID: $($mock.Id)"
Write-Output "Starting proxy on http://127.0.0.1:8000 ..."

$env:MOCK_LLM_URL = "http://localhost:8001/v1/chat/completions"
$env:UPSTREAM_TIMEOUT_SECONDS = "10"

try {
    python -m uvicorn backend.app.api.proxy:app --host 127.0.0.1 --port 8000 --reload
}
finally {
    if (Get-Process -Id $mock.Id -ErrorAction SilentlyContinue) {
        Stop-Process -Id $mock.Id -Force
        Write-Output "Stopped Mock LLM process."
    }
}

