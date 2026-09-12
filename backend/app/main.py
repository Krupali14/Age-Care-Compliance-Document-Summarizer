import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import SessionLocal
from app.models import Document
from app.routers import actions, auth, chat, deadlines, documents, eval, obligations, risks, summarize, upload

logger = logging.getLogger(__name__)

INTERRUPTED_MESSAGE = (
    "Processing was interrupted before it finished, most likely by a server "
    "restart. Upload the document again."
)


def _release_interrupted_documents() -> None:
    """Fail anything left mid-processing by the previous run of this process.

    Extraction runs in a FastAPI background task, so it lives and dies with the
    process. A restart mid-extraction left the row on "processing" forever: the
    dashboard polled it indefinitely, the document never finished, and nothing
    would ever pick it up again — ten documents were found stranded that way after
    a single deploy-sized restart.

    At startup nothing is running by definition, so any row still in a working
    state is a casualty of the last shutdown. Marking it failed turns an invisible
    permanent hang into a state the user can act on.

    ponytail: this is recovery, not a queue. A real queue would re-run the work
    instead of asking the user to upload again — see docs/PROCESSING_PIPELINE.md.
    """
    # The session is opened inside the try: if the database is unreachable,
    # SessionLocal() itself raises, and closing it in a finally would then fail on
    # an unbound name — turning a tidy-up problem into a server that will not start.
    db = None
    try:
        db = SessionLocal()
        stranded = db.query(Document).filter(Document.status.in_(["pending", "processing"])).all()
        for document in stranded:
            document.status = "failed"
            document.error_message = INTERRUPTED_MESSAGE
        if stranded:
            db.commit()
            logger.warning(
                "Released %s document(s) left mid-processing by a previous run: %s",
                len(stranded), [d.id for d in stranded],
            )
    except Exception:  # noqa: BLE001 - startup must not fail because of cleanup
        logger.exception("Could not release interrupted documents at startup")
    finally:
        if db is not None:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _release_interrupted_documents()
    yield


app = FastAPI(title="Aged Care Compliance Summariser API", lifespan=lifespan)

frontend_origin = os.environ.get("VITE_API_URL_ORIGIN", "http://localhost:3002")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(documents.router)
app.include_router(summarize.router)
app.include_router(obligations.router)
app.include_router(risks.router)
app.include_router(deadlines.router)
app.include_router(actions.router)
app.include_router(eval.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
