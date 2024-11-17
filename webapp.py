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

# .env 파일 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 세션 상태 초기화
if "page" not in st.session_state:
    st.session_state.update({
        "page": "news_search",
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

def navigate_to(page):
    """페이지 이동"""
    st.session_state.page = page

# 사이드바 네비게이션 - 순서 변경 및 설명 추가
st.sidebar.title("웹툰 메이커")
st.sidebar.markdown("""
### 원하는 방식을 선택하세요:
1. 일반 텍스트로 웹툰 만들기
2. 뉴스 기사로 웹툰 만들기
""")

tabs = st.sidebar.radio(
    "생성 방식 선택",
    ["일반 텍스트 입력", "뉴스 검색"],
    captions=["자유로운 텍스트로 웹툰 생성", "뉴스 기사 기반 웹툰 생성"]
)

if tabs == "일반 텍스트 입력":
    st.session_state.page = "text_input"
elif tabs == "뉴스 검색":
    st.session_state.page = "news_search"

# 결과 보기 버튼
if st.sidebar.button("생성된 결과 보기"):
    st.session_state.page = "final_result"

# render_general_text_input() 함수를 다음으로 대체
if st.session_state.page == "text_input":
    try:
        clip_analyzer = CLIPAnalyzer()
        converter = TextToWebtoonConverter(client, clip_analyzer)
        converter.render_ui()
    except Exception as e:
        st.error(f"텍스트 입력 처리 중 오류 발생: {str(e)}")

elif st.session_state.page == "news_search":
    render_news_search()

elif st.session_state.page == "generate_webtoon":
    st.markdown("<h1 style='text-align: center;'>웹툰 생성</h1>", unsafe_allow_html=True)
    
    if st.session_state.article_content:
        st.markdown("### 선택된 기사 내용")
        st.write(st.session_state.article_content)

        if st.button("핵심 정보 추출"):
            if st.session_state.selected_article:
                extracted_info = extract_news_info(
                    title=st.session_state.selected_article["title"],
                    content=st.session_state.article_content
                )
                st.session_state.extracted_info = extracted_info
                st.success("핵심 정보가 성공적으로 추출되었습니다!")
                st.write(extracted_info)

        if st.session_state.extracted_info and st.button("용어 간소화 및 키워드 추출"):
            simplified_content = simplify_terms_dynamically(
                content=st.session_state.extracted_info,
                domain_hint="general",
                simplification_level="basic",
                extract_keywords=True
            )
            st.session_state.simplified_content = simplified_content
            st.success("용어 간소화 및 키워드 추출 완료!")
            st.write(simplified_content)

        if st.session_state.simplified_content and st.button("웹툰 에피소드 생성"):
            webtoon_episode = generate_webtoon_scenes(
                extracted_info=st.session_state.simplified_content
            )
            st.session_state.webtoon_episode = webtoon_episode
            st.success("웹툰 에피소드 생성 완료!")
            st.write(webtoon_episode)

# 최종 결과 페이지
elif st.session_state.page == "final_result":
    st.title("생성된 웹툰")
    
    if 'selected_images' in st.session_state and st.session_state.selected_images:
        # 이미지들을 그리드 형태로 표시
        cols = st.columns(2)  # 2열 그리드
        for idx, image in st.session_state.selected_images.items():
            with cols[idx % 2]:  # 이미지를 번갈아가며 배치
                st.image(image, caption=f"컷 {idx + 1}", use_column_width=True)
                
        # 다운로드 버튼 추가
        st.download_button(
            label="웹툰 이미지 다운로드",
            data=Image.open("generated_images/webtoon_cut_1.png"),
            file_name="my_webtoon.png",
            mime="image/png"
        )
    else:
        st.info("아직 생성된 이미지가 없습니다. 먼저 웹툰을 생성해주세요!")

    # 새로운 웹툰 생성 버튼
    if st.button("새로운 웹툰 만들기"):
        st.session_state.selected_images = {}  # 이미지 초기화
        st.session_state.page = "text_input"  # 텍스트 입력 페이지로 이동