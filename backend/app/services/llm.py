import os
from functools import lru_cache

from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_openai import ChatOpenAI

from app.config import settings


# ponytail: one cached client for the process — extraction fires hundreds of calls
# concurrently, and a fresh ChatOpenAI per call builds a fresh HTTP connection pool
# each time, paying the TLS handshake over and over.
@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0,
        # A long document's extraction runs into the account's tokens-per-minute
        # ceiling. Firing every call at once and retrying the 429s is worse than
        # useless: the backoff thrash measured *lower* throughput than pacing, and
        # calls that exhaust their retries drop their sections from the document
        # entirely. Pacing releases calls just under the ceiling instead.
        rate_limiter=InMemoryRateLimiter(
            requests_per_second=float(os.environ.get("EXTRACTION_RPS", "1.3")),
            check_every_n_seconds=0.1,
            # A small bucket still absorbs a short lull without letting the start of
            # a document burst straight through the ceiling.
            max_bucket_size=4,
        ),
        max_retries=8,
        timeout=180,
    )
