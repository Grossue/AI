from fastapi import APIRouter, Query
import llm
import json
import re
from make_response import make_json_response


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
    result,urls,image = llm.get_ai_response(topic,level,type,sessionId)

    if result=="422":
        return make_json_response(data=None, message="입력한 주제에 대하여 글을 생성할 수 없습니다.",status = 422)
    
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
        print("JSONDecodeError 발생:", e) # e.doc
        return make_json_response(message="JSONDecodeError",status = 500)
    


@router.get("/chat")
def makePesonalArticle(
    question: str = Query(..., description="주제"),
    sessionId: str = Query(..., description="세션 ID")
):
    try:
        answer= llm.get_chat_bot(question,sessionId).text()
    except KeyError as e:
        return make_json_response(message=e.args[0],status = 404)
    return make_json_response(data= answer)

@router.get("/history")
def getStore(
):
    return llm.get_store()

@router.delete("/history")
def deleteHistory(
    sessionId: str = Query(..., description="세션 ID")
):
    try:
        llm.delete_history(sessionId)
    
    except KeyError as e:
        return make_json_response(message=e.args[0],status = 404)
    
    return make_json_response(message="성공적으로 세션을 삭제했습니다.")


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


@router.get("/recommend")
def getRecommendation(
    content: str = Query(..., description="생성된 기사 전문")
):
    try:
        result = llm.get_recommendation(content)
        return make_json_response(data=result)
    except Exception as e:
        return make_json_response(message=str(e), status=500)