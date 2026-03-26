from fastapi import FastAPI
# Для запуска сервера: uvicorn main:app --reload --port 8000

app = FastAPI(tittle='fishmess-server')

@app.get("/")
def root():
    return {"key": "test-key"}

@app.get("/{test_key}")
def test_get(test_key: int, q: str = None):
    return {"key": test_key, "q": q}