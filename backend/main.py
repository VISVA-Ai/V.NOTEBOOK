from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.engine import Engine
import os

# Engine Singleton
engine: Engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting V.NOTEBOOK Engine...")
    app.state.engine = Engine()
    yield
    print("Shutting down V.NOTEBOOK Engine...")
    # Optional cleanup

app = FastAPI(title="V.NOTEBOOK", version="4.0.0", lifespan=lifespan)

# CORS (Allow all for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes_common import router as common_router
from api.routes_notebook import router as notebook_router
from api.routes_assistant import router as assistant_router
from api.webhooks import router as webhook_router
from api.routes_settings import router as settings_router
from api.routes_auth import router as auth_router

app.include_router(common_router, prefix="/api")
app.include_router(notebook_router, prefix="/api/notebook")
app.include_router(assistant_router, prefix="/api/assistant")
app.include_router(webhook_router, prefix="/api/webhooks")
app.include_router(settings_router, prefix="/api")
app.include_router(auth_router, prefix="/api")

# Serve frontend static files
_frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if not os.path.isdir(_frontend_dir):
    _frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
