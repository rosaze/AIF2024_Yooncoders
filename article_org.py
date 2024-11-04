import openai
import os
from dotenv import load_dotenv

# .env 파일에서 API 키 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_news_info(title, content):
    """
    뉴스 기사의 전체 내용을 사용하여 핵심 정보를 추출합니다.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Extract key information from the news article and format it as bullet points."},
                {"role": "user", "content": f"Title: {title}\nContent: {content}"}
            ],
            max_tokens=500  # 더 많은 내용을 포함하기 위해 증가시킴
        )
        if response and response.choices:
            # 응답을 줄바꿈 기준으로 나누어 리스트로 반환
            return response.choices[0].message['content'].strip().split('\n')
        else:
            print("API 호출이 성공했지만, 응답이 비어 있습니다:", response)
            return None
    except Exception as e:
        print(f"API 호출 중 오류 발생: {e}")
        return None

def simplify_terms_dynamically(content, domain_hint="general", simplification_level="basic", extract_keywords=True):
    """
    뉴스 기사에서 복잡한 용어를 간소화하고 주요 키워드를 추출합니다.
    """
    try:
        messages = [
            {"role": "system", "content": "Dynamically detect and simplify complex terms in a news article, and extract main keywords."},
            {"role": "user", "content": f"""
                Content: {content}
                Domain: {domain_hint}
                Simplification Level: {simplification_level}
                Extract Keywords: {extract_keywords}
            """}
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=200  # 충분한 길이로 설정
        )
        if response and response.choices:
            return response.choices[0].message['content'].strip().split('\n')
        else:
            print("API 호출이 성공했지만, 응답이 비어 있습니다:", response)
            return None
    except Exception as e:
        print(f"Error in simplify_terms_dynamically: {e}")
        return None

def generate_webtoon_scenes(extracted_info):
    """
    추출된 정보를 기반으로 최대 4컷 이하의 웹툰 장면을 생성합니다.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "Create a webtoon episode based on the extracted information from a news article. "
                        "The episode should consist of up to 4 distinct scenes. "
                        "Each scene should be labeled as 'Scene 1:', 'Scene 2:', etc., and each scene should capture a key moment in the story. "
                        "Provide concise and clear descriptions for each scene, and ensure that each scene is separate."
                    )
                },
                {"role": "user", "content": f"{extracted_info}"}
            ],
            max_tokens=500
        )
        if response and response.choices:
            # 응답을 줄바꿈 기준으로 나누고 빈 문자열 제거
            scenes = response.choices[0].message['content'].strip().split('\n')
            scenes = [scene.strip() for scene in scenes if scene.strip()]  # 빈 문자열 제거 및 각 장면 트리밍
            
            # "Scene X:" 패턴이 있을 때만 장면별로 나누기
            separated_scenes = []
            current_scene = []
            for line in scenes:
                if line.startswith("Scene"):
                    if current_scene:
                        separated_scenes.append(" ".join(current_scene))
                        current_scene = []
                    current_scene.append(line)
                else:
                    current_scene.append(line)
            if current_scene:
                separated_scenes.append(" ".join(current_scene))

            # 최대 4개의 장면만 반환
            return separated_scenes[:4] if len(separated_scenes) > 4 else separated_scenes
        else:
            print("API 호출이 성공했지만, 응답이 비어 있습니다:", response)
            return None
    except Exception as e:
        print(f"Error in generate_webtoon_scenes: {e}")
        return None
