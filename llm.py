from dotenv import load_dotenv
from config import *

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
  
  retriever = database.as_retriever(search_kwargs={'k': 4})
  
  return retriever

def get_rag_chain(llm,retriever):

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

  system_prompt = (
    "당신은 어린이들을 위해 뉴스 기사를 작성하는 기자입니다. "
    "제공되는 주제와 관련된 기존 기사를 조합하여 1000자 이상의 새로운 기사와 이에 대한 3지선다 퀴즈 3문제를 만들어주세요. "
    "생성된 글에 대한 기사 제목도 만들어주시고, 'title' 속성에 담아주세요."
    "가장 중요한 부분은 문단을 적절히 나누는 것 입니다. "
    "꼭 함께 넘겨주는 문서 내용을 이용해야 합니다."
    "답은 json 형식으로 만들어주시고, 새로운 기사 제목은 'title'에, 새로운 기사 내용은 'article' 속성에 넣어주시고 , 퀴즈는 'quiz'속성에 리스트로 넣어주세요. "
    "quiz 와 함께 correct_answer에 숫자로 정답을 넣어줘. 첫번째 선지가 정답이면 0, 두번째 선지가 정답이면 1이야."
    "함께 전달해준 문서인 context에 저장된 url들을 url 속성에 담아주세요. "
    "\n\n"
    "{context}"
  )

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


def get_ai_response(user_message):
  
  llm = get_llm()

  retriever = get_retriever()
  
  rag_chain = get_rag_chain(llm,retriever) 
  
  ai_response = rag_chain.invoke(
    {
      "input": user_message
    },
    config={
          "configurable": {"session_id": "abc123"}
    }, 
    )

  return ai_response

def get_chat_bot(user_message):
  
  llm = get_llm()

  rag_chain = get_qna_rag_chain(llm) 

  ai_response = rag_chain.invoke( 
    {
      "input": user_message
    },
    config={
          "configurable": {"session_id": "abc123"}
    }, 
    )

  return ai_response

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

  llm_chain = RunnableSequence(qa_prompt, llm)

  conversational_rag_chain = RunnableWithMessageHistory(
      llm_chain,
      get_session_history,  
      input_messages_key="input",  
      history_messages_key="chat_history",  
      output_messages_key="answer", 
  )

  return conversational_rag_chain