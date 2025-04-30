from fastapi import APIRouter, Query
import llm
import json

router = APIRouter(
    prefix="/v1",
)

@router.get("/create")
def makePesonalArticle(
    topic: str = Query(..., description="주제"),
    sessionId: str = Query(..., description="세션 ID"),
    level: int = Query(..., description="글 난이도")
):
    print("/create 호출")
    result,urls,image = llm.get_ai_response(topic,level)

    start_index = result.find('{')
    end_index = result.rfind('}')

    json_string = result[start_index:end_index+1]
    
    json_data = {}

    try:
        # JSON 문자열 파싱
        json_data = json.loads(json_string,strict=False)
        
        # url, image를 llm에서 넘겨준 것이 아닌, 검색된 기사에서 직접 받아서 사용
        json_data['url'] = urls
        json_data['image_url'] = image
        
        #print("JSON이 정상적으로 파싱되었습니다:", json_data)
        
    except json.JSONDecodeError as e:
        print("JSONDecodeError 발생:", e)
        print("에러가 발생한 부분:", e.doc)
        
    except Exception as e:
        print("알 수 없는 에러 발생:", e)

    
    
    # JSON 응답으로 반환
    return json_data # FastAPI가 자동으로 JSON 변환


@router.get("/chat")
def makePesonalArticle(
    question: str = Query(..., description="주제"),
    sessionId: str = Query(..., description="세션 ID")
):
    answer= llm.get_chat_bot(question).text()

    # JSON 응답으로 반환
    return {"answer": answer}  # FastAPI가 자동으로 JSON 변환
