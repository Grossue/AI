from dotenv import load_dotenv
from config import *
import time
import re

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
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import RetrievalQA, LLMChain, create_history_aware_retriever, create_retrieval_chain

# LangChain Community 모듈
from langchain_community.chat_message_histories import ChatMessageHistory
from prompts import level_1, level_2, system_prompt_general, system_prompt_scripts

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
  
  database = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embedding, text_key="content")
  
  retriever = database.as_retriever(search_kwargs={'k': 2})

  return retriever


def get_rag_chain(llm,level,type):

  example_prompt = ChatPromptTemplate.from_messages(
      [
          ("human", "{input}"),
          ("ai", "{answer}"),
      ]
  )

  # FewShotChatMessagePromptTemplate : 질문/답변 예시들을 포함하는 few-shot 학습 형식 프롬프트
  few_shot_prompt = FewShotChatMessagePromptTemplate(
      example_prompt=example_prompt,
      examples = create_article_examples if type == "GENERAL" else create_article_script_examples
  )

  system_prompt = system_prompt_general if type== "GENERAL" else system_prompt_scripts



  # 레벨에 따라 system_prompt 앞에 추가
  if level == "LEVEL1":
      system_prompt = level_1 + "\n" + system_prompt
  elif level == "LEVEL2":
      system_prompt = level_2 + "\n" + system_prompt

  # 시스템 메시지 + 예시 + 히스토리 + 사용자 질문 으로 구성.
  # MessagesPlaceholder("chat_history") 는 대화 히스토리 유지용.

  qa_prompt = ChatPromptTemplate.from_messages(
      [
          ("system", system_prompt),  # 역할 정의 및 제약 조건
          few_shot_prompt, 
          MessagesPlaceholder("chat_history"), # 예시 삽입
          ("human", 
          # "현재 날짜 : 2025/5/5 "
          #"{input}'을 사용자가 입력했어. 사용자가 입력한 주제에 대해서 넘겨준 문서를 활용하여 새로운 글을 만들어줘."
          "{input}'을 사용자가 입력했고, 이를 통해 문서를 검색했어. "
          "넘겨준 문서에 대한 기사의 정보를 활용하여 새로운 글을 만들어주되, "
          "기사에 담긴 정보를 최대한 많이 알려주는게 목표야. "
          "사용자가 입력한 주제에 대해서만 설명하지 말고, 기사에 담긴 정보를 최대한 많이 활용해서 글을 만들어줘. "
          "만약, {input}이 '바보' , '병신' , '너 이름이 뭐야?', '내 생일','몰라', 와 같이 글을 생성할 수 없는 주제라면, "
          "'422'를 반환해주세요. "
          ),

      ]
  )
  
  # 검색된 문서들을 "그대로" LLM에게 넘겨주는 체인.
  question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

  #rag_chain = create_retrieval_chain(retriever, question_answer_chain) 
  llm_chain = (
        question_answer_chain
        | (lambda text: {"answer": text})
  )

  # RunnableWithMessageHistory : 세션별로 대화 기록을 유지해줌.
  conversational_rag_chain = RunnableWithMessageHistory(
        #question_answer_chain,
        #rag_chain,
        llm_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
  )
  return conversational_rag_chain


def get_ai_response(user_message,level,type,sessionId):
  
  llm = get_llm()

  retriever = get_retriever()
  
  #rag_chain = get_rag_chain(llm,retriever,level)

  rag_chain = get_rag_chain(llm,level,type)

  start_time = time.time()
  docs = retriever.invoke(user_message)
  end_time = time.time()
  print(f"retriever 소요 시간: {end_time - start_time:.4f}초")
  
  urls = []
  urls = [{"title" : doc.metadata['title'] , "url" : doc.metadata['url']} for doc in docs]

  image = ''
  for doc in docs:
        if len(doc.metadata["image"]) > 0:
            image = doc.metadata["image"]
            break
          
  for doc in docs:
    date = doc.metadata.get("date_time", "")
    url = doc.metadata.get("url","")
    content = doc.page_content 

    # 문장 단위로 분리 (정규식 사용, 기본적인 마침표 기준)
    sentences = re.split(r'(?<=[.!?])\s+', content.strip())
    
    # 각 문장 앞에 날짜 태그 추가
    tagged_sentences = [f"[기사 날짜 : {date}, 기사 출처 : {url}] {sentence}" for sentence in sentences if sentence]

    # 다시 하나로 합치기
    updated_content = ' '.join(tagged_sentences)

    # 수정된 content 반영
    doc.page_content = updated_content

  ai_response = rag_chain.invoke(
    {
      "input": user_message,
      "context" : docs
    },
    config={
          "configurable": { "session_id": sessionId }
    }, 
    )
  
  return ai_response["answer"],urls,image

def exist_session(sessionId):
  if sessionId not in store:
    raise KeyError(f"'{sessionId}'라는 키는 존재하지 않습니다.")

def get_chat_bot(user_message,sessionId):
  exist_session(sessionId)
  
  llm = get_llm()

  rag_chain = get_qna_rag_chain(llm) 

  ai_response = rag_chain.invoke( 
    {
      "input": user_message
    },
    config={
          "configurable": {"session_id": sessionId }
    }, 
    )

  return ai_response["answer"]

def get_qna_rag_chain(llm):
  example_prompt = ChatPromptTemplate.from_messages(
      [
          ("human", "{input}"),
          
          ("ai", "{answer}"),
      ]
  )
  few_shot_prompt = FewShotChatMessagePromptTemplate(
      example_prompt=example_prompt,
      examples= qna_examples,
  )

  system_prompt = (
      "당신은 방금전에 글과 퀴즈를 생성했습니다. "
      "이후 사용자가 해당 글과 퀴즈에 대해 궁금한 점을 물어보거나 당신의 생각을 물어볼 예정입니다."
      "질문에 답변해 주세요. "
      "필요할 경우에만 찾은 문서를 활용하도록 합니다. "
      "만약 당신이 생성한 글이 아닌 찾은 문서 내용을 바탕으로 답변을 해야한다면, '다른 기사 내용을 따르면,' 이라는 문구를 붙여 답변해 주세요. "
      "\n\n"
      #"{context}"
  )
  
  qa_prompt = ChatPromptTemplate.from_messages(
      [
          ("system", system_prompt),  
          few_shot_prompt,
          MessagesPlaceholder("chat_history"), 
          ("human", "{input}"), 
      ]
  )

  #llm_chain = RunnableSequence(qa_prompt, llm)
  llm_chain = (
        qa_prompt
        | llm
        | (lambda text: {"answer": text})
  )

  conversational_rag_chain = RunnableWithMessageHistory(
      llm_chain,
      get_session_history,  
      input_messages_key="input",  
      history_messages_key="chat_history",  
      output_messages_key="answer", 
  )

  return conversational_rag_chain

def get_store():
  print(store)
  return store

def delete_history(sessionId):
  if sessionId in store:
    del store[sessionId]
  else:
    raise KeyError(f"'{sessionId}'라는 키는 존재하지 않습니다.")