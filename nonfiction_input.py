import streamlit as st
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from openai import OpenAI
import logging
from datetime import datetime
from PIL import Image
from general_text_input import TextToWebtoonConverter
from io import BytesIO
from image_gen import generate_image_from_text
from save_utils import save_session
from clip_analyzer import CLIPAnalyzer  # CLIP 분석기 추가


@dataclass
class NonFictionConfig:
    style: str
    visualization_type: str
    aspect_ratio: str
    num_images: int
    emphasis: str = "clarity"

class NonFictionConverter:
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.setup_logging()
        
        # 시각화 타입을 스토리텔링 방식으로 변경
        self.visualization_types = {
           "설명하기": {
        "prompt": "simple minimalistic shapes, thin and sharp lines, clean composition, no text",
        "layout": "minimalistic single-concept layout",
        "elements": "sole object, no unnecessary shading or details",
        "style": "educational minimalistic style with thin lines"
    },
    "비교하기": {
        "prompt": "two-column comparison, thin outlines, minimalistic shapes, clean layout, no unnecessary details",
        "layout": "side-by-side layout, focus on clear differences",
        "elements": "precise shapes, no shading, no text",
        "style": "minimalistic cartoon style with fine lines"
    },
    "과정 보여주기": {
        "prompt": "step-by-step flow, clean lines, thin minimalistic shapes, cartoon-like simplicity without exaggeration",
        "layout": "horizontal or vertical progression with arrows",
        "elements": "single-colored shapes, no gradients, no text",
        "style": "thin line cartoon minimalistic style"
    },
    "원리 설명하기": {
        "prompt": "cause-and-effect diagram with minimalistic shapes, thin lines, plain white background, no text",
        "layout": "input-output or cause-effect structure",
        "elements": "clear, distinct shapes, no complex details",
        "style": "scientific minimalistic style with cartoon simplicity"
    }
}

    @staticmethod
    def setup_logging():
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def split_content_into_scenes(self, text: str, num_scenes: int) -> List[str]:
        """텍스트를 설명 가능한 장면들로 분할"""
        try:
            prompt = f"""다음 내용을 {num_scenes}개의 핵심 장면으로 분리해주세요.
        각 장면은 시각적으로 표현할 수 있어야 합니다.

        분석 기준:
        1. 중요 개념이나 핵심 아이디어 위주로 선택
        2. 시각적으로 표현하기 쉬운 부분 우선
        3. 내용의 논리적 흐름 유지
        4. 복잡한 내용은 단순한 관계로 재구성
        5. 추상적인 개념은 구체적인 비유로 변환

        현재 텍스트:
        {text}

        각 장면은 다음과 같은 형식으로 작성:
        - 시각적 요소를 중심으로 설명
        - 관계와 구조를 명확하게 표현
        - 한 장면당 1-2문장으로 간단히 기술"""

            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )

            scenes = response.choices[0].message.content.strip().split("\n\n")
            return [scene.strip() for scene in scenes if scene.strip()][:num_scenes]
        
        except Exception as e:
            logging.error(f"Scene splitting failed: {str(e)}")
            return [text]

    def create_scene_description(self, scene: str, config: NonFictionConfig) -> str:
        """장면을 웹툰 스타일의 프롬프트로 변환"""
        try:
        # visualization_type이 유효한지 확인
            if config.visualization_type not in self.visualization_types:
                logging.error(f"Invalid visualization type: {config.visualization_type}")
                # 기본값 "설명하기" 사용
                vis_type = self.visualization_types["설명하기"]
            else:
                vis_type = self.visualization_types[config.visualization_type]
            
            # 입력 텍스트 길이 제한
            max_length = 200
            content = scene[:max_length] if len(scene) > max_length else scene
            
            prompt = f"""Create a clear, simple educational illustration:

Main concept: {content}

Style requirements:
- {vis_type['style']}
- Layout: {vis_type['layout']}
- Elements: {vis_type['elements']}
- Visual style: {vis_type['prompt']}
- Single focused concept per image
- Bold, clean lines like manhwa/manga style
- Soft, pleasant color palette (2-3 colors maximum)
- White or very light background

Must include:
- One clear focal point
- Simple visual metaphor
- Easy-to-understand layout
- Gentle, rounded edges
- Ample white space around main element

Must avoid:
- Multiple competing concepts
- Complex diagrams or flowcharts
- Technical symbols or formulas
- Connecting lines or arrows
- Text labels or numbers
- Cluttered compositions
- Multiple scenes in one image
"""

            return prompt

        except Exception as e:
            logging.error(f"Scene description creation failed: {str(e)}")
            raise

    def process_submission(self, text: str, config: NonFictionConfig):
        
        """웹툰 스타일의 교육 컨텐츠 생성"""
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

            # 1. 텍스트를 설명 가능한 장면들로 분할
            status.info("📝 내용 분석 중...")
            scenes = self.split_content_into_scenes(text, config.num_images)
            progress_bar.progress(0.2)

            # 2. 결과 저장을 위한 딕셔너리 초기화
            generated_images = {}
            scene_descriptions = []

            # 생성 메트릭 저장용 딕셔너리
            generation_metrics = {
                'total_time': 0,
                'avg_clip_score': 0,
                'scores': [],
                'generation_attempts': []
            }

            # 3. 각 장면별 처리
            for i, scene in enumerate(scenes):
                scene_start_time = datetime.now()
                status.info(f"🎨 {i+1}/{len(scenes)} 장면 생성 중...")
            
                # 장면별 프롬프트 생성
                prompt = self.create_scene_description(scene, config)
                scene_descriptions.append(prompt)
            
                # 이미지 생성
                image_url, _, _ = generate_image_from_text(
                    prompt=prompt,
                    style="minimalistic",
                    aspect_ratio=config.aspect_ratio,
                    negative_prompt=(
                         "abstract art, messy layout, unclear connections, "
                            "photorealistic style, 3d rendering, "
                                "complex textures, dark colors, "
                                    "artistic interpretation, painterly style"
                    )
                    )
            
                if image_url:
                    generated_images[i] = image_url
                
                    # CLIP 검증 및 품질 분석
                    quality_check = self.clip_analyzer.validate_image(
                        image_url, 
                        prompt,
                        return_score=True
                    )

                    if i % 2 == 0:
                        cols = st.columns(min(2, config.num_images - i))
                
                    with cols[i % 2]:
                        # 이미지 표시
                        st.image(image_url, use_column_width=True)
                    
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
                        summary = self.summarize_scene(scene)
                        st.markdown(
                            f"<p style='text-align: center; font-size: 14px;'>{summary}</p>", 
                            unsafe_allow_html=True
                        )

                    # 메트릭 업데이트
                    generation_metrics['scores'].append(score)
                    generation_metrics['generation_attempts'].append({
                        'scene_number': i + 1,
                        'clip_score': score,
                        'generation_time': scene_time
                    })
            
                progress_bar.progress((i + 1) / config.num_images)

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

            # 세션 상태에 결과 저장
            st.session_state.generated_images = generated_images
            st.session_state.scene_descriptions = scene_descriptions

            status.success("✨ 웹툰 생성 완료!")

         

        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")
            logging.error(f"Error in process_submission: {str(e)}")

    def summarize_scene(self, description: str) -> str:
        """장면의 맥락과 의미를 담은 설명 생성"""
        try:
            prompt = """다음 시각적 설명을 보고 장면의 맥락과 핵심 메시지를 설명해주세요.

        요구사항:
    1. 단순한 시각적 묘사("~장면이다")는 피하고, 맥락과 의미를 담아주세요
    2. 가능한 현재형으로 설명해주세요
    3. 필요시 인과관계나 변화를 포함해도 좋습니다
    4. 최대 70자 이내로 작성해주세요

    예시:
    ❌ "원과 화살표가 연결된 장면이다"
    ⭕ "물이 수증기로 변하며 순환하는 과정을 보여줍니다"

    ❌ "두 개의 사각형이 비교된 장면이다"
    ⭕ "고체와 액체 상태에서 분자의 움직임이 달라집니다"

    ❌ "인물이 있는 배경 장면이다"
    ⭕ "환경오염으로 인해 지구의 온도가 계속 상승하고 있습니다"

    설명할 내용:
    {description}"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": description}
                ],
                temperature=0.7,
                max_tokens=200
            )
        
            summary = response.choices[0].message.content.strip()
            # 마침표가 없다면 추가
            if not summary.endswith(('.', '!', '?')):
                summary += '.'
            return summary[:150]
    
        except Exception as e:
            logging.error(f"Scene summarization failed: {str(e)}")
            return description[:70]
                

    def render_ui(self):
       #UI 단순화
        st.title("교육/ 과학 텍스트 시각화하기")
        with st.sidebar.expander("📚 시각화 가이드", expanded=True):
            st.markdown("""
                        ### 🎯 시각화 방식
        - **설명하기**: 개념을 명확하게 전달
          - _단순하고 직관적인 도식화_
          - _핵심 요소 강조_
        
        - **비교하기**: 차이점 또는 특징 대조
          - _나란한 구조로 표현_
          - _변화나 차이 부각_
        
        - **과정 보여주기**: 단계별 변화 설명
          - _순차적 흐름 표현_
          - _인과관계 명확화_
        
        - **원리 설명하기**: 작동 방식 시각화
          - _구조와 관계 표현_
          - _메커니즘 도식화_
        
        ### 🖼️ 이미지 비율
        - **정사각형 (1:1)**: 균형잡힌 도식
        - **와이드 (16:9)**: 과정이나 흐름 표현
        - **세로형 (9:16)**: 계층 구조나 순서 표현
        
        ### 📊 이미지 수량
        - **1장**: 핵심 개념 집중
        - **2장**: 비교 또는 전후 관계
        - **3장**: 단계별 진행 과정
        - **4장**: 상세한 분석이나 설명
        """)
        
        st.info("""
        💡 **효과적인 시각화 팁**
        - 복잡한 내용은 단계별로 나누어 표현하세요
        - 핵심 개념을 중심으로 단순화하세요
        - 직관적인 도형과 화살표를 활용하세요
        - 관련된 요소들은 같은 색상으로 묶어주세요
        """)
                        
        # 세션 상태 초기화
        if 'generated_images' not in st.session_state:
            st.session_state.generated_images = {}
            st.session_state.current_config = None
            st.session_state.current_text = None
            st.session_state.scene_descriptions = []
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
                list(self.visualization_types.keys()),  
                help="컨텐츠에 가장 적합한 설명 방식을 선택하세요"
            )
            
                num_images = st.radio(
                "몇 장의 그림이 필요하신가요?",
                options=[1, 2, 3, 4],
                horizontal=True
            )

            with col2:
                aspect_ratio = st.selectbox(
                "이미지 비율",
                ["정사각형 (1:1)", "와이드 (16:9)", "세로형 (9:16)"]
                )

            submit = st.form_submit_button("✨ 웹툰 생성 시작")

            if submit and text_content:
                ratio_map = {
                "정사각형 (1:1)": "1:1",
                "와이드 (16:9)": "16:9",
                "세로형 (9:16)": "9:16"
            }
            
                config = NonFictionConfig(
                style="webtoon",  # 웹툰 스타일로 고정
                visualization_type=visualization_type,
                aspect_ratio=ratio_map.get(aspect_ratio, "1:1"),
                num_images=num_images,
                emphasis="clarity"
            )
                 # 세션 상태에 현재 설정 저장
                st.session_state.current_config = config
                st.session_state.current_text = text_content
                self.process_submission(text_content, config)
            
            elif submit:
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
    #"""여러 장의 이미지 생성 및 처리"""
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
                    style="minimalist",  # 항상 미니멀 스타일 사용
                    aspect_ratio=config.aspect_ratio,
                    negative_prompt=self.negative_elements
            )
            
                if image_url:
                # imported summarize_scene 함수 사용
                    summary = self.summarize_scene(scene)  # 자체 메소드 대신 imported 함수 사용
                    generated_images.append({
                    "url": image_url,
                    "summary": summary,
                    "prompt": prompt,
                    "revised_prompt": revised_prompt
                })
            
                progress_bar.progress((i + 1) / len(scenes))

        # 3. 결과 표시
            if generated_images:
                cols = st.columns(min(2, len(generated_images)))
                for i, img_data in enumerate(generated_images):
                    with cols[i % 2]:
                        st.image(img_data["url"], use_column_width=True)
                        st.markdown(f"<p style='text-align: center; font-size: 14px;'>{img_data['summary']}</p>", 
                              unsafe_allow_html=True)
                    
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
        page_title="Educational Webtoon Creator",
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