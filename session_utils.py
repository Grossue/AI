from prompt.few_shot import *
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.chains.combine_documents import create_stuff_documents_chain
from redis_chat_message_history_custom import RedisChatMessageHistory
from redis_client import *


def exist_session(session_id: str):
    key = f"message_store:{session_id}"  # 실제 Redis에 저장된 키 형식과 맞춰야 합니다
    if not redis_client.exists(key):
        raise KeyError(f"'{session_id}'라는 키는 존재하지 않습니다.")

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    # Redis 기반 메시지 히스토리 객체를 반환
    # Redis 연결 설정 -> 커스텀하여 사용
    return RedisChatMessageHistory(session_id=session_id, redis_client=redis_client, ttl=86400)