from langchain_pinecone import PineconeVectorStore
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


def get_recommendation_retriever():
  embedding = OpenAIEmbeddings(model='text-embedding-3-large')

  index_name = 'ss-issue'
  
  database = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embedding, text_key="name")
  
  retriever = database.as_retriever(search_kwargs={'k': 4})

  return retriever

def get_recommendation(article_title: str):
    retriever = get_recommendation_retriever()
    docs = retriever.invoke(article_title)
    print(f"총 검색된 문서 수: {len(docs)}")

    if not docs:
        return {
            "recommendations": [],
            "total": 0
        }

    # article_content와 동일한 문서는 제외
    filtered = [doc.page_content.strip() for doc in docs if doc.page_content.strip() != article_title.strip()]

    # 최대 3개까지만 선택
    recommendations = filtered[:3]

    return {
        "recommendations": recommendations,
        "total": len(docs)
    }



# def get_recommendation(article_content: str):
#   # 1. 임베딩 모델 및 Pinecone retriever 준비
#   embedding_model = OpenAIEmbeddings(model='text-embedding-3-large')
#   retriever = get_retriever()

#   # 2. 생성된 기사 내용을 쿼리로 사용해 유사 기사 검색
#   docs = retriever.invoke(article_content)
#   print(f"총 검색된 문서 수: {len(docs)}")

#   if not docs:
#       return {
#           "summaries": [],
#           "clusters": [],
#           "total": 0
#       }

#   # 3. 검색된 기사 본문(content) 벡터화
#   contents = [doc.page_content for doc in docs]
#   embeddings = embedding_model.embed_documents(contents)
#   vectors = np.array(embeddings)

#   # 4. 군집 수 하드코딩 (예: 3개 주제로 분류)
#   n_clusters = 3
#   kmeans = KMeans(n_clusters=n_clusters, random_state=42)
#   labels = kmeans.fit_predict(vectors)

#   # 5. 군집별 기사 내용/메타 정보 분류
#   clustered_docs = [[] for _ in range(n_clusters)]
#   clustered_meta = [[] for _ in range(n_clusters)]

#   for i, label in enumerate(labels):
#       clustered_docs[label].append(docs[i].page_content)
#       clustered_meta[label].append({
#           "title": docs[i].metadata.get("title", ""),
#           "url": docs[i].metadata.get("url", ""),
#           "date": docs[i].metadata.get("date_time", "")
#       })

#     # 6. 각 군집을 LLM으로 요약
#   llm = get_llm()
#   prompt_template = ChatPromptTemplate.from_messages([
#       ("system", "다음 기사들을 기반으로 주제를 요약해서 제목을 생성해줘. 가능한 한 핵심 내용을 간결하게 뽑아줘."),
#       ("human", "{docs}"),
#   ])
#   llm_chain = LLMChain(llm=llm, prompt=prompt_template)

#   summaries = []
#   for cluster in clustered_docs:
#       joined_text = "\n".join(cluster)
#       response = llm_chain.invoke({"docs": joined_text})
#       summaries.append(response)

#   # 7. 최종 결과 반환
#   return {
#       "summaries": summaries,
#       "clusters": clustered_meta,
#       "total": len(docs)
#   }