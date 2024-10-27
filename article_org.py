import openai
import os
from dotenv import load_dotenv

# .env 파일에서 API 키 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def extract_news_info(title, content):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            # 현재 gpt 버전에서는 messages 필수 
            messages=[
                {"role": "system", "content": "Extract key information from the news article."},
                {"role": "user", "content": f"Title: {title}\nContent: {content}"}
            ],
            max_tokens=100
        )
        if response and response.choices:
            return response.choices[0].message['content'].strip()
        else:
            print("API 호출이 성공했지만, 응답이 비어 있습니다:", response)
            return None
    except Exception as e:
        print(f"API 호출 중 오류 발생: {e}")
        return None

def simplify_terms_dynamically(content, domain_hint="general", simplification_level="basic", extract_keywords=True):
    try:
        messages = [
            {"role": "system", "content": "Dynamically detect and simplify complex or domain-specific terms in a news article, and extract main keywords."},
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
            max_tokens=150
        )
        if response and response.choices:
            return response.choices[0].message['content'].strip()
        else:
            print("API 호출이 성공했지만, 응답이 비어 있습니다:", response)
            return None
    except Exception as e:
        print(f"Error in simplify_terms_dynamically: {e}")
        return None

def generate_webtoon_scenes(extracted_info):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Generate a webtoon episode based on the extracted news information."},
                {"role": "user", "content": f"{extracted_info}"}
            ],
            max_tokens=200
        )
        if response and response.choices:
            return response.choices[0].message['content'].strip()
        else:
            print("API 호출이 성공했지만, 응답이 비어 있습니다:", response)
            return None
    except Exception as e:
        print(f"Error in generate_webtoon_scenes: {e}")
        return None
