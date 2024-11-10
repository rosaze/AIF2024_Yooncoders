from openai import OpenAI
import os
from dotenv import load_dotenv
import requests
import logging
from PIL import Image
import io
# .env 파일 로드
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_image(prompt, style, negative_prompt):
    """DALL-E를 이용하여 이미지 생성"""
    try:
        # OpenAI 이미지 생성 요청
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="hd",
            n=1
        )
        
        # URL 반환
        return response.data[0].url
        
    except Exception as e:
        logging.error(f"이미지 생성 실패: {str(e)}")
        raise RuntimeError(f"이미지 생성 실패: {str(e)}")

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
    
def generate_image_from_text(prompt, style="minimalist", aspect_ratio="1:1", negative_prompt=None, retries=2):
    """
     DALL-E API를 통해 이미지를 생성합니다.
    
    Args:
        prompt (str): 상세 프롬프트
        style (str): 이미지 스타일
        aspect_ratio (str): 이미지 비율 ("1:1", "16:9", "9:16")
        negative_prompt (str): 부정적 프롬프트
        retries (int): 재시도 횟수
        
    Returns:
        tuple: (image_url, revised_prompt, created_seed)
    """
    size = "1024x1024" if aspect_ratio == "1:1" else "1792x1024" if aspect_ratio == "16:9" else "1024x1792"
    
    # 최종 프롬프트 구성
    full_prompt = prompt  # construct_webtoon_prompt에서 이미 스타일 정보가 포함됨
    if negative_prompt:
        full_prompt += f"\nNegative prompt: {negative_prompt}"
    
    logging.info(f"최종 프롬프트:\n{full_prompt}")  # 디버깅용
    
    # 이 부분이 retry
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
def download_and_display_image(image_url, filename=None):
    """
    이미지 URL을 받아 Streamlit에 표시할 수 있는 형태로 반환
    """
    try:
        logging.info(f"이미지 다운로드 시작: {image_url}")
        response = requests.get(image_url)
        if response.status_code == 200:
            # 바이트 스트림으로부터 이미지 생성
            image = Image.open(io.BytesIO(response.content))
            logging.info("이미지 생성 성공")
            return image
        else:
            logging.error(f"이미지 다운로드 실패: HTTP {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"이미지 처리 중 오류 발생: {str(e)}")
        return None


