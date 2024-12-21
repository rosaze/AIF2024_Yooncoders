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
from nonfiction_input import NonFictionConverter

# .env 파일 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 세션 상태 초기화
if "page" not in st.session_state:
    st.session_state.update({
        "page": "home",  # 기본값을 'home'으로 변경
        "selected_article": None,
        "article_content": None,
        "extracted_info": None,
        "simplified_content": None,
        "webtoon_episode": None,
        "current_cut_index": 0,
        "selected_images": {},
        "NAVER_CLIENT_ID": os.getenv("NAVER_CLIENT_ID"),
        "NAVER_CLIENT_SECRET": os.getenv("NAVER_CLIENT_SECRET")
    })

def render_home():
    st.title("Webtoonizer - 텍스트 시각화 도구")
    
    # 중앙 정렬을 위한 열 배치
    col1, col2, col3 = st.columns([1,2,1])
    
    with col2:
        st.markdown("""
        <style>
        .big-font {
            font-size:20px !important;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .container {
            display: flex;
            flex-direction: column;
            gap: 20px;
            padding: 20px;
        }
        .description {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }
        .button-spacing {
            margin-bottom: 15px;
        }
        </style>
        <div class="big-font">원하시는 시각화 방식을 선택해주세요</div>
        """, unsafe_allow_html=True)

        # 스토리 텍스트 시각화 버튼
        if st.button("📚 스토리 텍스트 시각화", use_container_width=True, key="story"):
            st.session_state.page = "text_input"
            st.rerun()

        st.markdown("""
        <div class="description">
        소설, 시나리오, 이야기 등을 웹툰 형식으로 변환합니다.
        </div>
        """, unsafe_allow_html=True)
        
        st.write("---")  # 구분선 추가

        # 교육/과학 텍스트 시각화 버튼
        if st.button("🎓 교육/과학 텍스트 시각화", use_container_width=True, key="edu"):
            st.session_state.page = "nonfiction_input"
            st.rerun()

        st.markdown("""
        <div class="description">
        교육 자료, 과학 개념, 프로세스 등을 시각적으로 설명합니다.
        </div>
        """, unsafe_allow_html=True)
        
        st.write("---")  # 구분선 추가

        # 뉴스 시각화 버튼 추가
        #if st.button("📰 뉴스 시각화", use_container_width=True, key="news"):
            #st.session_state.page = "news_search"
            #st.rerun()

        #st.markdown("""
        #<div class="description">
        #최신 뉴스 기사를 검색하고 웹툰으로 변환합니다.
        #</div>
        #""", unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="Webtoonizer",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 사이드바에 홈으로 돌아가기 버튼 추가
    with st.sidebar:
        if st.button("🏠 홈으로 돌아가기", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
        
        st.markdown("---")

    # 페이지 라우팅
    if st.session_state.page == "home":
        render_home()
        
    elif st.session_state.page == "text_input":
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
            st.error(f"교육/과학 콘텐츠 처리 중 오류 발생: {str(e)}")
    """
    elif st.session_state.page == "news_search":
        try:
            render_news_search()
        except Exception as e:
            st.error(f"뉴스 검색 처리 중 오류 발생: {str(e)}")
    """
    # 에러 처리
    try:
        if st.session_state.get("error"):
            st.error(st.session_state.error)
            st.session_state.error = None
    except Exception as e:
        st.error(f"예상치 못한 오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()