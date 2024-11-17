import streamlit as st
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from openai import OpenAI
import logging
from PIL import Image
import PyPDF2
from docx import Document
from io import BytesIO
from image_gen import generate_image_from_text
@dataclass
class NonFictionConfig:
    style: str
    emphasis: str  # "concept", "process", "comparison", "structure"
    complexity: str  # "basic", "intermediate", "advanced"
    visualization_type: str  # "diagram", "illustration", "chart", "symbol"
    aspect_ratio: str

class NonFictionConverter:
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.setup_logging()
        
        # Style guides for different types of non-fiction content
        self.style_guides = {
            "educational": {
                "prompt": "clear educational illustration, simplified representation, focused on key concepts",
                "emphasis": "Learning objectives and core concepts"
            },
            "scientific": {
                "prompt": "accurate scientific visualization, precise details, professional appearance",
                "emphasis": "Scientific accuracy and clarity"
            },
            "technical": {
                "prompt": "technical diagram style, schematic representation, systematic layout",
                "emphasis": "Technical details and relationships"
            },
            "informative": {
                "prompt": "informative visualization, clear communication, organized layout",
                "emphasis": "Information hierarchy and flow"
            }
        }
        
        # Visualization type guides
        self.visualization_guides = {
            "diagram": {
                "prompt": "systematic diagram, clear connections, organized structure",
                "layout": "structured layout with clear flow"
            },
            "illustration": {
                "prompt": "simplified illustration, essential elements, clear visuals",
                "layout": "focused composition with key elements"
            },
            "chart": {
                "prompt": "data visualization, clear hierarchy, organized information",
                "layout": "structured information display"
            },
            "symbol": {
                "prompt": "symbolic representation, abstract concepts, minimal design",
                "layout": "simplified symbolic elements"
            }
        }

        # Negative prompts for non-fiction content
        self.negative_elements = (
            "narrative elements, emotional expressions, decorative details, "
            "complex backgrounds, artistic flourishes, unnecessary elements, "
            "ambiguous symbols, cluttered layout, distracting elements"
            "undefined character"
        )

    @staticmethod
    def setup_logging():
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def analyze_text_type(self, text: str) -> Dict[str, float]:
        """Analyze text to determine its type and characteristics"""
        try:
            prompt = """Analyze this text and determine its characteristics. 
            Consider:
            1. Is it educational, scientific, or technical?
            2. What level of complexity does it have?
            3. What type of visualization would best represent it?
            
            Provide scores from 0 to 1 for each category:
            - Educational value
            - Scientific content
            - Technical detail
            - Abstract concepts
            - Process description
            - Data presentation

            Text: {text}"""

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt.format(text=text)}],
                temperature=0.3
            )

            # Parse the response to get scores
            analysis = response.choices[0].message.content
            # Convert the analysis into a structured format
            # This is a simplified version - you'd need to parse the actual response
            scores = {
                "educational": 0.5,
                "scientific": 0.5,
                "technical": 0.5,
                "abstract": 0.5,
                "process": 0.5,
                "data": 0.5
            }

            return scores

        except Exception as e:
            logging.error(f"Text analysis failed: {str(e)}")
            raise

    def determine_visualization_approach(self, analysis_scores: Dict[str, float]) -> Dict[str, str]:
        """Determine the best visualization approach based on text analysis"""
        # Find the dominant characteristics
        max_score = max(analysis_scores.values())
        dominant_types = [k for k, v in analysis_scores.items() if v == max_score]

        visualization_mapping = {
            "educational": {"type": "illustration", "style": "educational"},
            "scientific": {"type": "diagram", "style": "scientific"},
            "technical": {"type": "chart", "style": "technical"},
            "abstract": {"type": "symbol", "style": "minimalist"},
            "process": {"type": "diagram", "style": "systematic"},
            "data": {"type": "chart", "style": "informative"}
        }

        # Select the most appropriate visualization approach
        selected_approach = visualization_mapping.get(dominant_types[0], 
                                                   {"type": "illustration", "style": "educational"})
        
        return selected_approach

    def create_visualization_prompt(self, text: str, config: NonFictionConfig) -> str:
        """Create a detailed prompt for generating the visualization"""
        try:
            # Analyze the text
            analysis = self.analyze_text_type(text)
            approach = self.determine_visualization_approach(analysis)

            # Get the appropriate style and visualization guides
            style_guide = self.style_guides[approach["style"]]
            vis_guide = self.visualization_guides[approach["type"]]

            # Create the base prompt
            prompt = f"""Create a clear {approach['type']} visualization:

            Content: {text}

            Style requirements:
            {style_guide['prompt']}
            {style_guide['emphasis']}

            Visualization specifications:
            {vis_guide['prompt']}
            {vis_guide['layout']}

            Essential elements to include:
            1. Clear visual hierarchy
            2. Simplified representations
            3. Focused information display
            4. Logical organization
            5. Essential labels or indicators

            Emphasis level: {config.complexity}
            Primary focus: {config.emphasis}
            """

            return prompt

        except Exception as e:
            logging.error(f"Prompt creation failed: {str(e)}")
            raise

    def render_ui(self):
        """Streamlit UI for the non-fiction converter"""
        st.title("비문학 텍스트 시각화")

        with st.form("nonfiction_input_form"):
            # Text input
            text_content = st.text_area(
                "텍스트 입력",
                placeholder="교육적/과학적/기술적 내용을 입력하세요.",
                height=200
            )

            col1, col2 = st.columns(2)

            with col1:
                style = st.selectbox(
                    "스타일",
                    ["educational", "scientific", "technical", "informative"]
                )

                emphasis = st.selectbox(
                    "강조점",
                    ["concept", "process", "comparison", "structure"]
                )

            with col2:
                complexity = st.selectbox(
                    "복잡도",
                    ["basic", "intermediate", "advanced"]
                )

                visualization_type = st.selectbox(
                    "시각화 유형",
                    ["diagram", "illustration", "chart", "symbol"]
                )

                aspect_ratio = st.selectbox(
                    "이미지 비율",
                    ["1:1", "16:9", "9:16"]
                )

            submit = st.form_submit_button("시각화 생성")

            if submit and text_content:
                config = NonFictionConfig(
                    style=style,
                    emphasis=emphasis,
                    complexity=complexity,
                    visualization_type=visualization_type,
                    aspect_ratio=aspect_ratio
                )

                self.process_submission(text_content, config)

    def process_submission(self, text: str, config: NonFictionConfig):
    #Process the submission and generate visualization"""
        try:
            progress_bar = st.progress(0)
            status = st.empty()

        # 1. Analyze text and create prompt
            status.info("📝 텍스트 분석 중...")
            prompt = self.create_visualization_prompt(text, config)
            progress_bar.progress(0.3)

        # 2. Generate visualization
            status.info("🎨 시각화 생성 중...")
        
        # Import image generation function
         
        
        # Create negative prompt specific to non-fiction content
            negative_prompt = """
            narrative elements, emotional expressions, decorative details,
            complex backgrounds, artistic flourishes, unnecessary elements,
            ambiguous symbols, cluttered layout, distracting elements,
            unrealistic proportions, text in image, blurry details
             """
        
        # Generate image
            image_url, revised_prompt, created_seed = generate_image_from_text(
                prompt=prompt,
                style=config.style,
                aspect_ratio=config.aspect_ratio,
                negative_prompt=negative_prompt
            )
        
            if image_url:
            # Display the generated image
                st.subheader("생성된 시각화")
                st.image(image_url, use_column_width=True)
            
            # Store results in session state for the results page
                st.session_state.visualization_result = image_url
                st.session_state.visualization_metadata = {
                    "original_prompt": prompt,
                    "revised_prompt": revised_prompt,
                    "style": config.style,
                    "emphasis": config.emphasis,
                    "complexity": config.complexity,
                    "visualization_type": config.visualization_type
                }
            
            # Display prompt information in expandable section
                with st.expander("프롬프트 정보 보기"):
                    st.text_area("Original Prompt", prompt, height=100)
                    if revised_prompt:
                        st.text_area("Revised Prompt", revised_prompt, height=100)
        
            progress_bar.progress(1.0)
            status.success("✨ 시각화 생성 완료!")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")
            logging.error(f"Error in process_submission: {str(e)}")

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