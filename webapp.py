import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
from dotenv import load_dotenv
from openai import OpenAI
import urllib.request

# .env 파일에서 환경 변수 로드
# load_dotenv()

# OpenAI API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# 세션 상태 초기화
if "page" not in st.session_state:
    st.session_state.page = "template_selection"

if "character_selected" not in st.session_state:
    st.session_state["character_selected"] = None

if "bubble_positions" not in st.session_state:
    st.session_state["bubble_positions"] = {}

if "bubble_texts" not in st.session_state:
    st.session_state["bubble_texts"] = {}

if "cut_count" not in st.session_state:
    st.session_state["cut_count"] = 1

if "selected_images" not in st.session_state:
    st.session_state["selected_images"] = []

if len(st.session_state["selected_images"]) != st.session_state["cut_count"]:
    st.session_state["selected_images"] = [None] * st.session_state["cut_count"]

if "current_cut_index" not in st.session_state:
    st.session_state["current_cut_index"] = 0

def generate_image(prompt):
    try:
        client = openai.OpenAI()
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        return image_url
    except Exception as e:
        st.error(f"이미지 생성 중 오류 발생: {str(e)}")
        return None

def save_image(url, save_path="result.png"):
    try:
        urllib.request.urlretrieve(url, save_path)
        return save_path
    except Exception as e:
        st.error(f"이미지 저장 중 오류 발생: {str(e)}")
        return None

# 페이지 간 이동 함수
def navigate_to(page):
    st.session_state.page = page

# 사이드바 네비게이션
st.sidebar.title("네비게이션")
st.sidebar.button("템플릿 선택", on_click=lambda: navigate_to("template_selection"))
st.sidebar.button("캐릭터 선택", on_click=lambda: navigate_to("character_selection"))
st.sidebar.button("웹툰 생성", on_click=lambda: navigate_to("create_webtoon"))
st.sidebar.button("컷 생성 및 선택", on_click=lambda: navigate_to("select_cuts"))
st.sidebar.button("말풍선 및 텍스트 추가", on_click=lambda: navigate_to("add_bubbles"))
st.sidebar.button("최종 결과", on_click=lambda: navigate_to("final_result"))

# 템플릿 선택 페이지
if st.session_state.page == "template_selection":
    st.title("템플릿 선택")
    template = st.selectbox(
        "웹툰 템플릿을 선택하세요:",
        ["템플릿1 - 기본 스타일", "템플릿2 - 교육 자료 스타일", "템플릿3 - 단순한 웹툰 스타일"]
    )
    st.write(f"선택된 템플릿: {template}")
    st.button("다음", on_click=lambda: navigate_to("character_selection"))

# 캐릭터 선택 페이지
elif st.session_state.page == "character_selection":
    st.title("캐릭터 선택")
    character_selection = st.radio("캐릭터를 선택하시겠습니까?", ("예", "아니오"))
    
    if st.button("다음"):
        st.session_state["character_selected"] = True if character_selection == "예" else False
        navigate_to("create_webtoon")

# 웹툰 생성 페이지
elif st.session_state.page == "create_webtoon":
    st.title("웹툰 생성")
    st.markdown("## 필수 요소 선택")

    auto_elements = {"인물": "학생", "장소": "학교", "시간대": "낮"}
    user_elements = {}

    for key, value in auto_elements.items():
        user_elements[key] = st.text_input(f"{key} (자동 생성):", value)
    
    user_input = st.text_input("프롬프트를 입력하세요:")

    if "을미사변" in user_input:
        st.write("🔍 추천 프롬프트:")
        st.write("1️⃣ 중학교 2학년이 알아들을 수 있는 정도의 스토리보드")
        st.write("2️⃣ 유치원생이 이해할 수 있는 수준으로 구성")
    
    st.session_state["cut_count"] = st.number_input("생성할 컷 수를 입력하세요", min_value=1, step=1, value=3)
    
    st.session_state["selected_images"] = [None] * st.session_state["cut_count"]
    
    st.write(f"컷 {st.session_state['cut_count']}개가 생성될 예정입니다.")
    
    if st.button("다음"):
        st.session_state["current_cut_index"] = 0
        navigate_to("select_cuts")

