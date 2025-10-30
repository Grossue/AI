from dotenv import load_dotenv
from prompt.few_shot import *
import re
from prompt.feedback_prompt import feedback_system_prompt
from prompt.qna_prompt import qna_system_prompt
from session_utils import *
from rag_chains import *
from prompt_utils import *
from llm_utils import *
from retriever import *
import json
from error_handler import UnprocessableEntityException

async def get_chat_bot(user_message,sessionId):
    exist_session(sessionId)

    llm = get_llm()

    rag_chain = build_default_rag_chain(llm, qna_examples, qna_system_prompt)

    ai_response = await rag_chain.ainvoke(
        {
        "input": user_message
        },
        config={
            "configurable": {"session_id": sessionId }
        },
    )
    return ai_response["answer"]

async def get_s_quiz_feedback_chain(user_message,sessionId):
    exist_session(sessionId)

    llm = get_llm()

    rag_chain = build_default_rag_chain(llm, subjective_quiz_feedback_examples, feedback_system_prompt)

    ai_response = await rag_chain.ainvoke(
        {
        "input": user_message
        },
        config={
            "configurable": {"session_id": sessionId }
        },
        )

    return ai_response["answer"]


async def get_article(user_message, level, type, sessionId):
    llm = get_json_llm()
    rag_chain = build_create_article_rag_chain(llm, level, type)

    docs = await retrieve_docs(user_message)
    urls = extract_urls(docs)
    images = extract_images(docs)
    docs = preprocess_docs(docs)

    ai_response = await rag_chain.ainvoke(
        {"input": user_message, "context": docs},
        config={"configurable": {"session_id": sessionId}},
    )
    print(ai_response)
    
    result = ai_response["answer"]

    if result=="422":
        print("422 에러 발생 - 응답할 수 없는 질문:", e) 
        raise UnprocessableEntityException("입력값에 대한 글을 생성할 수 없습니다.")
    
    start_index = result.find('{')
    end_index = result.rfind('}')

    json_string = result[start_index:end_index+1]
    json_string = re.sub(r'(?<!\\)(?<!\n)\n(?!\n)(?=[^"\n]*?")', ' ', json_string)

    json_data = {}
            
    try:
        json_data = json.loads(json_string,strict=False)
        json_data['image'] = {}
        json_data['image']['image_url'] = next((img["image"] for img in images if img.get("origin_link") in json_data["url"]), None)
        json_data['image']['image_desc'] = next((img["image_desc"] for img in images if img.get("origin_link") in json_data["url"]), None)
        json_data['image']['image_source'] = next((img["origin_link"] for img in images if img.get("origin_link") in json_data["url"]), None)
        json_data['url'] = [item for item in urls if item["url"] in json_data["url"]]
        
    except json.JSONDecodeError as e:
        print("JSONDecodeError 발생:", e) # e.doc
        raise

    return json_data

def extract_urls(docs):
    return [
        {"title": doc.metadata["title"], "url": doc.metadata["origin_link"]}
        for doc in docs
    ]


def extract_images(docs):
    images = []
    for doc in docs:
        if len(doc.metadata.get("image", "")) > 0:
            images.append({
                "image": doc.metadata["image"],
                "image_desc": doc.metadata["image_desc"],
                "origin_link": doc.metadata["origin_link"],
            })
    return images


def preprocess_docs(docs):
    for doc in docs:
        date = doc.metadata.get("date_time", "")
        url = doc.metadata.get("origin_link", "") or doc.metadata.get("url", "")
        content = doc.page_content
        sentences = re.split(r'(?<=[.!?])\s+', content.strip())
        tagged_sentences = [
            f"[기사 날짜 : {date}, 기사 출처 : {url}] {s}"
            for s in sentences if s
        ]
        doc.page_content = " ".join(tagged_sentences)
    return docs