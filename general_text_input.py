import streamlit as st
from image_gen import generate_image_from_text, download_and_display_image
from PIL import Image

def render_general_text_input():
    """일반 텍스트 입력을 통한 이미지 생성 페이지"""
    st.title("일반 텍스트 입력을 통한 이미지 생성")

    # 텍스트 입력 필드
    user_text = st.text_area("이미지 생성을 위한 텍스트를 입력하세요", placeholder="예: 짧은 소설이나 직접 작성한 텍스트")
    
    # 스타일 선택 드롭다운
    style = st.selectbox("원하는 스타일을 선택하세요", ["minimalist", "pictogram", "cartoon", "cyberpunk", "webtoon"])

    # 이미지 컷 수 선택 슬라이더
    cut_count = st.slider("생성할 이미지 컷 수를 선택하세요", min_value=1, max_value=5, value=1)
    
    # 이미지 비율 선택 (예: 1:1, 16:9, 9:16)
    aspect_ratio = st.selectbox("이미지 비율을 선택하세요", ["1:1", "16:9", "9:16"])

    # 텍스트 기반 이미지 생성 시작 버튼
    if st.button("이미지 생성 시작"):
        if user_text.strip():  # 입력 텍스트가 존재할 경우에만 실행
            for i in range(cut_count):
                # 프롬프트 생성
                prompt = f"{user_text[:200]} - 스타일: {style} (컷 {i + 1})"
                
                # 일반 텍스트 전용 이미지 생성 함수 호출
                image_url, revised_prompt, created_seed = generate_image_from_text(prompt, style=style, aspect_ratio=aspect_ratio)
                
                if image_url:
                    # 이미지 다운로드 및 세션에 저장
                    filename = f"text_cut_{i + 1}.png"
                    download_and_display_image(image_url, filename=filename)
                    
                    # 생성된 이미지 로드하여 세션에 저장 후 표시
                    st.session_state.selected_images[i] = Image.open(filename)
                    st.image(st.session_state.selected_images[i], caption=f"컷 {i + 1}")

            st.success("모든 이미지가 성공적으로 생성되었습니다.")
        else:
            st.warning("텍스트를 입력해 주세요.")
