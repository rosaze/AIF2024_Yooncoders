import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
from bs4 import BeautifulSoup
import re
from openai import OpenAI
import urllib.request
from dotenv import load_dotenv
import requests
from user_input import render_news_search

# .env 파일 로드
load_dotenv()

# API 키 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 세션 상태 초기화
if "page" not in st.session_state:
    st.session_state.page = "news_search"

if "selected_article" not in st.session_state:
    st.session_state.selected_article = None

if "article_content" not in st.session_state:
    st.session_state.article_content = None

if "cut_count" not in st.session_state:
    st.session_state.cut_count = 3

if "selected_images" not in st.session_state:
    st.session_state.selected_images = [None] * st.session_state.cut_count

if "current_cut_index" not in st.session_state:
    st.session_state.current_cut_index = 0

def search_news(query, sort='sim'):
    """네이버 뉴스 API를 통해 뉴스 검색"""
    url = f"https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {
        "query": query,
        "sort": sort,
        "display": 10
    }
    
    response = requests.get(url, headers=headers, params=params)
    return response.json() if response.status_code == 200 else None

def extract_news_info(article_url):
    """네이버 뉴스 기사 내용 추출"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(article_url, headers=headers)
        response.raise_for_status()  # 오류 발생시 예외 발생
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 네이버 뉴스 본문 찾기
        article = soup.select_one('#dic_area')  # 네이버 뉴스 본문 영역의 ID
        if not article:
            article = soup.select_one('#articeBody')  # 다른 가능한 본문 영역 ID
            
        if article:
            # 본문에서 불필요한 요소 제거
            for tag in article.select('script, iframe, style'):
                tag.decompose()
                
            # 텍스트 추출 및 정제
            content = article.get_text(strip=True)
            content = re.sub(r'\s+', ' ', content)  # 연속된 공백 제거
            return content
        else:
            return "기사 내용을 찾을 수 없습니다."
            
    except Exception as e:
        st.error(f"기사 내용 추출 중 오류 발생: {str(e)}")
        return None

def generate_image(prompt):
    """DALL-E를 사용하여 이미지 생성"""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        st.error(f"이미지 생성 중 오류 발생: {str(e)}")
        return None

def save_image(url, save_path="result.png"):
    """이미지 URL을 로컬에 저장"""
    try:
        urllib.request.urlretrieve(url, save_path)
        return save_path
    except Exception as e:
        st.error(f"이미지 저장 중 오류 발생: {str(e)}")
        return None

def navigate_to(page):
    """페이지 이동"""
    st.session_state.page = page

# 사이드바 네비게이션
st.sidebar.title("네비게이션")
st.sidebar.button("뉴스 검색", on_click=lambda: navigate_to("news_search"))
st.sidebar.button("웹툰 생성", on_click=lambda: navigate_to("generate_webtoon"))
st.sidebar.button("최종 결과", on_click=lambda: navigate_to("final_result"))

# 뉴스 검색 페이지
if st.session_state.page == "news_search":
    st.title("뉴스 검색")
    
    search_option = st.radio("검색 방식 선택", ["키워드 검색", "URL 직접 입력"])
    
    if search_option == "키워드 검색":
        search_query = st.text_input("검색어를 입력하세요:")
        sort_option = st.selectbox("정렬 방식", ["정확도순", "최신순"], key="sort")
    
        if st.button("검색") and search_query:
            sort_param = 'sim' if sort_option == "정확도순" else 'date'
            results = search_news(search_query, sort_param)
        
            if results and 'items' in results:
                st.session_state.search_results = results['items']
                for idx, item in enumerate(results['items']):
                    st.markdown(f"### {item['title']}")
                    st.write(item['description'])
                    if st.button(f"이 기사로 웹툰 만들기", key=f"select_{idx}"):
                        st.session_state.selected_article = item
                        st.session_state.article_content = extract_news_info(item['originallink'])
                        navigate_to("generate_webtoon")
    
    else:  # URL 직접 입력
        article_url = st.text_input("뉴스 기사 URL을 입력하세요:")
        if st.button("기사 가져오기") and article_url:
            content = extract_news_info(article_url)
            if content:
                st.session_state.article_content = content
                st.success("기사 내용을 성공적으로 가져왔습니다!")
                st.markdown("### 가져온 기사 내용")

                 # 스크롤 가능한 텍스트 영역 생성
                st.text_area("", value=content, height=300)
            # 또는 container를 사용한 방법:
            # with st.container():
            #     st.markdown(f"""
            #         <div style="height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ccc; border-radius: 5px;">
            #             {content}
            #         </div>
            #         """, unsafe_allow_html=Tru
                if st.button("이 기사로 웹툰 만들기"):
                    navigate_to("generate_webtoon")
            else:
                st.error("기사 내용을 가져오는데 실패했습니다.")

# 웹툰 생성 페이지
elif st.session_state.page == "generate_webtoon":
    st.title("웹툰 생성")
    
    if st.session_state.article_content:
        st.markdown("### 선택된 기사 내용")
        st.write(st.session_state.article_content)
        
        if st.button("웹툰 생성 시작"):
            # 여기에 웹툰 생성 로직 구현
            prompt = f"웹툰 스타일의 뉴스 기사 장면: {st.session_state.article_content[:200]}"
            image_url = generate_image(prompt)
            if image_url:
                image_path = save_image(image_url, f"cut_{st.session_state.current_cut_index + 1}.png")
                if image_path:
                    st.session_state.selected_images[st.session_state.current_cut_index] = Image.open(image_path)
                    st.success("이미지가 생성되었습니다.")
                    navigate_to("final_result")

# 최종 결과 페이지
elif st.session_state.page == "final_result":
    st.title("최종 결과")
    
    for i, img in enumerate(st.session_state.selected_images):
        if img:
            st.markdown(f"### 컷 {i + 1}")
            st.image(img, caption=f"생성된 웹툰 컷 {i + 1}", use_column_width=True)
            
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            
            st.download_button(
                label=f"컷 {i + 1} 다운로드",
                data=img_bytes,
                file_name=f"news_webtoon_cut_{i+1}.png",
                mime="image/png"
            )