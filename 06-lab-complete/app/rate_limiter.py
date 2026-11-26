"""
Rate limiting (tiêu chí 7).

Yêu cầu:
  • Mỗi API key tối đa RATE_LIMIT_PER_MINUTE request trong 60 giây (sliding window)
  • Vượt giới hạn → HTTP 429, nên kèm header Retry-After
  • State lưu trong Redis để mọi worker / instance dùng chung và vẫn còn sau khi
    restart agent (script chấm sẽ restart agent để kiểm tra)
"""
import hashlib
import time
import uuid

from fastapi import HTTPException

from .config import settings
from .redis_client import r

_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = math.max(1, math.ceil(window - (now - tonumber(oldest[2]))))
    return {0, retry_after}
end

redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, window)
return {1, limit - count - 1}
"""


def check_rate_limit(key: str) -> None:
    window_seconds = 60
    now = time.time()
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    redis_key = f"agent:rate:{key_hash}"
    member = f"{now:.6f}:{uuid.uuid4().hex}"
    allowed, retry_after = r.eval(
        _SLIDING_WINDOW_SCRIPT,
        1,
        redis_key,
        now,
        window_seconds,
        settings.rate_limit_per_minute,
        member,
    )
    if not int(allowed):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(retry_after))},
        )
