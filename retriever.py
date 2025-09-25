import time
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.chains.combine_documents import create_stuff_documents_chain


def get_retriever():
  embedding = OpenAIEmbeddings(model='text-embedding-3-large')

  index_name = 'ss-news'
  
  database = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embedding, text_key="content")
  
  retriever = database.as_retriever(search_kwargs={'k': 4})

  return retriever


def retrieve_docs(user_message):
    retriever = get_retriever()
    start_time = time.time()
    docs = retriever.invoke(user_message)
    end_time = time.time()
    print(f"retriever 소요 시간: {end_time - start_time:.4f}초")
    return docs
