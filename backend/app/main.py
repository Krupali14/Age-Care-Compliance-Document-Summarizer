import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import actions, deadlines, obligations, risks, summarize, upload

app = FastAPI(title="Aged Care Compliance Summariser API")

frontend_origin = os.environ.get("VITE_API_URL_ORIGIN", "http://localhost:3002")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(summarize.router)
app.include_router(obligations.router)
app.include_router(risks.router)
app.include_router(deadlines.router)
app.include_router(actions.router)


@app.get("/health")
def health():
    return {"status": "ok"}
