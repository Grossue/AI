import redis
import os
from dotenv import load_dotenv

load_dotenv()

redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")

redis_client = redis.Redis(
    host=redis_host,
    port= int(redis_port),
    db=0,              # 기본 DB
    #decode_responses=True  # 문자열 자동 디코딩
    # ssl=True,
    # ssl_cert_reqs=None
)