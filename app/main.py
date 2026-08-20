from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.models.user import User
from app.models.sync import MobilityTrip, SyncJob
from app.models.token import TokenBlacklist, PasswordResetToken
from app.models.datapoint import DataPoint
from app.models.zone import Zone
from app.routes import auth, sync, users, datapoints, zones, dashboard, analysis
from app.routes import map as map_routes
from app.services.scheduler import start_scheduler, stop_scheduler
from app.models.notification import Notification
from app.routes import auth, sync, users, datapoints, zones, dashboard, analysis, notifications

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    await stop_scheduler()


app = FastAPI(title="GeoPulse API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


app.add_middleware(
    CORSMiddleware,
    # Vite (Frontend/vite.config.ts) n'a pas de port fixé -> il tourne sur son
    # port par défaut (5173), pas 3000 : on dérive l'origine autorisée de
    # settings.URL_FRONTEND pour ne plus jamais désynchroniser CORS et les
    # liens envoyés par email (invite/reset-password).
    allow_origins=[settings.URL_FRONTEND],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sync.router)
app.include_router(users.router)
app.include_router(datapoints.router)
app.include_router(zones.router)
app.include_router(dashboard.router)
app.include_router(analysis.router)
app.include_router(map_routes.router)
app.include_router(notifications.router)

@app.get("/")
def home():
    return {"message": "API OK"}
