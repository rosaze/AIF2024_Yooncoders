import streamlit as st
from PIL import Image
import io
import os
import openai
import requests
from dotenv import load_dotenv


from article_org import extract_news_info, simplify_terms_dynamically, generate_webtoon_scenes
from user_input import render_news_search, search_news, generate_final_prompt
from image_gen import generate_image, save_image

# .env 파일 로드
load_dotenv()

# API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")
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

def save_image(image_url, filename):
    # 이미지 다운로드하여 로컬에 저장 
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            image_path = os.path.join("generated_images", filename)
            os.makedirs("generated_images", exist_ok=True)
            with open(image_path, 'wb') as f:
                f.write(response.content)
            return image_path
        return None
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
    render_news_search()

# 웹툰 생성 페이지
elif st.session_state.page == "generate_webtoon":
    st.markdown("<h1 style='text-align: center;'>웹툰 생성</h1>",
    unsafe_allow_html=True)
    #여기에 디버깅시 필요한 출력문 추가 
    
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

        if st.button("웹툰 생성 시작"):
            prompt = f"웹툰 스타일의 뉴스 기사 장면: {st.session_state.article_content[:200]}"
            image_url = generate_image(prompt)
            if image_url:
                image_path = save_image(image_url, f"cut_{st.session_state.current_cut_index + 1}.png")
                if image_path:
                    st.session_state.selected_images[st.session_state.current_cut_index] = Image.open(image_path)
                    st.success("이미지가 생성되었습니다.")
                    navigate_to("final_result")
        if st.session_state.simplified_content and st.button("웹툰 생성 시작", key="generate_webtoon_button"):
           # 각 단계의 결과를 기반으로 최종 프롬프트 생성
            prompt = generate_final_prompt(
                article_content=st.session_state.article_content,
                extracted_info=st.session_state.extracted_info,
                simplified_content=st.session_state.simplified_content,
                webtoon_episode=st.session_state.webtoon_episode
                )
            style = "webtoon"  # 원하는 스타일 추가
            negative_prompt = "low quality, blurry, no text in the image, avoid unrequested content, limit to two characters"
            image_url = generate_image(prompt, style=style, negative_prompt=negative_prompt)
            if image_url:
                image_path = save_image(image_url, f"cut_{st.session_state.current_cut_index + 1}.png")
                if image_path:
                    st.session_state.selected_images[st.session_state.current_cut_index] = Image.open(image_path)
                    st.session_state.current_cut_index += 1
                    st.success("이미지가 생성되었습니다.")
                    navigate_to("final_result")

# 최종 결과 페이지
elif st.session_state.page == "final_result":
    st.title("최종 결과")

    if st.session_state.webtoon_episode:
        st.subheader("생성된 웹툰 에피소드")
        st.write(st.session_state.webtoon_episode)
        
        # 생성된 이미지들 표시
        if st.session_state.selected_images:
            st.subheader("생성된 웹툰 이미지")
            for idx, image in st.session_state.selected_images.items():
                st.image(image, caption=f"컷 {idx + 1}")
    else:
        st.write("아직 생성된 웹툰 에피소드가 없습니다.")


