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

    try:
        result = article_service.get_article(topic,level,type,sessionId)
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
def makePesonalArticle(
    question: str = Query(..., description="주제"),
    sessionId: str = Query(..., description="세션 ID")
):
    try:
        if question.strip().startswith("3번") :
            answer = "3번 문제를 천천히 풀어볼게요! 😊\n\n---\n\n 3번 문제  \n가상화폐 가격 상승 이유 중 하나는 무엇인가요?\n\n선택지:  \n1. 미국의 금리 인상  \n2. 미국의 금리 인하 기대  \n3. 비트코인 생산 줄어듦\n\n---\n\n🧐 글 속에서 선생님이 이렇게 말했어요:\n\n> “미국의 연방준비제도가 금리를 낮출 것이라는 기대가 커졌기 때문이에요.”\n\n그리고 또,\n\n> “금리가 낮아지면 사람들이 더 쉽게 돈을 빌릴 수 있어서 투자나 소비가 늘고,  \n> 그 돈이 가상화폐로도 많이 몰려요.”\n\n---\n\n💡 여기서 중요한 단어는 \"금리 인하 기대\"예요.\n\n- 금리 인하: 돈 빌릴 때 이자가 줄어드는 것  \n- 사람들은 돈을 쉽게 빌려서 투자도 더 많이 하게 되고  \n- 그래서 가상화폐 가격이 오르기도 해요!\n\n---\n\n🎯 정답은 바로  \n👉 2번. 미국의 금리 인하 기대예요!\n\n---\n\n📌 다른 보기들은 어떻게 될까요?\n\n- 1번. 금리 인상은 반대 상황이에요.  \n  금리를 올리면 돈 빌리기가 어려워지고 가상화폐 투자도 줄 수 있어요.\n\n- 3번. 비트코인 생산 줄어듦은 이번 기사에서는 언급되지 않았어요.  \n  이런 일이 가격에 영향을 줄 수는 있지만, 이번에는 금리 이야기가 중심이었어요.\n\n---\n\n아주 잘 따라왔어요~ 숫자와 경제 이야기가 좀 어려울 수 있지만,  \n이렇게 하나씩 배우면 금방 이해할 수 있어요. 궁금한 거 또 물어봐요!"
        elif question.strip().startswith("가상화폐") :
            answer = "좋은 질문이에요! 😊 이건 아주 많은 어른들도 궁금해하는 거예요~  \n우리 쉬운 예시로 천천히 설명해볼게요!\n\n---\n\n이번 글에서 배운 것처럼, 가상화폐는 인터넷에만 있는 디지털 돈이에요.  \n그런데 \"인터넷에 있는 숫자\"가 어떻게 돈처럼 가치가 생기고,  \n왜 사람들이 사고팔까요? 🤔\n\n---\n\n🔍 비유로 설명해볼게요!\n\n한번 이런 놀이를 생각해 보세요~  \n친구들끼리 게임 아이템을 서로 주고받을 수 있어요.  \n어떤 아이템은 구하기 어려워서 가치가 높고,  \n그래서 어떤 친구는 진짜 돈을 주고서라도 사려고 해요.  \n\n> 이럴 땐, 그 아이템 자체가 돈처럼 쓰이는 것 같죠?\n\n---\n\n가상화폐도 비슷해요!  \n- 만들어내기 어렵고(계산을 엄청 많이 해야 해요!),  \n- 숫자가 한정되어 있어서 희귀하고,  \n- 컴퓨터 기술로 복제나 위조가 안 되게 안전하게 만들어졌어요!\n\n그래서 사람들은 말해요:  \n“이건 믿을 수 있고, 전 세계 누구랑도 바로 주고받을 수 있으니까,  \n돈처럼 써도 되겠다!”\n\n---\n\n📈 사람들이 믿고 사용하고, 또 사려고 하니까  \n가치가 생기고,  \n수요가 많을수록 가격이 올라가는 구조예요!\n\n그래서 어떤 사람은 미리 샀다가  \n가격이 오르면 되팔아서 돈을 벌기도 해요. 마치 주식처럼요!\n\n---\n\n📌정리하자면,\n\n가상화폐는  \n- 컴퓨터 속에서 만들어진 희귀한 디지털 자산이고,  \n- 사람들이 서로 쓰고 싶어 하기 때문에  \n- 돈처럼 가격이 생기고, 사거나 팔 때 진짜 돈으로 바꿀 수 있는 거예요.\n\n---\n\n조금 어려울 수도 있지만, 마치 게임 속 희귀템이  \n진짜 돈처럼 가치가 생기는 걸 떠올리면 이해하기 쉬워요~ 😊  \n그래도 언제나 조심해서 사용해야 해요.  \n\n더 궁금한 게 있으면 또 물어봐 주세요!"
        else : 
            answer= article_service.get_chat_bot(question,sessionId).text()
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
        answer = "1. **잘한 점**  \n‘가상화폐가 너무 많이 오르면 사회적 문제로 이어질 수 있다’는 점을 잘 짚어줬어요. 단순히 개인의 선택이 아니라 사회 전체에도 영향을 줄 수 있다는 넓은 시각이 아주 좋아요. 공감도 가고, 중요한 문제를 잘 짚었어요!\n\n2. **아쉬운 점 / 개선할 점**  \n내용의 핵심은 잘 전달했지만, 문장 표현이 조금 매끄럽지 않아서 이해에 살짝 걸리는 부분이 있어요. 예를 들어 \"사람들이 사람들이 너무 많이 사다가\"처럼 중복된 표현이 있거나 설명이 조금 막연하게 느껴질 수 있어요. 어떤 식으로 사회적 문제가 발생할 수 있는지 구체적인 예시가 조금만 더 들어가면 내용도 훨씬 설득력 있게 전개될 것 같아요.\n\n3. **제안**  \n'돈을 잃는 사람이 많아지는 것이 어떻게 사회 문제로 이어질 수 있는지' 예를 들어 청년들이 무리하게 투자해서 빚을 지거나, 가상화폐 하락으로 가정 경제가 어려워지는 등의 사례를 덧붙이면 더욱 공감 가는 답변이 될 수 있어요. 또, 이런 문제를 막기 위한 태도나 해결책도 함께 제시하면 좋아요.\n\n4. **총평**  \n사람들의 충동적인 투자로 인해 발생할 수 있는 사회적 문제에 주목한 점이 아주 뛰어나요. 다만, 문장을 조금 정돈하고 내용을 구체적으로 보완하면 더 설득력 있는 의견이 될 수 있어요. 생각이 깊고 시야도 넓네요. 잘했어요!\n\n5. **보완 문장 예시**  \n가상화폐가 너무 많이 오르면 사람들이 더 오를 거라고 기대하고 무리하게 투자하는 경우가 많아져요. 이로 인해 큰 돈을 잃는 사람이 늘어나면 개인의 문제를 넘어서 빚, 우울증, 가정 불화 같은 사회적 문제로 이어질 수 있어요. 그래서 우리는 반드시 조심스럽게 투자하고, 가상화폐에 대해 충분히 공부하는 태도가 필요하다고 생각해요."
        return make_json_response(data= answer)

    try:
        answer= article_service.get_s_quiz_feedback_chain(answer,sessionId).text()
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