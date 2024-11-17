import streamlit as st
from PIL import Image
import io
import os
from openai import OpenAI
import requests
from dotenv import load_dotenv
from clip_analyzer import CLIPAnalyzer

# 각 기능별 모듈 import
from article_org import extract_news_info, simplify_terms_dynamically, generate_webtoon_scenes
from user_input import render_news_search, search_news, generate_final_prompt
from general_text_input import TextToWebtoonConverter
from nonfiction_input import NonFictionConverter  # 새로 추가된 모듈

# .env 파일 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 세션 상태 초기화
if "page" not in st.session_state:
    st.session_state.update({
        "page": "text_input",
        "selected_article": None,
        "article_content": None,
        "extracted_info": None,
        "simplified_content": None,
        "webtoon_episode": None,
        "current_cut_index": 0,
        "selected_images": {},
        "NAVER_CLIENT_ID": os.getenv("NAVER_CLIENT_ID"),
        "NAVER_CLIENT_SECRET": os.getenv("NAVER_CLIENT_SECRET"),
        "content_type": "general"  # 새로운 상태 변수 추가
    })

def navigate_to(page):
    """페이지 이동"""
    st.session_state.page = page

# 사이드바 네비게이션 - 새로운 옵션 추가
st.sidebar.title("콘텐츠 생성기")
st.sidebar.markdown("""
### 원하는 방식을 선택하세요:
1. 일반 텍스트로 웹툰 만들기
2. 교육/과학 콘텐츠 시각화
3. 뉴스 기사로 웹툰 만들기
""")

tabs = st.sidebar.radio(
    "생성 방식 선택",
    ["일반 텍스트 입력", "교육/과학 콘텐츠", "뉴스 검색"],
    captions=["자유로운 텍스트로 웹툰 생성", 
             "교육/과학 콘텐츠 시각화", 
             "뉴스 기사 기반 웹툰 생성"]
)

# 탭 선택에 따른 페이지 및 콘텐츠 타입 설정
if tabs == "일반 텍스트 입력":
    st.session_state.page = "text_input"
    st.session_state.content_type = "general"
elif tabs == "교육/과학 콘텐츠":
    st.session_state.page = "nonfiction_input"
    st.session_state.content_type = "nonfiction"
elif tabs == "뉴스 검색":
    st.session_state.page = "news_search"
    st.session_state.content_type = "news"

# 결과 보기 버튼
if st.sidebar.button("생성된 결과 보기"):
    st.session_state.page = "final_result"

# 페이지별 렌더링
if st.session_state.page == "text_input":
    try:
        clip_analyzer = CLIPAnalyzer()
        converter = TextToWebtoonConverter(client, clip_analyzer)
        converter.render_ui()
    except Exception as e:
        st.error(f"텍스트 입력 처리 중 오류 발생: {str(e)}")

elif st.session_state.page == "nonfiction_input":
    try:
        converter = NonFictionConverter(client)
        converter.render_ui()
    except Exception as e:
        st.error(f"비문학 콘텐츠 처리 중 오류 발생: {str(e)}")

elif st.session_state.page == "news_search":
    render_news_search()

elif st.session_state.page == "final_result":
    st.title("생성된 결과")
    
    if st.session_state.content_type == "nonfiction":
        # 비문학 콘텐츠용 결과 표시
        st.subheader("교육/과학 콘텐츠 시각화 결과")
        if 'visualization_result' in st.session_state:
            st.image(st.session_state.visualization_result)
            
            # 설명 및 메타데이터 표시
            if 'visualization_metadata' in st.session_state:
                with st.expander("시각화 세부 정보"):
                    st.json(st.session_state.visualization_metadata)
            
            # 다운로드 버튼
            if 'visualization_result' in st.session_state:
                st.download_button(
                    label="시각화 이미지 다운로드",
                    data=st.session_state.visualization_result,
                    file_name="visualization.png",
                    mime="image/png"
                )
        else:
            st.info("아직 생성된 시각화가 없습니다. 먼저 콘텐츠를 생성해주세요!")
            
    else:
        # 기존 웹툰/뉴스 결과 표시 로직
        if 'selected_images' in st.session_state and st.session_state.selected_images:
            cols = st.columns(2)
            for idx, image in st.session_state.selected_images.items():
                with cols[idx % 2]:
                    st.image(image, caption=f"컷 {idx + 1}", use_column_width=True)
            
            st.download_button(
                label="웹툰 이미지 다운로드",
                data=Image.open("generated_images/webtoon_cut_1.png"),
                file_name="my_webtoon.png",
                mime="image/png"
            )
        else:
            st.info("아직 생성된 이미지가 없습니다. 먼저 웹툰을 생성해주세요!")

    # 새로운 콘텐츠 생성 버튼
    if st.button("새로운 콘텐츠 만들기"):
        # 상태 초기화
        st.session_state.selected_images = {}
        st.session_state.visualization_result = None
        st.session_state.visualization_metadata = None
        # 이전 페이지로 이동
        st.session_state.page = st.session_state.content_type + "_input"

# 에러 처리를 위한 전역 예외 처리
try:
    if st.session_state.get("error"):
        st.error(st.session_state.error)
        st.session_state.error = None
except Exception as e:
    st.error(f"예상치 못한 오류가 발생했습니다: {str(e)}")