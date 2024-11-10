# general_text_input.py
import streamlit as st
from image_gen import generate_image_from_text, download_and_display_image
from PIL import Image
import requests
from openai import OpenAI
import logging
import os
import io
from dotenv import load_dotenv
import certifi
import ssl
from clip_analyzer import CLIPAnalyzer
from datetime import datetime


# SSL 컨텍스트 생성
ssl_context = ssl.create_default_context(cafile=certifi.where())

load_dotenv()

# API 키 확인 및 클라이언트 초기화
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# OpenAI 클라이언트 초기화 with SSL 설정
client = OpenAI(
    api_key=api_key,
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def render_general_text_input():
    st.title("일반 텍스트로 이미지 생성")

    # Initialize session state for selected images if not exists
    if 'selected_images' not in st.session_state:
        st.session_state.selected_images = {}
    
    # 텍스트 입력 필드
    user_text = st.text_area("스토리나 상황을 입력해주세요", placeholder="긴 소설이나, 책의 일부분이어도 좋아요.")
    
    # 캐릭터 설정 (선택사항)
    character_description = st.text_input(
        "주요 캐릭터의 특징을 입력해주세요! (선택입니다)",
        placeholder="예: 까만 머리의 10대 소녀, 눈송이를 들고 있다."
    )
    
    # 감정, 분위기 선택
    mood = st.selectbox(
        "장면의 분위기를 선택해주세요",
        ["일상적", "긴장된", "진지한", "따뜻한", "즐거운"]
    )
    
    # 구도 선택
    composition = st.selectbox(
        "장면의 구도를 선택해주세요",
        ["배경과 인물", "근접 샷", "대화형", "풍경 위주", "일반"]
    )
    
    # 스타일 선택 드롭다운
    style = st.select_slider(
        "원하는 스타일을 선택하세요",
        ["minimalist", "pictogram", "cartoon", "webtoon", "artistic"]
    )

    # 이미지 컷 수 선택
    cut_count = st.radio(
        "생성할 이미지 컷 수를 선택하세요",
        options=[1, 2, 3, 4],
        horizontal=True
    )
    
    # 이미지 비율 선택
    aspect_ratio = st.selectbox(
        "이미지 비율을 선택하세요",
        ["1:1", "16:9", "9:16"]
    )
    
    # 부정 프롬프트
    negative_prompt = """
    추상적인 이미지, 흐릿한 이미지, 낮은 품질, 비현실적인 비율, 
    왜곡된 얼굴, 추가 사지, 이미지 안 텍스트, 말풍선, 5명 이상의 인물, 국기 또는 나라, 
    잘린 이미지, 과도한 필터, 비문법적 구조, 중복된 특징, 
    나쁜 해부학, 나쁜 손, 과도하게 복잡한 배경
    """
    
    if st.button("이미지 생성 시작"):
        if user_text.strip():
            with st.spinner('장면 분석 및 이미지 생성 중...'):
                prompts, generated_images = generate_visual_sequence(
                    prompt=user_text,
                    cut_count=cut_count,
                    style=style,
                    composition=composition,
                    mood=mood,
                    character_desc=character_description
                )
                
                # Progress bar 초기화
                progress_bar = st.progress(0)
                
                # 이미지를 표시할 열 생성
                if cut_count > 1:
                    cols = st.columns(min(cut_count, 2))  # 최대 2열까지만 생성
                
                # 각 프롬프트에 대해 이미지 생성
                for i, prompt in enumerate(prompts):
                    if i >= cut_count:
                        break
                        
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
                        
                        # 이미지 다운로드 및 표시
                        image = download_and_display_image(image_url)
                        if image:
                            if cut_count > 1:
                                with cols[i % 2]:
                                    st.image(image, caption=f"컷 {i+1}", use_column_width=True)
                                    with st.expander(f"장면 {i+1} 상세 설명"):
                                        st.markdown("**원본 설명**")
                                        st.text(prompt)
                                        st.markdown("**요약 설명**")
                                        summary = summarize_scene(prompt)
                                        st.write(summary)
                            else:
                                st.image(image, caption=f"컷 {i+1}", use_column_width=True)
                                with st.expander(f"컷 {i+1} 상세 설명"):
                                    tab1, tab2 = st.tabs(["요약 설명", "상세 설명"])
                                    with tab1:
                                        summary = summarize_scene(prompt)
                                        st.write(summary)
                                    with tab2:
                                        st.text(prompt)
                                        
                            st.session_state.selected_images[i] = image
                        else:
                            st.error(f"컷 {i+1} 이미지 로드 실패")
                    
                    # Progress bar 업데이트
                    progress_bar.progress((i + 1) / len(prompts))
                
                st.success("모든 이미지가 성공적으로 생성되었습니다.")
        else:
            st.warning("스토리나 상황을 입력해 주세요.")
"""
def create_webtoon_scenes(user_text, character_desc, mood,style):
    client = OpenAI()
    
    prompt = f'다음 내용을 웹툰의 연속된 장면들로 변환해주세요.
    
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
    각 장면은 웹툰 그림체로 표현하기 적합하도록 구체적으로 설명해주세요.'
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
"""
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

#여기까지 construct webtoon prompt, create webtoon scenes, render general text input 
# 여기서 부터 새로 추가 
def analyze_text_for_scenes(text, cut_count):
    """
    텍스트를 분석하여 이미지화할 수 있는 주요 장면들을 추출합니다.
    
    Parameters:
    text (str): 사용자가 입력한 원문 텍스트
    cut_count (int): 생성할 이미지 컷 수
    
    Returns:
    list: 선택된 장면들의 설명
    """
    global client  
    try:
        print(f"Starting analyze_text_for_scenes...")
        print(f"Using API key: {client.api_key[:5]}...")
        print(f"Client configuration: {client}") 

        system_prompt = """당신은 텍스트를 분석하여 시각화할 수 있는 중요한 장면들을 선별하는 전문가입니다.
        다음 기준으로 장면을 선택하세요:
        1. 시각적으로 표현 가능한 구체적인 상황
        2. 이야기의 핵심을 전달할 수 있는 중요한 순간
        3. 감정과 분위기가 잘 드러나는 장면
        4. 인물의 행동과 표정이 포함된 장면
        """
        
        user_prompt = f"""다음 텍스트에서 {cut_count}개의 가장 중요한 장면을 선택하세요.
        각 장면은 반드시 다음 요소를 포함해야 합니다:
        - 장소와 배경 설명
        - 인물의 행동과 표정
        - 감정과 분위기
        - 시각적 세부 사항
        
        원문:
        {text}
        
        참고사항:
        - {cut_count}컷이므로, {'전체 내용을 골고루 다루되 핵심적인 장면들을 선택하세요.' if cut_count >= 3 else '가장 핵심이 되는 장면만 선택하세요.'}
        - 각 장면은 구체적이고 시각적으로 표현 가능해야 합니다.
        """
        
        print("Attempting API call for scene analysis...")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        print(f"API call successful. Response type: {type(response)}")
        
        scenes = response.choices[0].message.content.strip().split("\n\n")
        print(f"Successfully extracted {len(scenes)} scenes")
        return scenes
        
    except Exception as e:
        print(f"Error in analyze_text_for_scenes:")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        print(f"Error details: {e.__dict__}")
        raise

def create_detailed_scene_description(scene, style, composition, mood):
    """
    각 장면에 대한 상세한 시각적 설명을 생성합니다.
    
    Parameters:
    scene (str): 기본 장면 설명
    style (str): 선택된 스타일
    composition (str): 선택된 구도
    mood (str): 선택된 분위기
    
    Returns:
    str: 상세한 시각적 설명
    """
    global client
    try:
        print(f"Starting create_detailed_scene_description...")
        print(f"Input parameters: style={style}, composition={composition}, mood={mood}")
            
        prompt = f"""다음 장면을 웹툰/만화 형식의 한 컷으로 구현하기 위한 상세한 시각적 설명을 작성하세요.

        장면 내용:
        {scene}

        요구사항:
        - 스타일: {style}
        - 구도: {composition}
        - 분위기: {mood}

        다음 요소들을 반드시 포함하여 설명하세요:
        1. 배경의 구체적 묘사 (공간, 소품, 조명 등)
        2. 인물의 상세한 묘사 (위치, 포즈, 표정, 시선 등)
        3. 화면 구성 (주요 요소들의 배치, 강조점 등)
        4. 분위기를 전달하는 시각적 요소 (조명, 그림자, 색감 등)

        설명은 DALL-E가 이해하기 쉽도록 구체적이고 명확하게 작성하세요."""
        
        print("Attempting API call for detailed description...")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        print("Detailed description created successfully")
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"Error in create_detailed_scene_description:")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        raise

