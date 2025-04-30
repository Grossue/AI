from dotenv import load_dotenv
from config import *
import time

# LangChain OpenAI 관련 모듈
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# LangChain Pinecone 관련 모듈
from langchain_pinecone import PineconeVectorStore

# LangChain Core 모듈
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables import RunnableSequence
from langchain_core.runnables.history import RunnableWithMessageHistory

# LangChain Chains 관련 모듈
from langchain.chains import RetrievalQA, LLMChain, create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# LangChain Community 모듈
from langchain_community.chat_message_histories import ChatMessageHistory

store = {}

def get_llm(model="gpt-4o"):
  llm = ChatOpenAI(model=model)
  return llm

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


def get_retriever():
  embedding = OpenAIEmbeddings(model='text-embedding-3-large')

  index_name = 'tax-index'
  
  database = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embedding,text_key="content")
  
  retriever = database.as_retriever(search_kwargs={'k': 5})

  return retriever



def get_rag_chain_v1(llm,retriever,level):

  example_prompt = ChatPromptTemplate.from_messages(
      [
          ("human", "{input}"),
          ("ai", "{answer}"),
      ]
  )
  few_shot_prompt = FewShotChatMessagePromptTemplate(
      example_prompt=example_prompt,
      examples= create_article_examples,
  )

  level_1 = (
      "당신은 어린이(8세-14세)를 위해 뉴스 기사를 알기 쉽게 설명하는 사람입니다. "
      "어려운 단어는 쉽게 풀어 작성해주시고, "
      "스토링텔링 형식으로 기사들을 설명해주세요. "
      "같이 넘겨준 기사 내용을 최대한 활용해줘."
  )
  
  level_2 = (
    "당신은 15세 이상의 사람들을 위해 뉴스 기사를 알기 쉽게 설명하는 사람입니다. "
    "사용자가 입력한 주제에 대해서 기사 형식으로 글을 생성해주세요."
    "같이 넘겨준 기사 내용을 최대한 활용해줘."
  )

  system_prompt = (
    "제공되는 주제와 관련된 기존 기사를 조합하여 4000자 이상의 새로운 글과 이에 대한 3지선다 퀴즈 3문제를 만들어주세요. "
    "다음 9가지 조건을 모두 지켜주세요. \n"
    "0. 사용자의 질문에 대한 답만 해주는 것이 아니라, 넘겨준 context에 담긴 내용 전부를 이용해서 글을 만들어주세요. \n"
    "1. 글은 4000자 이상이여야합니다. \n"
    "2. 생성된 글에 대한 기사 제목도 만들어주시고, 'title' 속성에 담아주세요.\n"
    "3. 문단을 적절히 나누어야 합니다.\n"
    "4. 꼭 함께 넘겨주는 문서 내용을 이용해야 합니다.\n"
    "5. 답은 json 형식으로 만들어주시고, 새로운 기사 제목은 'title'에, 새로운 기사 내용은 'article' 속성에 넣어주시고 , 퀴즈는 'quiz'속성에 리스트로 넣어주세요. \n"
    "6. quiz 와 함께 correct_answer에 숫자로 정답을 넣어주세요. 첫번째 선지가 정답이면 0, 두번째 선지가 정답이면 1이입니다.\n"
    "7. 글을 생성할때 사용한 기사의 url들을 url 속성에 담아주세요. \n"
    "8. 넘겨준 자료들에 담긴 정보들만을 이용하여 글을 생성해주세요.  \n"
    "9. 사건을 말할때는 날짜 정보를 포함하여 주세요. "
    "\n\n"
    "{context}"
  )

  # 레벨에 따라 system_prompt 앞에 추가
  if level == 1:
      system_prompt = level_1 + "\n" + system_prompt
  elif level == 2:
      system_prompt = level_2 + "\n" + system_prompt

  qa_prompt = ChatPromptTemplate.from_messages(
      [
          ("system", system_prompt), # llm의 역할
          few_shot_prompt, # 예제를 많이 넣으면 넣을수록 .. 
          MessagesPlaceholder("chat_history"),
          ("human", "{input}"),
      ]
  )
  
  question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

  rag_chain = create_retrieval_chain(retriever, question_answer_chain) 

  conversational_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
  )
  return conversational_rag_chain



