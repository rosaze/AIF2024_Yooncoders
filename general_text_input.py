import streamlit as st
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from PIL import Image
import logging
from openai import OpenAI
import torch
from io import BytesIO
import PyPDF2
from clip_analyzer import CLIPAnalyzer
from docx import Document
from image_gen import generate_image_from_text
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
            "minimalist": {
                "prompt": "minimal details, simple lines, clean composition, essential elements only",
                "emphasis": "Focus on simplicity and negative space"
            },
            "pictogram": {
                "prompt": "symbolic representation, simplified shapes, icon-like style",
                "emphasis": "Clear silhouettes and symbolic elements"
            },
            "cartoon": {
                "prompt": "animated style, exaggerated features, bold colors",
                "emphasis": "Expressive and dynamic elements"
            },
            "webtoon": {
                "prompt": "webtoon style, manhwa art style, clean lines, vibrant colors",
                "emphasis": "Dramatic angles and clear storytelling"
            },
            "artistic": {
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
        #DALL-E를 사용한 이미지 생성"""
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
                quality_check = self.clip_analyzer.validate_image(image_url, description)
            
                if quality_check["similarity_score"] >= 0.7:
                    return image_url
                else:
                    logging.warning(f"Image quality check failed: {quality_check['suggestions']}")
                    return image_url
                
        except Exception as e:
            logging.error(f"Image generation failed: {str(e)}")
            raise

    def summarize_scene(self, description: str) -> str:
        #장면 설명 요약"""
        try:
            prompt = """웹툰의 한 장면을 간단히 설명해주세요.
        - 한 문장으로 작성할 것
        - 캐릭터의 감정이나 심리 상태가 아닌, 객관적인 상황 묘사에 집중
        - 예시: "한적한 카페에서 두 사람이 마주 앉아 대화를 나누고 있다."
        - 최대 100자 이내로 작성할 것
        
            장면:"""
        
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": description}
            ],
                 temperature=0.7,
                max_tokens=100
        )
        
            summary = response.choices[0].message.content.strip()
        # 마침표로 끝나는 경우 마침표 제거
            summary = summary.rstrip('.')
        # 50자로 제한
            return summary[:150]
        except Exception as e:
            logging.error(f"Scene summarization failed: {str(e)}")
            return description.split('\n')[0][:150]

    def render_ui(self):
        """Streamlit UI 렌더링"""
        st.title("텍스트를 웹툰으로 변환하기")
        
        input_method = st.radio(
            "입력 방식을 선택하세요",
            ["직접 입력", "파일 업로드"],
            horizontal=True
        )
        
        text_content = None
        
        with st.form("story_input_form"):
            if input_method == "직접 입력":
                text_content = st.text_area(
                    "스토리 입력",
                    placeholder="소설, 뉴스 기사, 또는 자유로운 이야기를 입력해주세요.",
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
                    options=["minimalist", "pictogram", "cartoon", "webtoon", "artistic"],
                    value="webtoon"
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
                    ["1:1", "16:9", "9:16"]
                )
            
            submit = st.form_submit_button("웹툰 생성 시작")
            
            if submit:
                if text_content:
                    self.process_submission(
                        text_content,
                        SceneConfig(style, composition, mood, character_desc, aspect_ratio),
                        cut_count
                    )
                else:
                    st.warning("텍스트를 입력하거나 파일을 업로드해주세요!")

    def process_submission(self, text: str, config: SceneConfig, cut_count: int):
        """폼 제출 처리 및 이미지 생성"""
        try:
            progress_bar = st.progress(0)
            status = st.empty()
            
            # 1. 장면 분석
            status.info("📖 텍스트 분석 중...")
            scenes = self.analyze_text(text, cut_count)
            
            # 2. 장면별 설명 생성
            status.info("🎨 장면 설명 생성 중...")
            scene_descriptions = []
            for i, scene in enumerate(scenes):
                description = self.create_scene_description(scene, config)
                enhanced_description = self.clip_analyzer.enhance_prompt(
                    description, config.style, config.mood
                )
                scene_descriptions.append(enhanced_description)
                progress_bar.progress((i + 1) / (len(scenes) * 2))
            
            # 3. 이미지 생성 및 표시
            status.info("🎨 이미지 생성 중...")
            cols = st.columns(min(cut_count, 2))
            
            for i, (description, col) in enumerate(zip(scene_descriptions, cols)):
                image_url = self.generate_image(description, config)
                if image_url:
                    with col:
                        st.image(image_url, caption=f"컷 {i+1}", use_column_width=True)
                        summary = self.summarize_scene(description)
                        #st.write(summary)
                        st.markdown(f"<p style='text-align: center; font-size: 14px; margin-top: -10px; margin-bottom: 20px;'>{summary}</p>", unsafe_allow_html=True)
                progress_bar.progress((len(scenes) + i + 1) / (len(scenes) * 2))
            
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