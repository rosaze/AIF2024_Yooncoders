import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
# Initialize session state
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

# Initialize selected_images to have the correct size
if "selected_images" not in st.session_state:
    st.session_state["selected_images"] = []

# Ensure the list has the correct number of elements (None initially)
if len(st.session_state["selected_images"]) != st.session_state["cut_count"]:
    st.session_state["selected_images"] = [None] * st.session_state["cut_count"]

if "current_cut_index" not in st.session_state:
    st.session_state["current_cut_index"] = 0

# Function to navigate between pages
def navigate_to(page):
    st.session_state.page = page

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.button("템플릿 선택", on_click=lambda: navigate_to("template_selection"))
st.sidebar.button("캐릭터 선택", on_click=lambda: navigate_to("character_selection"))
st.sidebar.button("웹툰 생성", on_click=lambda: navigate_to("create_webtoon"))
st.sidebar.button("컷 생성 및 선택", on_click=lambda: navigate_to("select_cuts"))
st.sidebar.button("말풍선 및 텍스트 추가", on_click=lambda: navigate_to("add_bubbles"))
st.sidebar.button("최종 결과", on_click=lambda: navigate_to("final_result"))

# Template Selection Page
if st.session_state.page == "template_selection":
    st.title("템플릿 선택")
    template = st.selectbox(
        "웹툰 템플릿을 선택하세요:",
        ["템플렛1 - 기본 스타일", "템플렛2 - 교육 자료 스타일", "템플렛3 - 단순한 웹툰 스타일"]
    )
    st.write(f"선택된 템플릿: {template}")
    st.button("다음", on_click=lambda: navigate_to("character_selection"))

# Character Selection Page
elif st.session_state.page == "character_selection":
    st.title("캐릭터 선택")
    character_selection = st.radio("캐릭터를 선택하시겠습니까?", ("Yes", "No"))
    
    if st.button("다음"):
        st.session_state["character_selected"] = True if character_selection == "Yes" else False
        navigate_to("create_webtoon")

# Webtoon Creation Page
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
    
    # Reinitialize selected_images based on the cut_count
    st.session_state["selected_images"] = [None] * st.session_state["cut_count"]
    
    st.write(f"컷 {st.session_state['cut_count']}개가 생성될 예정입니다.")
    
    if st.button("다음"):
        st.session_state["current_cut_index"] = 0  # Reset to the first cut
        navigate_to("select_cuts")

# Cut Selection Page
elif st.session_state.page == "select_cuts":
    st.title(f"컷 {st.session_state['current_cut_index'] + 1} 선택")

    col1, col2 = st.columns(2)

    with col1:
        img1 = Image.new("RGB", (200, 150), color=(255, 200, 200))
        if st.button(f"컷 {st.session_state['current_cut_index'] + 1} 이미지 1 선택", key=f"cut_{st.session_state['current_cut_index']}_1"):
            st.session_state["selected_images"][st.session_state["current_cut_index"]] = img1

    with col2:
        img2 = Image.new("RGB", (200, 150), color=(200, 255, 200))
        if st.button(f"컷 {st.session_state['current_cut_index'] + 1} 이미지 2 선택", key=f"cut_{st.session_state['current_cut_index']}_2"):
            st.session_state["selected_images"][st.session_state["current_cut_index"]] = img2
    
    # Display the selected image
    selected_image = st.session_state["selected_images"][st.session_state["current_cut_index"]]
    if selected_image:
        st.image(selected_image, caption=f"선택된 컷 {st.session_state['current_cut_index'] + 1} 이미지")

    # Navigation: Move to the next cut or next phase
    if st.session_state["current_cut_index"] < st.session_state["cut_count"] - 1:
        if selected_image and st.button("다음 컷"):
            st.session_state["current_cut_index"] += 1
    else:
        if all(st.session_state["selected_images"]) and st.button("말풍선 추가로 넘어가기"):
            navigate_to("add_bubbles")


# Add Speech Bubbles Page
elif st.session_state.page == "add_bubbles":
    st.title(f"컷 {st.session_state['current_cut_index'] + 1} 말풍선 추가")

    img = st.session_state["selected_images"][st.session_state["current_cut_index"]]
    st.image(img, caption=f"선택된 컷 {st.session_state['current_cut_index'] + 1} 이미지")

    if st.button(f"컷 {st.session_state['current_cut_index'] + 1}에 말풍선 위치 추가"):
        new_position = (50, 50)  # Placeholder for user-selected position
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
        if len(st.session_state["bubble_texts"][st.session_state["current_cut_index"]]) < num_bubbles:
            st.session_state["bubble_texts"][st.session_state["current_cut_index"]].append(text_input)
        else:
            st.session_state["bubble_texts"][st.session_state["current_cut_index"]][j] = text_input

    if st.session_state["current_cut_index"] < st.session_state["cut_count"] - 1:
        if st.button("다음 컷"):
            st.session_state["current_cut_index"] += 1
    else:
        if st.button("최종 결과로 넘어가기"):
            navigate_to("final_result")
# Final Result Page
if st.session_state.page == "final_result":
    st.title("최종 결과")

    for i, img in enumerate(st.session_state["selected_images"]):
        st.markdown(f"### 컷 {i + 1}")
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("malgun.ttf", 24)  # Windows example with a font supporting Korean
        except IOError:
            font = ImageFont.load_default()

        positions = st.session_state["bubble_positions"].get(i, [])
        texts = st.session_state["bubble_texts"].get(i, [])

        for position, text in zip(positions, texts):
            bubble_width, bubble_height = 150, 80
            draw.ellipse([position, (position[0] + bubble_width, position[1] + bubble_height)], outline="black", width=2)
            draw.text((position[0] + 10, position[1] + 10), text, font=font, fill="black")
        
        # Display the final image
        st.image(img, caption=f"최종 컷 {i + 1} 이미지", use_column_width=True)

        # Save the image to a BytesIO object and provide a download link
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)  # Move the pointer to the start of the stream

        # Provide a download button
        st.download_button(
            label="이미지 다운로드",
            data=img_bytes,
            file_name=f"final_webtoon_cut_{i+1}.png",
            mime="image/png"
        )