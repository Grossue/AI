from dotenv import load_dotenv
from config import *
import time
import re
import json
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


#from langchain_community.chat_message_histories import RedisChatMessageHistory
from redis_chat_message_history_custom import RedisChatMessageHistory
import redis
from redis_client import redis_client

store = {}

def get_llm(model="chatgpt-4o-latest"): # gpt-5-mini gpt-4o gpt-4.1-mini chatgpt-4o-latest
  llm = ChatOpenAI(model=model)
  return llm


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    # Redis 기반 메시지 히스토리 객체를 반환
    # Redis 연결 설정 -> 커스텀하여 사용
    return RedisChatMessageHistory(session_id=session_id, redis_client=redis_client,ttl=86400)

# def get_session_history(session_id: str) -> BaseChatMessageHistory:
#     if session_id not in store:
#         store[session_id] = ChatMessageHistory()
#     return store[session_id]


def get_retriever():
  embedding = OpenAIEmbeddings(model='text-embedding-3-large')

  index_name = 'tax-index'
  
  database = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embedding, text_key="content")
  
  retriever = database.as_retriever(search_kwargs={'k': 4})

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
      example_prompt = example_prompt,
      examples = create_article_examples_LEVEL1 if (type == "GENERAL" and level == "LEVEL1") else (create_article_examples_LEVEL2 if type == "GENERAL" else create_article_script_examples)
      #create_article_examples if type == "GENERAL" else create_article_script_examples
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
          few_shot_prompt	, 
          MessagesPlaceholder("chat_history"), # 예시 삽입
          ("human", 
          "{input}'을 사용자가 입력했고, 이를 통해 문서를 검색했어. "
          "넘겨준 문서에 대한 기사의 정보를 활용하여 새로운 글을 만들어주되, "
          "기사에 담긴 정보를 최대한 많이 알려주는게 목표야. "
          "사용자가 입력한 주제에 대해서만 설명하지 말고, 기사에 담긴 정보를 최대한 많이 활용해서 글을 만들어줘. "
          "만약, {input}이 '바보' , '병신' , '너 이름이 뭐야?', '내 생일','몰라', 와 같이 글을 생성할 수 없는 주제라면, "
          "'422'를 반환해주세요. "

          """
          - 모든 응답은 반드시 JSON 형식으로 작성하세요.
          - JSON 속성 이름과 문자열 값은 반드시 큰따옴표(")로 감싸야 합니다.
          - 작은따옴표(')를 사용하지 마세요.
          - 응답에 불필요한 설명이나 문장은 포함하지 말고, 오직 JSON 데이터만 반환하세요.
          - JSON이 문법 오류 없이 파싱 가능하도록 정확하게 포맷팅해 주세요.
          - 응답의 각 키와 값은 명확하고 일관되게 작성해 주세요.
          """
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
  llm = llm.bind(response_format={"type": "json_object"})

  retriever = get_retriever()
  
  #rag_chain = get_rag_chain(llm,retriever,level)

  rag_chain = get_rag_chain(llm,level,type)

  start_time = time.time()
  docs = retriever.invoke(user_message)
  end_time = time.time()
  print(f"retriever 소요 시간: {end_time - start_time:.4f}초")
  
  urls = []
  urls = [{"title" : doc.metadata['title'] , "url" : doc.metadata['origin_link']} for doc in docs]

  images = []
  for doc in docs:
        if len(doc.metadata["image"]) > 0:
            images.append({
              "image" : doc.metadata["image"],
              "image_desc" : doc.metadata["image_desc"],
              "origin_link" : doc.metadata["origin_link"]
            })
            
          
  for doc in docs:
    date = doc.metadata.get("date_time", "")
    #url = doc.metadata.get("url","")
    #url = doc.metadata.get("origin_link","")
    url = doc.metadata.get("origin_link", "") or doc.metadata.get("url", "")
    content = doc.page_content 
    image_desc = doc.metadata.get("image_desc", "")
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
  print(ai_response)

  return ai_response["answer"],urls,images

# def exist_session(sessionId):
#   if sessionId not in store:
#     raise KeyError(f"'{sessionId}'라는 키는 존재하지 않습니다.")

def exist_session(session_id: str):
    key = f"message_store:{session_id}"  # 실제 Redis에 저장된 키 형식과 맞춰야 합니다
    if not redis_client.exists(key):
        raise KeyError(f"'{session_id}'라는 키는 존재하지 않습니다.")

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

def get_s_quiz_feedback_chain(user_message,sessionId):
  exist_session(sessionId)
  
  llm = get_llm()

  rag_chain = get_subjective_feedback(llm) 

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

      """
      당신은 초등학생이 이해하기 쉽게 친절하고 부드러운 \"~요\" 체로 답변하는 역할을 합니다.  
      사용자가 질문을 하면 상황에 따라 아래 기준에 맞춰 답해주세요.
      특히, 대부분의 질문은 사용자가 전에 생성된 글과 퀴즈를 보고 하는 것이니,  

      답변할 때는 그 내용을 바탕으로 설명하거나 연결 지어주는 것이 좋아요.  
      ※ 만약 질문이 글과 직접적인 관련이 없어 보이더라도,  
      가능하다면 글의 내용을 연결해서 추가 설명이나 배경지식을 함께 알려주세요.

      다음 기준에 따라 상황에 맞게 답변해 주세요:

      1. 질문에 명확히 답할 수 있을 때  
      → 글과 연결된 맥락을 먼저 짚어주고, 그 후 질문에 답하세요.  
      예시나 비유도 함께 제시해 주세요.  
      > 예) "방금 글에서 ~라는 이야기가 있었죠? 거기서 나온 단어예요. 예를 들어, ~처럼 생각하면 쉬워요."

      2. 질문에 대해 현재 글만으로는 정확한 답을 알 수 없을 때  
      → 솔직하게 그렇게 말해주되, 아이가 스스로 생각해볼 수 있도록 도와주세요.  
      > 예) "이건 지금 글만으로는 확실히 알기 어려워요. 그래도 학생은 어떻게 생각하나요?"

      3. 아이가 오해했거나 잘못 이해한 질문일 경우  
      → 정답을 알려주되, 부드럽게 다르게 설명해 주세요.  
      > 예) "조금 다르게 이해할 수도 있어요. 다시 쉽게 설명해 줄게요~"

      4. 질문이 너무 어렵거나 추상적일 때  
      → 걱정하지 말라고 격려하고, 쉽게 예시나 비유로 설명해 주세요.  
      > 예) "이건 조금 어려운 질문이지만, 퍼즐을 하나하나 맞추듯이 배우면 돼요!"

      5. 필요한 경우에는, 스스로 생각해볼 수 있도록 질문으로 유도하고 격려하기  
      → 여러 관점이 있을 수 있다는 점을 말해주고, 아이의 생각을 들어보세요.  
      > 예) "이건 정해진 답이 없을 수도 있어요. 학생이라면 어떻게 할 것 같나요?"

      6. 비유나 예시를 꼭 활용해서 쉽게 풀어 설명하기  
      → 친근한 경험(자전거, 친구, 놀이터 등)을 비유로 사용해 주세요.  
      > 예) "이건 친구랑 놀이 규칙 정하는 거랑 비슷해요~"

      또한, **질문이 글 내용과 직접 연결되지 않더라도**, 가능하다면 글에서 다뤘던 개념이나 내용을 바탕으로 자연스럽게 연관 지어 설명해 주세요.  
      > 예) "이번 글에서도 비슷한 개념이 나왔는데요~", "글에서 다뤘던 ~과도 관련이 있어요."

      항상 친절하고 따뜻한 말투로, 아이가 더 깊이 배우고 생각할 수 있도록 도와주세요.

      질문에 답할 때는 꼭 학생이 이해하기 쉽도록 천천히, 친절하게, 그리고 생각할 거리를 주는 답변을 해 주세요.
      """
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

# 주관식 채점
def get_subjective_feedback(llm):
  example_prompt = ChatPromptTemplate.from_messages(
      [
          ("human", "{input}"),
          
          ("ai", "{answer}"),
      ]
  )
  few_shot_prompt = FewShotChatMessagePromptTemplate(
      example_prompt=example_prompt,
      examples= subjective_quiz_feedback_examples,
  )

  system_prompt = (
    "당신은 사용자가 이전에 작성한 thinking_question에 대한 답변에 피드백을 제공해야 해. "
    "피드백은 다음 요소들을 포함해야 해:\n"
    "1. 잘한 점 - 의견에서 긍정적인 부분과 공감하는 내용을 짧고 명확하게 말해줘. (문장 구성, 설득력, 내용 등) \n"
    "2. 아쉬운 점 / 개선할 점 - 부족한 부분이나 보완할 점을 구체적으로 지적해줘. (문장 구성, 설득력, 내용 등)"
    "만약 설득력이나 내용이 부족하다면 왜 그렇게 생각하는지 이유를 좀 더 설명하면 좋겠다고 말해줘.\n"
    "3. 제안 - 의견에 추가하면 좋을 내용이나 다른 관점, 보완책을 제안해줘.\n"
    "4. 총평 - 전체적인 종합적으로 정리해서 총평을 만들어주면돼. \n"
    "5. 보완 문장 예시 - 위 내용을 반영해서 더 완성도 높은 문장 예시를 짧게 작성해줘.\n\n"
    "주의사항:\n"
    "- 답변은 학생에게 친근한 말투인 ‘~요’ 체로 작성해줘.\n"
    "- 피드백은 질문으로 끝나지 않도록 하고, 명확히 피드백임을 알 수 있게 작성해줘.\n"
    "- 공감하는 부분과 개선할 점을 반드시 모두 포함해야 해.\n"
    "- 답변은 이해하기 쉽게 작성해줘."
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