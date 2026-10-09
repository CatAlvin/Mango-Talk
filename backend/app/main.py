from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.rooms import router as rooms_router
from app.api.messages import router as messages_router
from app.api.ws import router as ws_router
from app.api.uploads import router as uploads_router
from app.core.config import settings
from app.db.session import test_db_connection

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(rooms_router)
app.include_router(messages_router)
app.include_router(ws_router)
app.include_router(uploads_router)


@app.get("/")
def root():
    return {
        "message": "Mango Talk API is running",
        "env": settings.APP_ENV,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    test_db_connection()
    return {"status": "ok", "database": "connected"}
