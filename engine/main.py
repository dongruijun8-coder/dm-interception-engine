"""FastAPI application entry point."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from engine.router_dashboard import router
from engine.db import init_db

app = FastAPI(title="截流引擎", version="0.1.0")
app.include_router(router)

STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/")
async def index():
    html_file = STATIC_DIR / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return {"message": "Dashboard HTML not found. Place index.html in engine/static/"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("engine.main:app", host="127.0.0.1", port=8765, reload=True)
