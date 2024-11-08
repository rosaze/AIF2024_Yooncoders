# general_text_input.py
import streamlit as st
from image_gen import generate_image_from_text, download_and_display_image
from PIL import Image
import requests
from openai import OpenAI
import logging
import os

# API 키 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def render_general_text_input():
    #일반 텍스트 입력을 통한 이미지 생성 페이지
    st.title("일반 텍스트로 이미지 생성")

    # Initialize session state for selected images if not exists
    if 'selected_images' not in st.session_state:
        st.session_state.selected_images = {}
     # 텍스트 입력 필드
    user_text = st.text_area("스토리나 상황을 입력해주세요", placeholder="긴 소설이나, 책의 일부분이어도 좋아요.")
    #캐릭터 설정 ( 선택사항 )
    character_description=st.text_input(
        "주요 캐릭터의 특징을 입력해주세요! ( 선택입니다)",
        placeholder= "예: 까만 머리의 10대 소녀, 눈송이를 들고 있다."
    )
    #감정, 분위기 선택
    mood=st.selectbox(
        "장면의 분위기를 선택해주세요",
        ["일상적","긴장된","진지한","따뜻한","즐거운"]
    )
   # 구도 선택
    composition = st.selectbox(
        "장면의 구도를 선택해주세요",
        ["배경과 인물", "근접 샷", "대화형", "풍경 위주","일반"]
    )
    
    
    # 스타일 선택 드롭다운
    style = st.select_slider("원하는 스타일을 선택하세요", ["minimalist", "pictogram", "cartoon", "webtoon","artistic"])

    # 이미지 컷 수 선택 슬라이더
    cut_count = st.radio("생성할 이미지 컷 수를 선택하세요", options=[1,2,3,4],horizontal=True)
    
    # 이미지 비율 선택
    aspect_ratio = st.selectbox("이미지 비율을 선택하세요", ["1:1", "16:9", "9:16"])
    
    # 부정 프롬프트
    negative_prompt = """
    추상적인 이미지, 흐릿한 이미지, 낮은 품질, 비현실적인 비율, 
    왜곡된 얼굴, 추가 사지, 이미지 안 텍스트, 말풍선, 5명 이상의 인물,국기 또는 나라, 
    잘린 이미지, 과도한 필터, 비문법적 구조, 중복된 특징, 
    나쁜 해부학, 나쁜 손, 과도하게 복잡한 배경
    """    
    if st.button("이미지 생성 시작"):
        if user_text.strip():
            scenes = create_webtoon_scenes(user_text,character_description,mood,style)
            logging.info("생성된 장면 프롬프트: %s", scenes)
            
            # Progress bar 초기화
            progress_bar = st.progress(0)
            
            for i, scene in enumerate(scenes[:cut_count]):
                prompt = construct_webtoon_prompt(
                    scene=scene,
                    composition=composition,
                    character_desc=character_description,
                    mood=mood,
                    style=style
                )
                image_url, revised_prompt, created_seed = generate_image_from_text(
                    prompt=prompt,
                    style=style,
                    aspect_ratio=aspect_ratio,
                    negative_prompt=negative_prompt
                )
                
                if image_url:
                    # 로그에 생성 정보 기록
                    logging.info(f"컷 {i+1} 생성 정보:")
                    logging.info(f"프롬프트: {prompt}")
                    logging.info(f"생성 시드: {created_seed}")
                    
                    # 이미지 다운로드 및 세션에 저장
                    filename = f"webtoon_cut_{i + 1}.png"
                    download_and_display_image(image_url, filename=filename)
                    
                    # 생성된 이미지 로드하여 세션에 저장 후 표시
                    st.session_state.selected_images[i] = Image.open(filename)
                    st.image(st.session_state.selected_images[i], caption=f"컷 {i + 1}")
                else:
                    logging.error(f"컷 {i+1} 생성 실패")
                
                # Progress bar 업데이트
                progress_bar.progress((i + 1) / cut_count)

            st.success("모든 이미지가 성공적으로 생성되었습니다.")
        else:
            st.warning("스토리나 상황을 입력해 주세요.")

def create_webtoon_scenes(user_text, character_desc, mood,style):
    client = OpenAI()
    
    prompt = f"""다음 내용을 웹툰의 연속된 장면들로 변환해주세요.
    
    스토리: {user_text}
    주요 캐릭터: {character_desc if character_desc else '특별히 지정되지 않음'}
    분위기: {mood}
    스타일: {style}
    
    각 장면은 다음 요소를 포함해야 합니다:
    1. 명확한 캐릭터의 행동과 표정
    2. 구체적인 배경 설명
    3. 장면의 분위기나 감정
    4. 시각적으로 표현 가능한 요소들
    장면의 개수는 4개 이하로 해주세요.
    각 장면은 웹툰 그림체로 표현하기 적합하도록 구체적으로 설명해주세요."""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": prompt
        }],
        max_tokens=1000
    )
    
    # 응답에서 텍스트 추출하고 줄바꿈으로 분리
    scenes = response.choices[0].message.content.strip().split("\n")
    return [scene for scene in scenes if scene]

def construct_webtoon_prompt(scene, composition,character_desc,mood,style):
    #webtoon 스타일에 최적화된 프롬프트 생성 
    style_guide = {
         "minimalist": "minimal details, simple lines, clean composition, essential elements only",
        "pictogram": "symbolic representation, simplified shapes, icon-like style",
        "cartoon": "animated style, exaggerated features, bold colors",
        "webtoon": "webtoon style, manhwa art style, clean lines, vibrant colors",
        "artistic": "painterly style, artistic interpretation, creative composition"
    }
     # 구도에 따른 추가 지시사항
    composition_guide = {
        "배경과 인물": "balanced composition of character and background, eye-level shot",
    "근접 샷": "close-up shot, focused on character's expression",
    "대화형": "two-shot composition, characters facing each other",
    "풍경 위주": "wide shot, emphasis on background scenery",
    "일반": "standard view, balanced composition"
    }
# 분위기에 따른 추가 지시사항
    mood_guide = {
        "일상적": "natural lighting, soft colors",
    "긴장된": "dramatic lighting, high contrast, intense atmosphere",
    "진지한": "subdued lighting, serious atmosphere, formal composition",
    "따뜻한": "warm colors, soft lighting, comfortable atmosphere",
    "즐거운": "bright lighting, warm colors, dynamic composition"
    }
    prompt = f"""
    {scene}
    {style_guide[style]},
    {composition_guide[composition]},
    {mood_guide[mood]},
    {"character description: " + character_desc if character_desc else ""}
    """
    return prompt