import os
import json
from datetime import datetime
import shutil
from PIL import Image
import requests
from io import BytesIO

def save_session(config: dict, images: dict, save_dir: str = "saved_sessions") -> str:
    """
    세션 정보와 이미지들을 저장하는 함수
    
    Args:
        config (dict): 설정 정보 (프롬프트, 스타일, 구도 등)
        images (dict): 생성된 이미지 URL들의 딕셔너리
        save_dir (str): 저장할 기본 디렉토리
    
    Returns:
        str: 저장된 세션 디렉토리 경로
    """
    # 타임스탬프로 세션 폴더 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(save_dir, f"session_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)
    
    # 설정 정보를 JSON 파일로 저장
    config['timestamp'] = timestamp
    config_path = os.path.join(session_dir, "config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    # 이미지 저장
    images_dir = os.path.join(session_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    saved_images = {}
    for idx, image_url in images.items():
        try:
            # URL에서 이미지 다운로드
            response = requests.get(image_url)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                image_path = os.path.join(images_dir, f"image_{idx}.png")
                image.save(image_path)
                saved_images[idx] = image_path
        except Exception as e:
            print(f"이미지 {idx} 저장 중 오류 발생: {str(e)}")
    
    # 저장된 이미지 정보를 JSON에 추가
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    config_data['saved_images'] = saved_images
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    return session_dir

def load_session(session_dir: str) -> tuple:
    """
    저장된 세션을 불러오는 함수
    
    Args:
        session_dir (str): 세션 디렉토리 경로
    
    Returns:
        tuple: (설정 정보, 이미지 경로들)
    """
    try:
        # 설정 정보 로드
        config_path = os.path.join(session_dir, "config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 이미지 경로들 반환
        images = config.get('saved_images', {})
        return config, images
    except Exception as e:
        print(f"세션 로드 중 오류 발생: {str(e)}")
        return None, None

def list_saved_sessions(save_dir: str = "saved_sessions") -> list:
    """저장된 세션 목록 반환"""
    if not os.path.exists(save_dir):
        return []
    
    sessions = []
    for session_name in os.listdir(save_dir):
        session_path = os.path.join(save_dir, session_name)
        config_path = os.path.join(session_path, "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                sessions.append({
                    'name': session_name,
                    'path': session_path,
                    'timestamp': config.get('timestamp', ''),
                    'type': config.get('type', ''),
                    'title': config.get('title', '')
                })
    
    return sorted(sessions, key=lambda x: x['timestamp'], reverse=True)