def generate_visual_sequence(prompt, cut_count, style, composition, mood, character_desc):
    """
    텍스트를 받아 웹툰 형식의 이미지 시퀀스를 생성
    
    Parameters:
    prompt (str): 사용자가 입력한 원문 텍스트
    cut_count (int): 생성할 이미지 컷 수
    style (str): 선택된 스타일
    composition (str): 선택된 구도
    mood (str): 선택된 분위기
    character_desc (str): 캐릭터 설명
    
    Returns:
    tuple: (final_prompts, generated_images)
    """
    try:
        print("Starting generate_visual_sequence...")
        print(f"Parameters: cut_count={cut_count}, style={style}, composition={composition}, mood={mood}")
        
        # CLIP 분석기 초기화
        clip_analyzer = CLIPAnalyzer()
        
        # 1. 주요 장면 추출
        scenes = analyze_text_for_scenes(prompt, cut_count)
        scenes = scenes[:cut_count]  # 요청된 컷 수만큼만 사용
        
        # 2. 각 장면에 대한 상세 설명 생성
        detailed_scenes = []
        generated_images = []  # 생성된 이미지 URL 저장 리스트
        
        for scene in scenes:
            detailed_description = create_detailed_scene_description(
                scene, style, composition, mood
            )
            # CLIP을 사용한 프롬프트 개선
            enhanced_description = clip_analyzer.enhance_prompt(
                detailed_description, style, mood
            )
            detailed_scenes.append(enhanced_description)
        
        # 3. 최종 프롬프트 구성 및 이미지 생성
        final_prompts = []
        for i, desc in enumerate(detailed_scenes):
            final_prompt = construct_webtoon_prompt(
                scene=desc,
                composition=composition,
                character_desc=character_desc,
                mood=mood,
                style=style
            )
            final_prompts.append(final_prompt)
            
            # 이미지 생성 - 수정된 부분: composition 파라미터 제거
            image_url, revised_prompt, created_seed = generate_image_from_text(
                prompt=final_prompt,
                style=style,
                aspect_ratio="1:1",  # 기본값 설정
                negative_prompt=None  # 필요한 경우 negative_prompt 추가
            )
            
            if image_url:
                # CLIP으로 이미지 검증
                quality_check = clip_analyzer.validate_image(image_url, prompt)
                
                if quality_check and quality_check["similarity_score"] >= 0.7:
                    generated_images.append(image_url)
                    st.success(f"컷 {i} 생성 성공 (유사도: {quality_check['similarity_score']:.2f})")
                    st.image(image_url, caption=f"컷 {i} (유사도: {quality_check['similarity_score']:.2f})")
                else:
                    st.warning(f"컷 {i}의 품질이 기준에 미치지 못합니다. (유사도 70% 이상 필요)")
                    if quality_check and quality_check["suggestions"]:
                        st.info("\n".join(quality_check["suggestions"]))
            else:
                st.error(f"컷 {i} 생성에 실패했습니다.")
        
        return final_prompts, generated_images
        
    except Exception as e:
        logging.error(f"Error in generate_visual_sequence: {str(e)}")
        st.error(f"이미지 생성 중 오류 발생: {str(e)}")
        raise
        
#이미지에 설명 추가 ( 그니까 컷 밑에, 이미지에 대한 요약 or 장면 설명)
# 이 부분은 앞으로 계속 수정할 부분.

def summarize_scene(prompt):
    """
    장면 프롬프트를 간단한 설명으로 요약합니다.
    """
    global client
    try:
        print("Starting scene summarization...")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "주어진 장면 설명을 2-3문장으로 간단히 요약해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        print("Scene summarization successful")
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in summarize_scene:")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        logging.error(f"장면 요약 생성 중 오류 발생: {str(e)}")
        return prompt.split('\n')[0]  # 첫 줄만 반환