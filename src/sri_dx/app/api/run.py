"""Entry point: uv run python -m sri_dx.app.api.run"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "sri_dx.app.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
