$env:MOCK_LLM_URL = "http://localhost:8001/v1/chat/completions"
$env:LLM_PROVIDER = "mock"
$env:UPSTREAM_TIMEOUT_SECONDS = "10"
python -m uvicorn backend.app.api.proxy:app --host 127.0.0.1 --port 8000 --reload
