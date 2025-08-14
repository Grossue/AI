from fastapi import APIRouter, Query
import llm
import json
import re
from make_response import make_json_response
import time

router = APIRouter(
    prefix="/v1",
)

# 주관식 -> 생각해보세요 문제. 단답형 문제(일반 내용 문제)
@router.get("/create")
def makePesonalArticle(
    topic: str = Query(..., description="주제"),
    sessionId: str = Query(..., description="세션 ID"),
    level: str = Query(..., description="글 난이도"),
    type: str =  Query("GENERAL", description="글 타입"),
    forTest: bool = Query(False, description="테스트일 경우 true")
):
    print("/create 호출")

    # 테스트를 위한 요청 이라면
    if forTest == True :
        time.sleep(20)
        if type=="GENERAL" and level == "LEVEL1" :
            with open('./test_data/general_l1_result.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

        elif type=="GENERAL" and level == "LEVEL2" :
            with open('./test_data/general_l2_result.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

        elif type=="SCRIPT" :
            with open('./test_data/script_result.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        return make_json_response(data=data)


    result,urls,images = llm.get_ai_response(topic,level,type,sessionId)

    if result=="422":
        return make_json_response(data=None, message="입력한 주제에 대하여 글을 생성할 수 없습니다.",status = 422)
    
    start_index = result.find('{')
    end_index = result.rfind('}')

    json_string = result[start_index:end_index+1]
    json_string = re.sub(r'(?<!\\)(?<!\n)\n(?!\n)(?=[^"\n]*?")', ' ', json_string)

    json_data = {}
    
    data = None
        
    try:
        # urls = [{"title" : doc.metadata['title'] , "url" : doc.metadata['origin_link']} for doc in docs]
        # JSON 문자열 파싱
        json_data = json.loads(json_string,strict=False)


        json_data['image'] = {}
        json_data['image']['image_url'] = next((img["image"] for img in images if img.get("origin_link") in json_data["url"]), None)
        json_data['image']['image_desc'] = next((img["image_desc"] for img in images if img.get("origin_link") in json_data["url"]), None)
        json_data['image']['image_source'] = next((img["origin_link"] for img in images if img.get("origin_link") in json_data["url"]), None)
        
        # url, image를 llm에서 넘겨준 것이 아닌, 검색된 기사에서 직접 받아서 사용
        json_data['url'] = [item for item in urls if item["url"] in json_data["url"]] #urls
        #json_data['image_url'] = image

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

@router.get("/thinking-question-feedback")
def makePesonalArticle(
    answer: str = Query(..., description="주관식 답변"),
    sessionId: str = Query(..., description="세션 ID"),
    forTest: bool = Query(False, description="테스트일 경우 true")
):
    print("/thinking-question-feedback 호출")
    # test 용 일 경우
    if(forTest==True):
        answer = "- 잘한 점  \n의견이 분명하게 드러났어요. 한 가지 해결책을 제시하며 문제를 간단히 접근하려는 시도가 좋았어요.\n\n- 아쉬운 점 / 개선할 점  \n당 해체라는 주장은 굉장히 강력한 조치이기 때문에, 왜 이런 생각을 했는지 구체적인 이유가 필요해요. 특히 당 해체가 어떤 긍정적인 결과를 가져올 수 있는지, 그리고 어떤 부정적인 문제를 초래할 수 있는지도 함께 고려하면 좋을 듯해요.\n\n- 제안  \n당 해체 외에도 문제를 해결할 수 있는 다른 방법이 무엇일지 생각해 보는 것도 좋을 것 같아요. 회원의 의식 개선이나 정책 수정 같은 다른 방법들도 함께 고려해 보면 더 균형 잡힌 의견을 낼 수 있을 거예요.\n\n- 총평  \n단순하면서도 직설적인 의견을 제시한 점이 긍정적이었어요. 앞으로는 왜 그런 의견을 가지게 되었는지 좀 더 설명해 주고, 다른 해결책도 함께 고려해 보면 좋을 것 같아요. 포기하지 말고 다양한 관점에서 생각을 확장해 보세요!\n\n- 보완 문장 예시  \n당을 해체하는 것도 한 가지 방법일 수 있지만, 그로 인해 생길 수 있는 혼란과 사회적 비용도 고려해야 해요. 해체하는 대신 정책 개선이나 내부 멤버 교육 등 다른 방법으로 문제를 해결할 수 있는지도 같이 생각해 보는 게 좋을 것 같아요."
        return make_json_response(data= answer)

    try:
        answer= llm.get_s_quiz_feedback_chain(answer,sessionId).text()
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


