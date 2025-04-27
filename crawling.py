from langchain_openai import OpenAIEmbeddings
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import requests
from bs4 import BeautifulSoup
import requests 
from pinecone import Pinecone

import requests
from bs4 import BeautifulSoup

def get_embedding(content):
    embedding = OpenAIEmbeddings(model='text-embedding-3-large')
    return embedding.embed_documents([content])[0]


index_name = 'tax-index'
pc = Pinecone(api_key="")

index = pc.Index(index_name)


# ChromeDriver 경로 설정
chrome_driver_path = "D:\chrome-driver\chromedriver-win64\chromedriver.exe"

# Selenium WebDriver 설정
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # 화면 없이 실행하려면 주석 해제
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=options)

# 네이버 뉴스 경제 섹션 URL
url = "https://news.naver.com/section/101"

# 정치 : "https://news.naver.com/section/100"
# 경제 : "https://news.naver.com/section/101" # -> 금융, 증권, 산업/재계, 중기 벤처. .이렇게로도 가능
# 사회 : "https://news.naver.com/section/102"
# 생활/문화 : "https://news.naver.com/section/103"
# IT/과학 : "https://news.naver.com/section/105"
# 세계 : "https://news.naver.com/section/104"


# 정치의 경우 -> 17번 이상 더보기 버튼 누르면 24시간 이내 기사 모두 수집 가능할 것으로 보임. 


driver.get(url)

# 시간 정보가 "3시간 전", "20분 전"까지 더보기 버튼 클릭
def time_diff_in_minutes(post_time_str):
    """시간 차이를 계산하는 함수. 예: '0시간 전', '3시간 전', '20분 전'"""
    if "시간전" in post_time_str:
        hours_ago = int(post_time_str.replace("시간전", "").strip())
        return hours_ago * 60  # 시간을 분으로 변환
    elif "분전" in post_time_str:
        minutes_ago = int(post_time_str.replace("분전", "").strip())
        return minutes_ago
    return float('inf')  # 시간 정보가 없으면 무한값 반환

# 스크롤 및 "더보기" 버튼 클릭
for _ in range(100):  # 원하는 만큼 반복해서 기사 더 가져오기
    try:
        # "더보기" 버튼 클릭 (명시적으로 대기)
        more_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".section_more_inner._CONTENT_LIST_LOAD_MORE_BUTTON"))
        )
        ActionChains(driver).move_to_element(more_button).click().perform()
        time.sleep(3)  # 버튼 클릭 후 페이지 로드 대기
    except Exception:
        break  # 더 이상 버튼이 없으면 종료

# 페이지 소스 가져오기
html = driver.page_source
driver.quit()

# BeautifulSoup으로 파싱
soup = BeautifulSoup(html, "html.parser")

# 기사 정보 수집 (기사 제목, 이미지, 시간)
articles = []
for article_div in soup.select(".sa_item_inner"):
    # 기사 제목
    title_tag = article_div.select_one(".sa_text_title._NLOG_IMPRESSION")
    if title_tag:
        article_link = title_tag.get("href")
    else:
        article_link = None

    # 기사 이미지
    img_tag = article_div.find("img")
    img_src = img_tag.get("src") if img_tag else None

    # 시간 정보 (시간이 <b> 태그 안에 있음)
    time_tag = article_div.select_one(".sa_text_datetime b")
    if time_tag:
        post_time_str = time_tag.get_text().strip()
    else:
        post_time_str = None

    # 시간 차이를 계산하고 "3시간 전" 이내의 기사만 필터링
    if post_time_str and time_diff_in_minutes(post_time_str) <= 180000000:  # 180분(3시간) 이내의 기사만
        articles.append({
            "title": title_tag.get_text() if title_tag else None,
            "link": article_link,
            "img_src": img_src,
            "time": post_time_str
        })

# 결과 출력
print(f"수집한 기사 개수: {len(articles)}")
# for article in articles:
#     print(f"제목: {article['title']}")
#     print(f"링크: {article['link']}")
#     print(f"이미지: {article['img_src']}")
#     print(f"시간: {article['time']}")
#     print("-" * 50)






for article in articles:

    # 네이버 뉴스 기사 URL
    url = article['link']

    # User-Agent 설정 (크롤링 차단 방지)
    headers = {"User-Agent": "Mozilla/5.0"}

    # HTTP 요청 보내기
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 기사 제목 가져오기
    title = soup.find('h2', class_='media_end_head_headline')
    title_text = title.get_text(strip=True) if title else "제목 없음"

    # 기사 본문 가져오기 (id="dic_area")
    article_body = soup.find('article', id='dic_area')
    content = article_body.get_text("\n", strip=True) if article_body else "기사 본문 없음"

    # 기사 날짜 가져오기 (data-date-time 속성 값)
    date_span = soup.find('span', class_='media_end_head_info_datestamp_time _ARTICLE_DATE_TIME')
    article_date_time = date_span['data-date-time'] if date_span and 'data-date-time' in date_span.attrs else "날짜 없음"

    # 이미지 및 이미지 설명 가져오기 (여러 개)
    images = []
    image_sections = soup.find_all('span', class_='end_photo_org')  # find_all() 사용

    for section in image_sections:
        img_tag = section.find('img')
        img_desc_tag = section.find(class_='img_desc')

        # src 또는 data-src 속성 가져오기
        img_url = img_tag.get('src') or img_tag.get('data-src', '이미지 없음') if img_tag else "이미지 없음"
        img_desc = img_desc_tag.get_text(strip=True) if img_desc_tag else "이미지 설명 없음"

        images.append({"url": img_url, "desc": img_desc})
        #images.append(f"URL: {img_url}, 설명: {img_desc}")

    # 출력
    print(f"기사 링크 : {url}")
    print(f"📰 기사 제목: {title_text}\n")
    print(f"📅 기사 날짜: {article_date_time}\n")
    #print(f"📄 기사 내용:\n{content}\n")
    print("🖼 이미지 목록:")
    for i, img in enumerate(images, 1):
        print(f"{i}. URL: {img}")
        #print(f"   설명: {img['desc']}\n")
    print("\n\n#######################################################################\n\n")
    
    id = hash(url)
    url = url
    vector = get_embedding(title_text)

    # Pinecone에 벡터 저장
    # index.upsert([(str(id), vector)])
    metadata = {
        'title' : title_text,
        'content': content,
        'date_time' : article_date_time,
        'url': url,
        'image' : images[0]['url'] if images else ''
    }
    
    # Pinecone에 벡터 저장
    index.upsert([(str(id), vector, metadata)])

print("데이터를 Pinecone에 성공적으로 저장했습니다.")







