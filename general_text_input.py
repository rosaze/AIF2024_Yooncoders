import streamlit as st
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from PIL import Image
import logging
from openai import OpenAI
import torch
from io import BytesIO
import PyPDF2
from clip_analyzer import CLIPAnalyzer
from docx import Document
from image_gen import generate_image_from_text
from save_utils import save_session
@dataclass
class SceneConfig:
    style: str
    composition: str
    mood: str
    character_desc: str
    aspect_ratio: str

class TextToWebtoonConverter:
    def __init__(self, openai_client: OpenAI, clip_analyzer):
        self.client = openai_client
        self.clip_analyzer = clip_analyzer
        self.setup_logging()
        self.style_guides = {
            "미니멀리스트": {
                "prompt": "minimal details, simple lines, clean composition, essential elements only",
                "emphasis": "Focus on simplicity and negative space"
            },
            "픽토그램": {
                "prompt": "pictogram style,symbolic representation, simplified shapes, icon-like style",
                "emphasis": "Clear silhouettes and symbolic elements"
            },
            "카툰": {
                "prompt": "animated style, exaggerated features, bold colors",
                "emphasis": "Expressive and dynamic elements"
            },
            "웹툰": {
                "prompt": "webtoon style, manhwa art style, clean lines, vibrant colors",
                "emphasis": "Dramatic angles and clear storytelling"
            },
            "예술적": {
                "prompt": "painterly style, artistic interpretation, creative composition",
                "emphasis": "Atmospheric and textural details"
            }
        }
        
        self.mood_guides = {
            "일상적": {
                "prompt": "natural lighting, soft colors, everyday atmosphere",
                "lighting": "warm, natural daylight",
                "color": "neutral, balanced palette"
            },
            "긴장된": {
                "prompt": "dramatic lighting, high contrast, intense atmosphere",
                "lighting": "harsh shadows, dramatic highlights",
                "color": "high contrast, intense tones"
            },
            "진지한": {
                "prompt": "subdued lighting, serious atmosphere, formal composition",
                "lighting": "soft, directional light",
                "color": "muted, serious tones"
            },
            "따뜻한": {
                "prompt": "warm colors, soft lighting, comfortable atmosphere",
                "lighting": "golden hour, soft glow",
                "color": "warm, inviting palette"
            },
            "즐거운": {
                "prompt": "bright lighting, warm colors, dynamic composition",
                "lighting": "bright, cheerful",
                "color": "vibrant, playful colors"
            }
        }
        
        self.composition_guides = {
            "배경과 인물": "balanced composition of character and background, eye-level shot",
            "근접 샷": "close-up shot, focused on character's expression",
            "대화형": "two-shot composition, characters facing each other",
            "풍경 위주": "wide shot, emphasis on background scenery",
            "일반": "standard view, balanced composition"
        }
         # 부정적 조건을 클래스 속성으로 정의
        self.negative_elements = (
            "blurry images, distorted faces, text in image, unrealistic proportions, "
            "extra limbs, overly complicated backgrounds, too much characters,excessive details,poor lighting, bad anatomy, "
            "abstract images, cut-off elements"
        )

    @staticmethod
    def setup_logging():
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    @staticmethod
    def read_file_content(uploaded_file):
        """다양한 형식의 파일 읽기"""
        try:
            file_extension = uploaded_file.name.split('.')[-1].lower()
        
            if file_extension == 'txt':
                bytes_data = uploaded_file.getvalue()
                encoding = 'utf-8'
                try:
                    return bytes_data.decode(encoding)
                except UnicodeDecodeError:
                    return bytes_data.decode('cp949')
            
            elif file_extension == 'pdf':
                pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.getvalue()))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
            
            elif file_extension in ['docx', 'doc']:
                doc = Document(BytesIO(uploaded_file.getvalue()))
                return "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
            else:
                return None
            
        except Exception as e:
            st.error(f"파일 읽기 오류: {str(e)}")
            return None

    def analyze_text(self, text: str, cut_count: int) -> List[str]:
        """텍스트를 분석하여 주요 장면들을 추출"""
        try:
            system_prompt = """웹툰 작가의 관점으로 다음 기준에 따라 장면을 선택하세요:
            1. 시각적 임팩트가 강한 순간
            2. 캐릭터의 감정이 극대화되는 장면
            3. 스토리의 전환점이 되는 순간
            4. 독자의 몰입도를 높일 수 있는 구도가 가능한 장면
            5. 연속된 컷의 흐름이 자연스러운 장면들"""
            
            user_prompt = f"""다음 텍스트에서 웹툰화하기 가장 적합한 {cut_count}개의 장면을 선택하세요.
            각 장면은 다음 요소를 포함해야 합니다:
            - 구체적인 공간감과 배경 묘사
            - 캐릭터의 동작과 표정
            - 조명과 분위기
            - 시각적 포인트가 될 요소
            - 앞뒤 장면과의 연결성
            
            텍스트:
            {text}"""
             # 메시지 데이터
            messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
            st.subheader("🔍 GPT 요청 메시지")
            st.text_area("Request Messages", value=f"{messages}", height=200)
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7
            )
            
            scenes = response.choices[0].message.content.strip().split("\n\n")
            return scenes[:cut_count]
            
        except Exception as e:
            logging.error(f"Scene analysis failed: {str(e)}")
            raise

    def analyze_story_by_cuts(self, text: str, cut_count: int) -> Dict[str, str]:
        """컷 수에 따른 스토리 분석"""
        try:
            scene_types = {
                1: ["핵심 장면"],
                2: ["도입부", "절정"],
                3: ["시작", "전개", "결말"],
                4: ["기(起)", "승(承)", "전(轉)", "결(結)"]
            }
            
            prompt = f"""다음 이야기를 {cut_count}개의 핵심 장면으로 나누어 분석해주세요.
            각 장면은 다음 구조에 맞춰 선택해주세요:
            {scene_types[cut_count]}
            
            각 장면은 다음 요소를 포함해야 합니다:
            - 구체적인 공간감과 배경 묘사
            - 캐릭터의 동작과 표정
            - 조명과 분위기
            - 시각적 포인트
            - 앞뒤 장면과의 연결성

            텍스트:
            {text}"""
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            scenes = {}
            raw_scenes = response.choices[0].message.content.strip().split("\n\n")
            
            for scene_type, scene in zip(scene_types[cut_count], raw_scenes):
                scenes[scene_type] = scene
            
            return scenes
            
        except Exception as e:
            logging.error(f"Scene analysis failed: {str(e)}")
            raise

    @staticmethod
    def get_image_size(aspect_ratio: str) -> str:
        """이미지 크기 결정"""
        sizes = {
            "1:1": "1024x1024",
            "16:9": "1792x1024",
            "9:16": "1024x1792"
        }
        return sizes.get(aspect_ratio, "1024x1024")
    def create_scene_description(self, scene: str, config: SceneConfig) -> str:
    ###"""장면별 상세 시각적 설명 생성"""
        try:
            style_guide = self.style_guides[config.style]
            mood_guide = self.mood_guides[config.mood]
        
            prompt = f"""웹툰 작화 지침:
            장면: {scene}
        
            스타일 요구사항:
            {style_guide['prompt']}
            {style_guide['emphasis']}
        
            분위기 요구사항:
            {mood_guide['prompt']}
            조명: {mood_guide['lighting']}
            색감: {mood_guide['color']}
        
            구도: {self.composition_guides[config.composition]}
            캐릭터 특징: {config.character_desc if config.character_desc else '특별한 지정 없음'}
        
            다음 요소들을 상세히 설명해주세요:
            1. 화면 구도와 시점
            2. 캐릭터의 위치, 포즈, 표정
            3. 배경의 깊이감과 디테일
            4. 조명과 그림자의 처리
            5. 감정을 강조하는 시각적 요소"""

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
        
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Scene description creation failed: {str(e)}")
            raise


    def generate_image(self, description: str, config: SceneConfig) -> str:
        # 최대 시도 횟수 제한
        max_attempts = 3  
        min_acceptable_score = 0.6  # 최소 허용 점수

        for attempt in range(max_attempts):
            try:
                style_guide = self.style_guides[config.style]
                mood_guide = self.mood_guides[config.mood]
                
                final_prompt = f"""{description}
                Visual style: {style_guide['prompt']}
                Mood: {mood_guide['prompt']}
                Lighting: {mood_guide['lighting']}
                Color: {mood_guide['color']}"""

                # 부정적 프롬프트
                negative_prompt = """
                추상적인 이미지, 흐릿한 이미지, 낮은 품질, 비현실적인 비율, 
                왜곡된 얼굴, 추가 사지, 이미지 안 텍스트, 말풍선, 5명 이상의 인물, 국기 또는 나라, 
                잘린 이미지, 과도한 필터, 비문법적 구조, 중복된 특징, 
                나쁜 해부학, 나쁜 손, 과도하게 복잡한 배경
                """

                # image_gen.py의 함수 사용
                image_url, revised_prompt, created_seed = generate_image_from_text(
                    prompt=final_prompt,
                    style=config.style,
                    aspect_ratio=config.aspect_ratio,
                    negative_prompt=negative_prompt
                )
                
                if image_url:
                    quality_check = self.clip_analyzer.validate_image(
                        image_url, 
                        description,
                        return_score=True
                    )
                    
                    score = quality_check.get("similarity_score", 0.0)
                    self._record_attempt(attempt, image_url, score)
                    
                    # 점수에 따른 조건부 수락
                    if score >= 0.7:  # target_score_threshold
                        logging.info(f"이상적인 이미지 생성 (점수: {score})")
                        return image_url
                    elif score >= min_acceptable_score and attempt >= 1:
                        logging.info(f"적정 수준의 이미지 생성 (점수: {score})")
                        return image_url
                    
                    # 프롬프트 개선은 1회만 시도
                    if attempt == 0 and score < min_acceptable_score:
                        description = self._enhance_prompt_with_missing_elements(
                            description,
                            quality_check.get("missing_elements", [])
                        )
                        logging.info("프롬프트 개선 시도")
                    
            except Exception as e:
                logging.error(f"이미지 생성 시도 {attempt + 1} 실패: {str(e)}")
                if attempt == max_attempts - 1:
                    best_result = self._get_best_attempt()
                    if best_result:
                        return best_result
                    
        return None

    def _record_attempt(self, attempt_num: int, image_url: str, score: float):
        """각 시도의 결과를 기록"""
        if not hasattr(self, '_generation_attempts'):
            self._generation_attempts = []
        
        self._generation_attempts.append({
            'attempt': attempt_num,
            'image_url': image_url,
            'score': score,
            'timestamp': datetime.now()
        })

    def _get_best_attempt(self) -> str:
        """지금까지의 시도 중 최상의 결과 반환"""
        if not hasattr(self, '_generation_attempts') or not self._generation_attempts:
            return None
            
        best_attempt = max(self._generation_attempts, key=lambda x: x['score'])
        logging.info(f"최선의 시도 선택 (점수: {best_attempt['score']})")
        return best_attempt['image_url']

    def _enhance_prompt_with_missing_elements(self, original_prompt: str, missing_elements: list) -> str:
        """프롬프트 개선"""
        try:
            enhancement = f"""
            필수 포함 요소:
            - 캐릭터 특징: {', '.join(missing_elements) if missing_elements else '기존 유지'}
            - 스토리 상황: {original_prompt}
            
            위 요소들을 자연스럽게 통합하여 더 구체적으로 수정해주세요.
            특히 캐릭터의 행동과 감정 표현에 중점을 두어주세요.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # 빠른 응답을 위해 GPT-3.5 사용
                messages=[
                    {"role": "system", "content": enhancement},
                    {"role": "user", "content": original_prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            enhanced_prompt = response.choices[0].message.content.strip()
            logging.info("프롬프트 개선 완료")
            return enhanced_prompt
            
        except Exception as e:
            logging.error(f"프롬프트 개선 실패: {str(e)}")
            return original_prompt

    def summarize_scene(self, description: str) -> str:
        """
       장면 설명 요약 - 원본 텍스트의 맥락을 유지하면서 사용자 이해를 돕는 설명 생성
    
    Args:
        description (str): 현재 장면 설명
        original_text (str): 사용자가 입력한 원본 텍스트
        scene_index (int): 현재 장면 인덱스
    Returns:
        str: 맥락이 유지된 요약 설명
        """
        try:
            # 구체적이고 상황 중심의 요약을 요청하는 프롬프트
            prompt = """다음 내용을 바탕으로 현재 장면에 대한 설명을 만들어주세요.
