import streamlit as st
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from openai import OpenAI
import logging
from clip_analyzer import CLIPAnalyzer
from datetime import datetime
from PIL import Image
from general_text_input import TextToWebtoonConverter
from io import BytesIO
from image_gen import generate_image_from_text
from save_utils import save_session

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
        self.clip_analyzer = CLIPAnalyzer()  # CLIP 분석기 추가
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
        
        # form 바깥에서 저장 버튼 처리
        if st.session_state.generated_images:
            if st.button("💾 이번 과정 저장하기"):
                save_config = {
                'type': 'education',
                'title': st.session_state.current_text[:100],
                'text': st.session_state.current_text,
                'visualization_type': st.session_state.current_config.visualization_type,
                #'complexity': st.session_state.current_config.complexity,
                'aspect_ratio': st.session_state.current_config.aspect_ratio,
                'num_images': st.session_state.current_config.num_images,
                'scene_descriptions': st.session_state.scene_descriptions
                }
                session_dir = save_session(save_config, st.session_state.generated_images)
                
                st.success(f"✅ 성공적으로 저장되었습니다! 저장 위치: {session_dir}")

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