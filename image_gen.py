import openai
import os
from dotenv import load_dotenv
import requests
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
# .env 파일 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_image(prompt, style="webtoon", negative_prompt="low quality, blurry"):
    """DALL-E를 이용하여 이미지 생성"""
    # 프롬프트를 스타일에 맞게 최종적으로 구성합니다.
    full_prompt = f"{style} style, {prompt}. Negative prompt: {negative_prompt}."

    try:
        response = openai.Image.create(
            prompt=full_prompt,
            n=1,
            size="1024x1024"
        )
        image_url = response['data'][0]['url']
        return image_url
    except Exception as e:
        print(f"이미지 생성 중 오류 발생: {str(e)}")
        return None

def save_image(image_url, filename):
    """이미지를 URL에서 다운로드하여 로컬에 저장"""
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
        print(f"이미지 저장 중 오류 발생: {str(e)}")
        return None
# DALL-E 이미지 생성 함수
def generate_image_from_text(prompt, style="minimalist", aspect_ratio="1:1", retries=3):
    """
    DALL-E API를 통해 이미지를 생성합니다.
    prompt: 사용자 정의 프롬프트
    style: 사용자 정의 스타일
    aspect_ratio: 이미지의 가로 세로 비율 ("1:1", "16:9", "9:16")
    retries: 재시도 횟수
    """
    size = "1024x1024" if aspect_ratio == "1:1" else "1792x1024" if aspect_ratio == "16:9" else "1024x1792"
    
    for _ in range(retries):
        try:
            response = openai.Image.create(
                model="dall-e-3",
                prompt=f"{prompt}, in style of {style}",
                size=size,
                n=1,
                quality="hd"
            )
            # 응답에서 이미지 URL과 수정된 프롬프트 가져오기
            image_url = response['data'][0]['url']
            revised_prompt = response['data'][0].get('revised_prompt', prompt)
            created_seed = response['created']  # 생성 시점의 seed
            return image_url, revised_prompt, created_seed
        except Exception as e:
            print(f"Error generating image: {e}")
            continue
    return None, None, None

# 이미지 다운로드 및 표시 함수
def download_and_display_image(image_url, filename="generated_image.png"):
    """
    이미지 URL을 받아 다운로드 후 로컬에 저장하고 출력합니다.
    image_url: DALL-E API에서 반환한 이미지 URL
    filename: 저장할 이미지 파일 이름
    """
    response = requests.get(image_url)
    with open(filename, 'wb') as file:
        file.write(response.content)

    # 이미지 파일을 로드하고 출력
    img = mpimg.imread(filename)
    plt.imshow(img)
    plt.axis('off')
    plt.show()