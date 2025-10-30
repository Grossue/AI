from fastapi import APIRouter, Query
import article_service
import json
import re
from make_response import make_json_response
import time
from models import UserHistoryRequest
from recomendation import get_recommendation, get_recommendations
from typing import List
from error_handler import UnprocessableEntityException
router = APIRouter(
    prefix="/v1",
)

@router.get("/create")
async def makePesonalArticle(
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

    try:
        result = await article_service.get_article(topic,level,type,sessionId)
        return make_json_response(data=result)

    except json.JSONDecodeError:
        print("상위에서 JSONDecodeError 잡음!")
        return make_json_response(message="JSONDecodeError",status = 500)

    except UnprocessableEntityException as e:
        return make_json_response(message=str(e.detail), status=422)

    except ValueError as e:
        print("상위에서 커스텀 예외 잡음:", e)
        return make_json_response(message="ValueError",status = 500)

    

@router.get("/chat")
async def makePesonalArticle(
    question: str = Query(..., description="주제"),
    sessionId: str = Query(..., description="세션 ID")
):
    try:
        answer = (await article_service.get_chat_bot(question,sessionId)).text()
    except KeyError as e:
        return make_json_response(message=e.args[0],status = 404)
    return make_json_response(data= answer)


@router.get("/thinking-question-feedback")
async def makePesonalArticle(
    answer: str = Query(..., description="주관식 답변"),
    sessionId: str = Query(..., description="세션 ID"),
    forTest: bool = Query(False, description="테스트일 경우 true")
):
    print("/thinking-question-feedback 호출")
    # test 용 일 경우
    if(forTest==True):
        answer = "1. **잘한 점**  \n’가상화폐가 너무 많이 오르면 사회적 문제로 이어질 수 있다’는 점을 잘 짚어줬어요. 단순히 개인의 선택이 아니라 사회 전체에도 영향을 줄 수 있다는 넓은 시각이 아주 좋아요. 공감도 가고, 중요한 문제를 잘 짚었어요!\n\n2. **아쉬운 점 / 개선할 점**  \n내용의 핵심은 잘 전달했지만, 문장 표현이 조금 매끄럽지 않아서 이해에 살짝 걸리는 부분이 있어요. 예를 들어 \"사람들이 사람들이 너무 많이 사다가\"처럼 중복된 표현이 있거나 설명이 조금 막연하게 느껴질 수 있어요. 어떤 식으로 사회적 문제가 발생할 수 있는지 구체적인 예시가 조금만 더 들어가면 내용도 훨씬 설득력 있게 전개될 것 같아요.\n\n3. **제안**  \n’돈을 잃는 사람이 많아지는 것이 어떻게 사회 문제로 이어질 수 있는지’ 예를 들어 청년들이 무리하게 투자해서 빚을 지거나, 가상화폐 하락으로 가정 경제가 어려워지는 등의 사례를 덧붙이면 더욱 공감 가는 답변이 될 수 있어요. 또, 이런 문제를 막기 위한 태도나 해결책도 함께 제시하면 좋아요.\n\n4. **총평**  \n사람들의 충동적인 투자로 인해 발생할 수 있는 사회적 문제에 주목한 점이 아주 뛰어나요. 다만, 문장을 조금 정돈하고 내용을 구체적으로 보완하면 더 설득력 있는 의견이 될 수 있어요. 생각이 깊고 시야도 넓네요. 잘했어요!\n\n5. **보완 문장 예시**  \n가상화폐가 너무 많이 오르면 사람들이 더 오를 거라고 기대하고 무리하게 투자하는 경우가 많아져요. 이로 인해 큰 돈을 잃는 사람이 늘어나면 개인의 문제를 넘어서 빚, 우울증, 가정 불화 같은 사회적 문제로 이어질 수 있어요. 그래서 우리는 반드시 조심스럽게 투자하고, 가상화폐에 대해 충분히 공부하는 태도가 필요하다고 생각해요."
        return make_json_response(data= answer)

    try:
        answer = (await article_service.get_s_quiz_feedback_chain(answer,sessionId)).text()
    except KeyError as e:
        return make_json_response(message=e.args[0],status = 404)
    return make_json_response(data= answer)

@router.get("/recommend")
def getRecommendation(
    content: str = Query(..., description="생성된 기사 전문")
):
    try:
        result = get_recommendation(content)
        return make_json_response(data=result)
    except Exception as e:
        return make_json_response(message=str(e), status=500)

@router.post("/recommend", response_model=List[str])
def recommend(request: UserHistoryRequest):
    return get_recommendations(request.history)