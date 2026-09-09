from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.websocket import router as websocket_router
from app.api.routes.smart_home import router as smart_home_router
from app.api.routes.assistant import router as assistant_router
from app.core.logging_config import setup_logging
from app.services.smart_home_service import get_smart_home_service
from app.services.ip_camera_service import get_ip_camera_service


def create_app() -> FastAPI:
    setup_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        del app
        service = get_smart_home_service()
        camera_service = get_ip_camera_service()
        service.start()
        camera_service.start()
        try:
            yield
        finally:
            await camera_service.stop()
            service.stop()

    app = FastAPI(title="IoT Smart Home Backend", lifespan=lifespan)
    app.include_router(websocket_router)
    app.include_router(smart_home_router)
    app.include_router(assistant_router)

    frontend_dir = Path(__file__).resolve().parent / "frontend"
    if frontend_dir.exists():
        app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")

        @app.get("/", include_in_schema=False)
        async def serve_frontend() -> FileResponse:
            return FileResponse(frontend_dir / "index.html")
    else:

        @app.get("/", include_in_schema=False)
        async def root_message() -> JSONResponse:
            return JSONResponse({"message": "IoT Smart Home Backend"})
    return app


app = create_app()
