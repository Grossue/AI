from fastapi import APIRouter, Query
import llm
import json
import re
from fastapi.responses import JSONResponse
from typing import Any, Optional

router = APIRouter(
    prefix="/v1",
)

@router.get("/create")
def makePesonalArticle(
    topic: str = Query(..., description="주제"),
    sessionId: str = Query(..., description="세션 ID"),
    level: str = Query(..., description="글 난이도"),
    type: str =  Query(0, description="글 타입 : 기본값은 0, 대본일 경우 1")
):
    print("/create 호출")
    result,urls,image = llm.get_ai_response(topic,level,type)

    if result=="422":
        return make_json_response(data=None, message="입력한 주제에 대하여 글을 생성할 수 없습니다.",status = 422 )
    
    start_index = result.find('{')
    end_index = result.rfind('}')

    json_string = result[start_index:end_index+1]
    json_string = re.sub(r'(?<!\\)(?<!\n)\n(?!\n)(?=[^"\n]*?")', ' ', json_string)

    json_data = {}
    
    data = None

    try:
        # JSON 문자열 파싱
        json_data = json.loads(json_string,strict=False)
        
        # url, image를 llm에서 넘겨준 것이 아닌, 검색된 기사에서 직접 받아서 사용
        json_data['url'] = urls
        json_data['image_url'] = image
        data = json_data

        return make_json_response(data=data)

    except json.JSONDecodeError as e:
        print("JSONDecodeError 발생:", e)
        print("에러가 발생한 부분:", e.doc)
        return make_json_response(message="ai 서버 에러, 관리자에게 문의해주세요.",status = 500)
        
    except Exception as e:
        print("알 수 없는 에러 발생:", e)
        return make_json_response(message="ai 서버 에러, 관리자에게 문의해주세요.",status = 500)

@router.get("/test")
def makePesonalArticle(
    topic: str = Query(..., description="주제"),
    sessionId: str = Query(..., description="세션 ID"),
    level: str = Query(..., description="글 난이도"),
    type: str =  Query(0, description="글 타입 - 기본값은 0, 대본일 경우 1")
):
    print("/test 호출")
    data = {}

    if topic=="바보":
        return make_json_response(data=None, message="입력한 주제에 대하여 글을 생성할 수 없습니다.",status = 422)
    
    if type=="GENERAL" :
        with open('general_result.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

    if type=="SCRIPT" :
        with open('script_result.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

    return make_json_response(data= data)

@router.get("/chat")
def makePesonalArticle(
    question: str = Query(..., description="주제"),
    sessionId: str = Query(..., description="세션 ID")
):
    answer= llm.get_chat_bot(question).text()

    # JSON 응답으로 반환
    return {"answer": answer}  # FastAPI가 자동으로 JSON 변환


def make_json_response(
    data: Optional[Any] = None,
    message: str = "",
    status: int = 200
) -> JSONResponse:
    return JSONResponse(
        content={
            "data": data,
            "message": message
        },
        status_code=status
    )