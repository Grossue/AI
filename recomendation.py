import numpy as np
from datetime import datetime
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

# ----------------------------
# Pinecone 초기화
# ----------------------------
def init_pinecone():
    index_name = 'ss-issue'
    pc = Pinecone()
    index = pc.Index(index_name)
    return index

index = init_pinecone()
embed_model = OpenAIEmbeddings(
    model='text-embedding-3-large'
)
LAMBDA_DECAY = 0.1


# ----------------------------
# 시간 가중치 계산
# ----------------------------
def compute_time_weight(read_date):
    days_diff = (datetime.now() - read_date).days
    return np.exp(-LAMBDA_DECAY * days_diff)

# ----------------------------
# 사용자 벡터 생성
# ----------------------------
def build_user_vector(user_history):
    vectors = []
    for item in user_history:
        vector = embed_model.embed_query(item.title)
        weight = compute_time_weight(item.date_time)
        vectors.append(weight * np.array(vector))
    if vectors:
        return np.mean(vectors, axis=0)
    return None

# ----------------------------
# Pinecone에서 추천
# ----------------------------
def recommend_articles(user_vector, top_k=10):
    response = index.query(
        vector=user_vector.tolist(),
        top_k=top_k,
        include_values=False,
        include_metadata=True
    )
    return response['matches']

# ----------------------------
# 전체 추천 함수
# ----------------------------
def get_recommendations(user_history):
    user_vector = build_user_vector(user_history)
    if user_vector is None:
        return []

    matches = recommend_articles(user_vector)

    read_titles = {item.title for item in user_history}
    recommended_titles = [
        match['metadata']['name']
        for match in matches
        if match['metadata']['name'] not in read_titles
    ]

    return recommended_titles
