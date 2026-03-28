"""
main.py
ComplianceOS - FastAPI application entry point.
Run: uvicorn main:app --reload --port 8000
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from api.routes_alerts import router as alerts_router
from api.routes_analysis import router as analysis_router
from api.routes_business import router as business_router
from api.routes_reports import router as reports_router
from database.db_manager import get_db_stats, init_db

sys.path.insert(0, str(Path(__file__).parent))


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n[Startup] ComplianceOS starting up...")
    init_db()

    try:
        from agents.monitor_agent import run as monitor_run

        monitor_run(create_alerts=False)
        print("   [OK] Monitor agent initialised")
    except Exception as exc:
        print(f"   [Warn] Monitor agent startup error: {exc}")

    print("   [OK] ComplianceOS ready\n")
    yield
    print("\n[Shutdown] ComplianceOS shutting down...")


app = FastAPI(
    title="ComplianceOS API",
    description="Multi-agent regulatory compliance intelligence for Indian MSMEs and FinTechs",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ui_path = Path(__file__).parent / "ui"
if ui_path.exists():
    static_path = ui_path / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

app.include_router(business_router, prefix="/api/business", tags=["Business"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(reports_router, prefix="/api/reports", tags=["Reports"])


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    index = ui_path / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return HTMLResponse("<h2>ComplianceOS API running. UI not found - place index.html in /ui/</h2>")


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "db_stats": get_db_stats(),
    }


@app.get("/api/stats")
async def stats():
    return get_db_stats()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
