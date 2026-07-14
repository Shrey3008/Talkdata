from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, dashboards, history, query, rag
from app.config import settings

app = FastAPI(title="TalkData API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rag.router)
app.include_router(query.router)
app.include_router(history.router)
app.include_router(dashboards.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
