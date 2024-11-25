import streamlit as st
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from openai import OpenAI
import logging
from PIL import Image
from general_text_input import TextToWebtoonConverter  # 파일 처리 기능 재사용
from io import BytesIO
from image_gen import generate_image_from_text
from clip_analyzer import CLIPAnalyzer  # CLIP 분석기 추가


@dataclass
class NonFictionConfig:
    style: str
    complexity: str  # "basic", "intermediate", "advanced"
    visualization_type: str  # "diagram", "illustration", "chart", "symbol"
    aspect_ratio: str
    num_images: int  # 추가된 필드
    emphasis: str = "process"  # 기본값 설정 (마지막에 배치)

class NonFictionConverter:
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.clip_analyzer = CLIPAnalyzer()
        self.setup_logging()

        self.base_style = {
            "prompt": "minimal cartoon style, clear and simple design",
            "background": "clean white background",
            "colors": "cheerful and clear colors"
        }
        
        self.visualization_types = {
            "process": {
                "prompt": "simple step-by-step cartoon",
                "layout": "easy to follow flow",
                "elements": "cute arrows, simple numbered steps"
            },
            "concept": {
                "prompt": "friendly explanation cartoon",
                "layout": "central idea with simple connections",
                "elements": "cute icons, simple metaphors"
            },
            "system": {
                "prompt": "simple parts explanation",
                "layout": "clear connections between parts",
                "elements": "labeled parts with cute symbols"
            },
            "comparison": {
                "prompt": "side by side cartoon comparison",
                "layout": "clear before/after or vs layout",
                "elements": "matching cute illustrations"
            }
        }
        
        # 부정적 요소 단순화
        self.negative_elements = (
            "complex diagrams, technical symbols, cluttered layout, "
            "excessive details, scientific notation, complicated backgrounds, "
            "unnecessary text, too many elements"
        )

    @staticmethod
    def setup_logging():
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    def split_content_into_scenes(self, text: str, num_scenes: int) -> List[str]:
        """텍스트를 여러 장면으로 분할"""
        try:
            prompt = f"""다음 내용을 {num_scenes}개의 핵심 장면/개념으로 나누어주세요.
            각 장면은 독립적이면서도 연결되어야 하며, 가능한 한 간단명료해야 합니다.
            
            규칙:
            1. 각 장면은 아주 쉽게 설명할 수 있어야 합니다
            2. 마치 어린이에게 설명하듯이 단순화해주세요
            3. 각 장면은 하나의 명확한 포인트만 가져야 합니다
            4. 전문용어는 피하고 일상적인 표현을 사용해주세요
            
            텍스트:
            {text}"""

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            scenes = response.choices[0].message.content.strip().split("\n")
            return [scene.strip() for scene in scenes if scene.strip()][:num_scenes]
        
        except Exception as e:
            logging.error(f"Scene splitting failed: {str(e)}")
            return [text]  # 실패 시 전체 텍스트를 하나의 장면으로
   

    def determine_visualization_approach(self, analysis_result: Dict[str, str]) -> Dict[str, str]:
         # 시각화 스타일 가이드
        style_guide = {
        "cartoon": {
            "prompt": "simple cartoon style, cute and friendly characters, minimal details",
            "style": "fun and engaging minimal cartoon",
            "elements": "basic shapes, simple expressions, clear actions"
        },
        "minimal": {
            "prompt": "basic geometric shapes, essential elements only",
            "style": "clean and simple",
            "elements": "circles, squares, arrows, basic icons"
        },
        "flowchart": {
            "prompt": "simple flowchart style, clear direction",
            "style": "step-by-step visual guide",
            "elements": "connected boxes, directional arrows"
        },
        "comparison": {
            "prompt": "side-by-side comparison, clear differences",
            "style": "comparative visualization",
            "elements": "paired illustrations, contrast indicators"
        }
    }
        visual_style = analysis_result.get("visual_style", "minimal")
        return style_guide.get(visual_style, style_guide["minimal"])

    
    
    def analyze_text_type(self, text: str) -> Dict[str, float]:
        #텍스트 분석을 통해 가장 적합한 시각화 방식 결정"""
        try:
            prompt = """다음 텍스트를 읽고, 가장 효과적인 시각화 방식을 추천해주세요:

        1. 이것이 설명하는 것이 무엇인가요?
        - 과정/단계
        - 개념/아이디어
        - 비교/대조
        - 구조/시스템

        2. 어떻게 표현하면 가장 이해하기 쉬울까요?
        - 간단한 만화 스타일
        - 기본 도형으로 표현
        - 흐름도
        - 비교 그림

        핵심은 '단순함'과 '명확함'입니다.
        너무 복잡하거나 과학적인 표현은 피해주세요.

        텍스트: {text}"""

            response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt.format(text=text)}],
            temperature=0.3
        )

        # 간단한 결과 반환
            return {
            "content_type": "process",  # process, concept, comparison, system
            "visual_style": "cartoon"   # cartoon, minimal, flowchart, comparison
        }

        except Exception as e:
            logging.error(f"Text analysis failed: {str(e)}")
            raise

    def render_ui(self):
       #UI 단순화
        st.title("교육/ 과학 텍스트 시각화하기")
         # 입력 방식 선택
        input_method = st.radio(
            "입력 방식을 선택하세요",
            ["직접 입력", "파일 업로드"],
            horizontal=True
        )

        with st.form("nonfiction_input_form"):
            text_content = None
            if input_method == "직접 입력":
                text_content = st.text_area(
                    "설명하고 싶은 내용을 입력하세요",
                    placeholder="어려운 내용을 쉽게 설명해드릴게요.",
                    height=200
             )
            else:
                uploaded_file=st.file_uploader(
                    "파일 업로드",
                type=['txt', 'pdf', 'docx', 'doc'],
                help="지원 형식: TXT, PDF, DOCX"
                )
                if uploaded_file:
                    text_content=TextToWebtoonConverter.read_file_content(uploaded_file)
                    if text_content:
                        st.success("파일 업로드 성공!")
                        with st.expander("파일 내용 확인"):
                            st.text(text_content[:500] + "..." if len(text_content) > 500 else text_content)
            col1, col2 = st.columns(2)

            with col1:
                visualization_type = st.selectbox(
                "어떤 방식으로 설명할까요?",
                ["process", "concept", "system", "comparison"],
                help="process: 순서대로 설명, concept: 개념 설명, system: 구조 설명, comparison: 비교 설명"
            )
            
                num_images = st.radio(
                "몇 장의 그림이 필요하신가요?",
                options=[1, 2, 3, 4],
                horizontal=True
            )

            with col2:
                complexity = st.select_slider(
                "이미지의 자세함 설정 ",
                    options=["basic", "intermediate", "advanced"],
                    value="basic"
            )
                aspect_ratio = st.selectbox(
                "이미지 비율",
                ["1:1", "16:9", "9:16"]
            )

        # Submit 버튼을 form 내부로 이동
            submit = st.form_submit_button("웹툰 생성 시작 ")

            if submit:
                if text_content:
                    config = NonFictionConfig(
                        style="cartoon",  # 항상 친근한 만화 스타일 사용
                        visualization_type=visualization_type,
                        complexity=complexity,
                        aspect_ratio=aspect_ratio,
                        num_images=num_images,
                        emphasis="clarity"  # 항상 명확성 강조
                     )
                self.process_submission(text_content, config)
            else:
                st.warning("텍스트를 입력하거나 파일을 업로드해주세요!")
    
    def create_scene_description(self, scene: str, config: NonFictionConfig) -> str:
      #각 장면에 대한 시각화 프롬프트 생성"""
        try:
            vis_type = self.visualization_types[config.visualization_type]
            
        # 기본 스타일과 선택된 시각화 타입 결합
            prompt = f"""Create a simple and friendly cartoon visualization:

            Content to explain: {scene}

            Style:
            - Simple cartoon style like children's book illustrations
            - Clean and easy to understand
            - Use cute and friendly elements
            - Minimal details, maximum clarity

            Visual approach: {vis_type['prompt']}
            Layout: {vis_type['layout']}
            Main elements: {vis_type['elements']}

            Key requirements:
            - Keep it super simple and friendly
            - Use basic shapes and cute symbols
            - Make it instantly understandable
            - Avoid complex details
            - Use clear, cheerful colors
            - Make it engaging and fun

            Complexity: {config.complexity} (but keep it simple regardless)"""

            return prompt

        except Exception as e:
            logging.error(f"Scene description creation failed: {str(e)}")
            raise

    def _parse_analysis_response(self, response_text: str) -> Dict[str, float]:
    #"""분석 응답을 파싱하여 점수로 변환"""
         try:
        # 간단한 파싱 로직 구현
            scores = {
            "process": 0.5,
            "concept": 0.5,
            "system": 0.5,
            "comparison": 0.5
        }
            return scores
         except Exception as e:
            logging.error(f"Analysis parsing failed: {str(e)}")
            return {"process": 0.5, "concept": 0.5, "system": 0.5, "comparison": 0.5}

    def process_submission(self, text: str, config: NonFictionConfig):
        try:
            progress_bar = st.progress(0)
            status = st.empty()

            # 1. 텍스트를 여러 장면으로 분할
            status.info("📝 내용 분석 중...")
            scenes = self.split_content_into_scenes(text, config.num_images)
            progress_bar.progress(0.2)

            # 2. 각 장면별 처리
            generated_images = []
            for i, scene in enumerate(scenes):
                status.info(f"🎨 {i+1}/{len(scenes)} 이미지 생성 중...")
                
                # 장면별 프롬프트 생성
                prompt = self.create_scene_description(scene, config)
                
                # 이미지 생성
                image_url, revised_prompt, _ = generate_image_from_text(
                    prompt=prompt,
                    style="minimalist",
                    aspect_ratio=config.aspect_ratio,
                    negative_prompt=self.negative_elements
                )
                
                if image_url:
                    # CLIP 점수 계산
                    # 피드백 루프X 최초 이미지 점수
                    clip_score = self.clip_analyzer.validate_image(
                        image_url,
                        prompt,
                        return_score=True
                    )
                    
                    summary = self.summarize_scene(scene)
                    generated_images.append({
                        "url": image_url,
                        "summary": summary,
                        "prompt": prompt,
                        "revised_prompt": revised_prompt,
                        "clip_score": clip_score.get("similarity_score", 0.0)
                    })
                
                progress_bar.progress((i + 1) / len(scenes))

            # 3. 결과 표시
            if generated_images:
                cols = st.columns(min(2, len(generated_images)))
                for i, img_data in enumerate(generated_images):
                    with cols[i % 2]:
                        st.image(img_data["url"], use_column_width=True)
                        st.markdown(
                            f"<p style='text-align: center; font-size: 14px;'>{img_data['summary']}</p>", 
                            unsafe_allow_html=True
                        )
                        
                        # CLIP 점수를 단순 숫자로 표시
                        st.markdown(
                            f"<p style='text-align: center; font-size: 14px;'>"
                            f"이미지-텍스트 일치도: {img_data['clip_score']:.3f}</p>",
                            unsafe_allow_html=True
                        )
                        
                        with st.expander(f"이미지 {i+1} 상세 정보"):
                            st.text(f"사용된 프롬프트:\n{img_data['prompt']}")
                            if img_data['revised_prompt']:
                                st.text(f"수정된 프롬프트:\n{img_data['revised_prompt']}")

            progress_bar.progress(1.0)
            status.success("✨ 시각화된 웹툰 생성 완료!")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")
            logging.error(f"Error in process_submission: {str(e)}")

    def summarize_scene(self, description: str) -> str:
   # """장면 설명 요약"""
        try:
            prompt = """다음 시각화 내용을 간단히 설명해주세요:
        1. 한 문장으로 작성
        2. 객관적인 설명 위주
        3. 핵심 요소만 포함
        4. 최대 50자 이내
        
            설명할 내용:"""
        
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
            return summary[:100]  # 50자로 제한
        
        except Exception as e:
            logging.error(f"Scene summarization failed: {str(e)}")
            return description[:100]                
# The main function would be similar to your existing code
def main():
    st.set_page_config(
        page_title="Non-fiction Text Visualizer",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    try:
        client = OpenAI()
        converter = NonFictionConverter(client)
        converter.render_ui()
    except Exception as e:
        st.error(f"애플리케이션 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    main()