def get_rag_chain_v2(llm,retriever,level):

  example_prompt = ChatPromptTemplate.from_messages(
      [
          ("human", "{input}"),
          ("ai", "{answer}"),
      ]
  )

  few_shot_prompt = FewShotChatMessagePromptTemplate(
      example_prompt=example_prompt,
      examples= create_article_examples,
  )

  level_1 = (
      "당신은 어린이(8세-14세)를 위해 뉴스 기사를 알기 쉽게 설명하는 사람입니다. "
      "어려운 단어는 쉽게 풀어 작성해주시고, "
      "스토링텔링 형식으로 기사들을 설명해주세요. "
      "같이 넘겨준 기사 내용을 최대한 활용해줘."
  )
  
  level_2 = (
    "당신은 15세 이상의 사람들을 위해 뉴스 기사를 알기 쉽게 설명하는 사람입니다. "
    "사용자가 입력한 주제에 대해서 기사 형식으로 글을 생성해주세요."
    "같이 넘겨준 기사 내용을 최대한 활용해줘."
  )
  
  system_prompt = (
    "제공되는 주제와 관련된 기존 기사를 조합하여 4000자 이상의 새로운 글과 이에 대한 3지선다 퀴즈 3문제를 만들어주세요. "
    "다음 9가지 조건을 모두 지켜주세요. \n"
    "0. 사용자의 질문에 대한 답만 해주는 것이 아니라, 넘겨준 context에 담긴 내용 전부를 이용해서 글을 만들어주세요. \n"
    "1. 글은 4000자 이상이여야합니다. \n"
    "2. 생성된 글에 대한 기사 제목도 만들어주시고, 'title' 속성에 담아주세요.\n"
    "3. 문단을 적절히 나누어야 합니다.\n"
    "4. 꼭 함께 넘겨주는 문서 내용을 이용해야 합니다.\n"
    "5. 답은 json 형식으로 만들어주시고, 새로운 기사 제목은 'title'에, 새로운 기사 내용은 'article' 속성에 넣어주시고 , 퀴즈는 'quiz'속성에 리스트로 넣어주세요. \n"
    "6. quiz 와 함께 correct_answer에 숫자로 정답을 넣어주세요. 첫번째 선지가 정답이면 0, 두번째 선지가 정답이면 1이입니다.\n"
    "7. 글을 생성할때 사용한 기사의 url들을 url 속성에 담아주세요. \n"
    "8. 넘겨준 자료들에 담긴 정보들을 최대한 많이 담아주세요. \n"
    "\n\n"
    "{context}"
  )


  # 레벨에 따라 system_prompt 앞에 추가
  if level == 1:
      system_prompt = level_1 + "\n" + system_prompt
  elif level == 2:
      system_prompt = level_2 + "\n" + system_prompt

  qa_prompt = ChatPromptTemplate.from_messages(
      [
          ("system", system_prompt), # llm의 역할
          few_shot_prompt, # 예제를 많이 넣으면 넣을수록 .. 
          MessagesPlaceholder("chat_history"),
          ("human", "{input}"),
      ]
  )
  
  question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

  #rag_chain = create_retrieval_chain(retriever, question_answer_chain) 

  conversational_rag_chain = RunnableWithMessageHistory(
        question_answer_chain,
        #rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
  )
  return conversational_rag_chain


def get_ai_response(user_message,level):
  
  llm = get_llm()

  retriever = get_retriever()
  
  #rag_chain = get_rag_chain(llm,retriever,level) 

  rag_chain = get_rag_chain_v2(llm,retriever,level)

  start_time = time.time()
  docs = retriever.invoke(user_message)
  end_time = time.time()
  print(f"retriever 소요 시간: {end_time - start_time:.4f}초")
  
  urls = []
  urls = [doc.metadata['url'] for doc in docs[:5]] # 검색된 문서들 중 상위 5개 문서 url 리스트에 삽입

  image = ''
  for doc in docs:
        if len(doc.metadata["image"]) > 0:
            image = doc.metadata["image"]
            break
  

  ai_response = rag_chain.invoke(
    {
      "input": user_message,
      "context" : docs
    },
    config={
          "configurable": {"session_id": "abc123"}
    }, 
    )
  
  return ai_response,urls,image


