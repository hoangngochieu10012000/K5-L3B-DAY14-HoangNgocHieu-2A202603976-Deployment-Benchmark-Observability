"""
Trợ lý AI sẵn sàng vận hành — Part 6.

Chạy kiểm tra đầy đủ bằng:
    python check_production_ready.py
"""
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .auth import verify_api_key
from .config import settings
from .cost_guard import check_budget, record_cost
from .rate_limiter import check_rate_limit
from .redis_client import redis_healthy
from utils.mock_llm import ask as llm_ask


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
        }
        for field in ("method", "path", "status", "duration_ms"):
            if hasattr(record, field):
                data[field] = getattr(record, field)
        return json.dumps(data, ensure_ascii=False)


logger = logging.getLogger("production_agent")
logger.setLevel(logging.INFO)
logger.handlers.clear()
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.propagate = False


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("startup", extra={"event": "startup", "environment": settings.environment})
    try:
        yield
    finally:
        logger.info("shutdown", extra={"event": "shutdown"})


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str | None = None


def _answer_question(question: str, api_key: str) -> dict[str, str]:
    check_rate_limit(api_key)
    check_budget()
    answer = llm_ask(question)
    input_tokens = max(1, len(question.split()) * 2)
    output_tokens = max(1, len(answer.split()) * 2)
    record_cost(input_tokens, output_tokens)
    return {"question": question, "answer": answer}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    logger.info(
        "http_request",
        extra={
            "event": "http_request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        },
    )
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, bool]:
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis is not ready")
    return {"ready": True}


@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    return _answer_question(body.question, api_key)


@app.post("/demo/ask")
def demo_ask(body: AskRequest):
    if not settings.agent_api_key:
        raise HTTPException(status_code=503, detail="Public demo is not configured")
    return _answer_question(body.question, settings.agent_api_key)
