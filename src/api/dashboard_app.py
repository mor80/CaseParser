"""Serve React frontend build."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="CaseParser Frontend", docs_url=None, redoc_url=None)

dist_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
assets_path = dist_path / "assets"

if assets_path.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(assets_path)),
        name="frontend-assets",
    )


@app.get("/{full_path:path}")
async def serve_spa(full_path: str = "") -> FileResponse:
    """Serve React SPA for any route."""
    index_file = dist_path / "index.html"
    if not index_file.exists():
        raise HTTPException(
            status_code=500,
            detail="Frontend build not found. Run `npm install && npm run build` inside frontend.",
        )
    return FileResponse(index_file)
