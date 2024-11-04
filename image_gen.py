import openai
import os
from dotenv import load_dotenv
import requests

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