# 컷 선택 페이지
elif st.session_state.page == "select_cuts":
    st.title(f"컷 {st.session_state['current_cut_index'] + 1} 선택")

    # 실제 이미지 생성 로직 추가
    if st.button("이미지 생성"):
        prompt = f"웹툰 스타일의 {st.session_state['current_cut_index'] + 1}번째 컷"
        image_url = generate_image(prompt)
        if image_url:
            image_path = save_image(image_url, f"cut_{st.session_state['current_cut_index'] + 1}.png")
            if image_path:
                st.session_state["selected_images"][st.session_state["current_cut_index"]] = Image.open(image_path)
                st.success("이미지가 성공적으로 생성되었습니다.")
            else:
                st.error("이미지 저장에 실패했습니다.")
        else:
            st.error("이미지 생성에 실패했습니다.")

    # 선택된 이미지 표시
    selected_image = st.session_state["selected_images"][st.session_state["current_cut_index"]]
    if selected_image:
        st.image(selected_image, caption=f"선택된 컷 {st.session_state['current_cut_index'] + 1} 이미지")

    # 네비게이션: 다음 컷으로 이동 또는 다음 단계로
    if st.session_state["current_cut_index"] < st.session_state["cut_count"] - 1:
        if selected_image and st.button("다음 컷"):
            st.session_state["current_cut_index"] += 1
    else:
        if all(st.session_state["selected_images"]) and st.button("말풍선 추가로 넘어가기"):
            navigate_to("add_bubbles")

# 말풍선 추가 페이지
elif st.session_state.page == "add_bubbles":
    st.title(f"컷 {st.session_state['current_cut_index'] + 1} 말풍선 추가")

    img = st.session_state["selected_images"][st.session_state["current_cut_index"]]
    st.image(img, caption=f"선택된 컷 {st.session_state['current_cut_index'] + 1} 이미지")

    if st.button(f"컷 {st.session_state['current_cut_index'] + 1}에 말풍선 위치 추가"):
        new_position = (50, 50)  # 사용자가 선택한 위치로 대체 필요
        if st.session_state["current_cut_index"] not in st.session_state["bubble_positions"]:
            st.session_state["bubble_positions"][st.session_state["current_cut_index"]] = []
        st.session_state["bubble_positions"][st.session_state["current_cut_index"]].append(new_position)
        st.success(f"컷 {st.session_state['current_cut_index'] + 1}에 말풍선 위치가 추가되었습니다: {new_position}")

    num_bubbles = len(st.session_state["bubble_positions"].get(st.session_state["current_cut_index"], []))
    st.markdown(f"### 컷 {st.session_state['current_cut_index'] + 1} 말풍선 텍스트 입력")

    for j in range(num_bubbles):
        text_input = st.text_input(f"컷 {st.session_state['current_cut_index'] + 1} 말풍선 {j + 1} 텍스트 입력", key=f"text_input_{st.session_state['current_cut_index']}_{j}")
        if st.session_state["current_cut_index"] not in st.session_state["bubble_texts"]:
            st.session_state["bubble_texts"][st.session_state["current_cut_index"]] = []
        if len(st.session_state["bubble_texts"][st.session_state["current_cut_index"]]) <= j:
            st.session_state["bubble_texts"][st.session_state["current_cut_index"]].append(text_input)
        else:
            st.session_state["bubble_texts"][st.session_state["current_cut_index"]][j] = text_input

    if st.session_state["current_cut_index"] < st.session_state["cut_count"] - 1:
        if st.button("다음 컷"):
            st.session_state["current_cut_index"] += 1
    else:
        if st.button("최종 결과로 넘어가기"):
            navigate_to("final_result")

# 최종 결과 페이지
elif st.session_state.page == "final_result":
    st.title("최종 결과")

    for i, img in enumerate(st.session_state["selected_images"]):
        st.markdown(f"### 컷 {i + 1}")
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("NanumGothic.ttf", 24)  # 한글 지원 폰트로 변경
        except IOError:
            st.warning("지정된 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
            font = ImageFont.load_default()

        positions = st.session_state["bubble_positions"].get(i, [])
        texts = st.session_state["bubble_texts"].get(i, [])

        for position, text in zip(positions, texts):
            bubble_width, bubble_height = 150, 80
            draw.ellipse([position, (position[0] + bubble_width, position[1] + bubble_height)], outline="black", width=2)
            draw.text((position[0] + 10, position[1] + 10), text, font=font, fill="black")
        
        st.image(img, caption=f"최종 컷 {i + 1} 이미지", use_column_width=True)

        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        st.download_button(
            label="이미지 다운로드",
            data=img_bytes,
            file_name=f"final_webtoon_cut_{i+1}.png",
            mime="image/png"
        )