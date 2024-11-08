from openai import OpenAI
import os
from dotenv import load_dotenv
import requests
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
# .env 파일 로드
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_image(prompt, style, negative_prompt):
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
def generate_image_from_text(prompt, style="minimalist", aspect_ratio="1:1", negative_prompt=None, retries=3):
    """
    DALL-E API를 통해 이미지를 생성합니다.
    prompt: construct_webtoon_prompt에서 생성된 상세 프롬프트
    style: 사용자가 선택한 스타일
    negative_prompt: 부정적 프롬프트
    """
    size = "1024x1024" if aspect_ratio == "1:1" else "1792x1024" if aspect_ratio == "16:9" else "1024x1792"
    
    # 최종 프롬프트 구성
    full_prompt = prompt  # construct_webtoon_prompt에서 이미 스타일 정보가 포함됨
    if negative_prompt:
        full_prompt += f"\nNegative prompt: {negative_prompt}"
    
    print(f"최종 프롬프트: {full_prompt}")  # 디버깅용
    
    for _ in range(retries):
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                size=size,
                n=1,
                quality="hd"
            )
            
            image_url = response.data[0].url
            revised_prompt = getattr(response.data[0], 'revised_prompt', full_prompt)
            created_seed = getattr(response, 'created', None)
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