원본 텍스트:
{original_text}

현재 장면 설명:
{description}
요구사항:
1. 원본 텍스트의 내용과 표현을 최대한 유지할 것
2. 현재 장면에 해당하는 부분을 중심으로 설명할 것
3. 이야기의 흐름이 자연스럽게 이어지도록 할 것
4. 기술적인 설명이나 시각적 묘사는 최소화할 것
5. 실제 스토리텔링에 중점을 둘 것
6. 150자 이내로 작성할 것
예시:
❌ "위에서 내려다보는 구도로, 왼쪽에는 개미들이 오른쪽에는 베짱이가 위치해 있다"
⭕ "무더운 여름날, 주인공이 무엇을 하는데 무엇이 발생했다. "
⭕"주인공은 어떠한 상황에 있다"

장면 번호: {scene_index + 1}"""
        
            # GPT 모델 호출
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                {"role": "system", "content": "당신은 사용자의 원본 텍스트를 기반으로 자연스러운 스토리텔링을 하는 작가입니다."},
                {"role": "user", "content": prompt}
                ],
                temperature=0.5,  # 더 일관성 있는 결과를 위해 낮은 temperature 사용
                max_tokens=200
            )
        
            # GPT 응답 처리
            summary = response.choices[0].message.content.strip()
            # 100자로 제한
            if len(summary) > 150:
            # 마지막 마침표 위치 찾기
                last_period = summary[:150].rfind('.')
                if last_period != -1:
                    summary = summary[:last_period + 1]
                else:
                # 마침표가 없는 경우 150자에서 자르고 마침표 추가
                    summary = summary[:150] + '.'

        except Exception as e:
            logging.error(f"Scene summarization failed: {str(e)}")
            return description[:150] + ('...' if len(description) > 150 else '')
        return summary


    def render_ui(self):
        st.title("스토리 텍스트 시각화하기")
         # UI 가이드 expander 추가
        with st.sidebar.expander("📌 인터페이스 가이드", expanded=True):
            st.markdown("""
        ### 🎨 스타일 설정
        - **미니멀리스트**: 단순하고 깔끔한 디자인
        - **픽토그램**: 상징적인 아이콘 스타일
        - **카툰**: 과장되고 생동감 있는 표현
        - **웹툰**: 한국식 만화 스타일
        - **예술적**: 회화적이고 창의적인 표현
        
        ### 🌈 분위기 선택
        - **일상적**: 자연스럽고 편안한 톤
        - **긴장된**: 극적이고 강렬한 분위기
        - **진지한**: 무게감 있는 표현
        - **따뜻한**: 포근하고 긍정적인 감성
        - **즐거운**: 밝고 경쾌한 분위기
        
        ### 📐 구도 설정
        - **배경과 인물**: 전체적인 장면 구성
        - **근접 샷**: 감정과 표정 강조
        - **대화형**: 캐릭터 간 상호작용
        - **풍경 위주**: 배경 중심 연출
        - **일반**: 기본적인 구도
        """)
        
        st.info("""
        💡 **활용 팁**
        - 스토리의 분위기에 맞는 스타일을 선택하세요
        - 장면의 감정을 잘 표현할 수 있는 분위기를 고르세요
        - 상황에 적합한 구도로 설정하면 더 효과적입니다
        """)

    
    # 세션 상태 초기화
        if 'generated_images' not in st.session_state:
            st.session_state.generated_images = {}
            st.session_state.current_config = None
            st.session_state.current_text = None
            st.session_state.scene_descriptions = []
    
        input_method = st.radio(
        "입력 방식을 선택하세요",
        ["직접 입력", "파일 업로드"],
        horizontal=True
        )
    
        with st.form("story_input_form"):
            text_content = None
            if input_method == "직접 입력":
                text_content = st.text_area(
                    "스토리 입력",
                    placeholder="소설, 시나리오, 또는 자유로운 이야기를 입력해주세요.",
                    height=200
                )
            else:
                uploaded_file = st.file_uploader(
                    "파일 업로드",
                    type=['txt', 'pdf', 'docx', 'doc'],
                    help="지원 형식: TXT, PDF, DOCX"
                )
            
                if uploaded_file:
                    text_content = self.read_file_content(uploaded_file)
                    if text_content:
                        st.success("파일 업로드 성공!")
                        with st.expander("파일 내용 확인"):
                            st.text(text_content[:500] + "..." if len(text_content) > 500 else text_content)
                
            col1, col2 = st.columns(2)
            with col1:
                style = st.select_slider(
                    "스타일 선택",
                    options=["미니멀리스트", "픽토그램", "카툰", "웹툰", "예술적"],
                    value="웹툰"
                )
            
                mood = st.selectbox(
                    "분위기",
                    ["일상적", "긴장된", "진지한", "따뜻한", "즐거운"]
                )   
            
                composition = st.selectbox(
                    "구도",
                    ["배경과 인물", "근접 샷", "대화형", "풍경 위주", "일반"]
                )
        
            with col2:
                character_desc = st.text_input(
                    "캐릭터 설명 (선택사항)",
                 placeholder="주요 캐릭터의 특징을 입력해주세요"
                )
            
                cut_count = st.radio(
                "생성할 컷 수",
                options=[1, 2, 3, 4],
                horizontal=True
                )
            
                aspect_ratio = st.selectbox(
                "이미지 비율",
                ["정사각형 (1:1)", "와이드 (16:9)", "세로형 (9:16)"]
                )
        
            submit = st.form_submit_button("✨웹툰 생성 시작")
        
            if submit and text_content:
            # aspect ratio 값 변환
                ratio_map = {
                "정사각형 (1:1)": "1:1",
                "와이드 (16:9)": "16:9",
                "세로형 (9:16)": "9:16"
                }
            
                config = SceneConfig(
                    style=style,
                    composition=composition,
                    mood=mood,
                    character_desc=character_desc,
                    aspect_ratio=ratio_map.get(aspect_ratio, "1:1")
                )
            
                # 세션 상태에 현재 설정 저장
                st.session_state.current_config = config
                st.session_state.current_text = text_content
                self.process_submission(text_content, config, cut_count)

        # form 바깥에서 저장 버튼 처리
        if st.session_state.generated_images:
            if st.button("💾 이번 과정 저장하기"):
                save_config = {
                    'type': 'story',
                    'title': st.session_state.current_text[:100],
                    'text': st.session_state.current_text,
                    'style': st.session_state.current_config.style,
                    'composition': st.session_state.current_config.composition,
                    'mood': st.session_state.current_config.mood,
                    'character_desc': st.session_state.current_config.character_desc,
                    'aspect_ratio': st.session_state.current_config.aspect_ratio,
                    'scene_descriptions': st.session_state.scene_descriptions
                }
                session_dir = save_session(save_config, st.session_state.generated_images)
                st.success(f"✅ 성공적으로 저장되었습니다! 저장 위치: {session_dir}")

    
    # process_submission 메소드 내의 이미지 생성 부분을 다음과 같이 수정

    def process_submission(self, text: str, config: SceneConfig, cut_count: int):
        try:
            progress_bar = st.progress(0)
            status = st.empty()
        
            # 로그 저장을 위한 세션 데이터 초기화
            if 'generation_logs' not in st.session_state:
                st.session_state.generation_logs = []
        
            # 분석 시작 시간 기록
            start_time = datetime.now()
        
            # CLIP 분석기 정보 표시
            st.sidebar.markdown("### 🔍 CLIP 분석기 정보")
            st.sidebar.info(f"디바이스: {self.clip_analyzer.device}")
            st.sidebar.info(f"모델: openai/clip-vit-base-patch32")
        
            status.info("📖 스토리 구조 분석 중...")
            scenes = self.analyze_story_by_cuts(text, cut_count)
        
            generated_images = {}
            scene_descriptions = []
        
            # 생성 메트릭 저장용 딕셔너리
            generation_metrics = {
                'total_time': 0,
                'avg_clip_score': 0,
                'scores': [],
                'generation_attempts': []
            }
        
            cols_per_row = min(cut_count, 2)
            rows_needed = (cut_count + 1) // 2
        
            for row in range(rows_needed):
                cols = st.columns(cols_per_row)
                start_idx = row * cols_per_row
                end_idx = min(start_idx + cols_per_row, cut_count)
            
                for i in range(start_idx, end_idx):
                    scene_type, scene = list(scenes.items())[i]
                    status.info(f"🎨 {scene_type} 장면 생성 중... ({i+1}/{cut_count})")
                
                    scene_start_time = datetime.now()
                
                    # 장면 설명 생성 및 CLIP 분석
                    description = self.create_scene_description(scene, config)
                    enhanced_description = self.clip_analyzer.enhance_prompt(
                        description, config.style, config.mood
                    )
                    scene_descriptions.append(enhanced_description)
                
                    # 이미지 생성
                    image_url = self.generate_image(enhanced_description, config)
                
                    if image_url:
                        generated_images[i] = image_url
                    
                        # CLIP 검증 및 품질 분석
                        quality_check = self.clip_analyzer.validate_image(
                            image_url, 
                            description,
                            return_score=True
                        )
                    
                        with cols[i % cols_per_row]:
                            # 이미지 표시
                            st.image(image_url, caption=f"컷 {i+1}: {scene_type}", use_column_width=True)
                        
                            # 분석 결과 표시를 위한 expander 추가
                            with st.expander("🔍 CLIP 분석 결과", expanded=False):
                                col1, col2 = st.columns(2)
                                score = quality_check.get("similarity_score", 0.0)
                            
                                with col1:
                                    st.metric("품질 점수", f"{score:.2f}")
                                with col2:
                                    if score >= 0.7:
                                        st.success("✓ 높은 품질")
                                    elif score >= 0.5:
                                        st.warning("△ 중간 품질")
                                    else:
                                        st.error("⚠ 낮은 품질")
                            
                                # 세부 분석 결과 표시
                                st.write("프롬프트 매칭:")
                                st.progress(score)
                            
                                # 생성 시간 표시
                                scene_time = (datetime.now() - scene_start_time).total_seconds()
                                st.info(f"⏱ 생성 시간: {scene_time:.1f}초")
                        
                            # 장면 설명 표시
                            summary = self.summarize_scene(description)
                            st.markdown(
                                f"<p style='text-align: center; font-size: 14px;'>{summary}</p>",
                                unsafe_allow_html=True
                            )
                    
                        # 메트릭 업데이트
                        generation_metrics['scores'].append(score)
                        generation_metrics['generation_attempts'].append({
                            'scene_number': i + 1,
                            'scene_type': scene_type,
                            'clip_score': score,
                            'generation_time': scene_time
                        })
                
                    progress_bar.progress((i + 1) / cut_count)
        
            # 전체 생성 시간 계산
            generation_metrics['total_time'] = (datetime.now() - start_time).total_seconds()
            generation_metrics['avg_clip_score'] = sum(generation_metrics['scores']) / len(generation_metrics['scores'])
        
            # 생성 로그 저장
            st.session_state.generation_logs.append({
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'config': config.__dict__,
                'metrics': generation_metrics
            })
        
            # 생성 결과 요약 표시
            st.sidebar.markdown("### 📊 생성 결과 요약")
            st.sidebar.metric("평균 CLIP 점수", f"{generation_metrics['avg_clip_score']:.2f}")
            st.sidebar.metric("총 생성 시간", f"{generation_metrics['total_time']:.1f}초")
        
            # 세션 상태 업데이트
            st.session_state.generated_images = generated_images
            st.session_state.scene_descriptions = scene_descriptions
        
            status.success("✨ 웹툰 생성 완료!")
        
          
        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")
            logging.error(f"Error in process_submission: {str(e)}")
def main():
    st.set_page_config(
        page_title="Text to Webtoon Converter",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    try:
        client = OpenAI()
        clip_analyzer = CLIPAnalyzer()
        converter = TextToWebtoonConverter(client, clip_analyzer)
        converter.render_ui()
    except Exception as e:
        st.error(f"애플리케이션 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    main()