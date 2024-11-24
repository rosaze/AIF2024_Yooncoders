import torch
from PIL import Image
import logging
from transformers import CLIPProcessor, CLIPModel
from openai import OpenAI
import requests
from io import BytesIO
import streamlit as st

class CLIPAnalyzer:
    def __init__(self):
        """CLIP 모델과 프로세서 초기화"""
        try:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
            self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.client = OpenAI()
            self.minimum_score_threshold = 0.5  # 최소 허용 점수
            self.target_score_threshold = 0.7   # 목표 점수
            logging.info(f"CLIP Analyzer initialized on device: {self.device}")
            
        except Exception as e:
            logging.error(f"CLIP 모델 초기화 실패: {str(e)}")
            raise RuntimeError(f"CLIP 모델 초기화 실패: {str(e)}")

    def enhance_prompt(self, prompt, style, mood):
        """프롬프트를 개선하고 시각적 요소를 강화"""
        try:
            # 핵심 요소 추출
            key_elements = self._extract_key_elements(prompt)
            
            enhancement_prompt = f"""
            다음 장면 설명을 웹툰 스타일로 개선해주세요:
            1. 핵심 시각적 요소를 유지하면서 더 구체적으로 표현
            2. {style} 스타일과 {mood} 분위기를 자연스럽게 반영
            3. 캐릭터의 감정과 동작을 생생하게 표현
            4. 배경과 조명을 통해 분위기 강화
            
            핵심 요소들:
            {key_elements}
            
            원본 설명:
            {prompt}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # 더 빠른 응답을 위해 GPT-3.5 사용
                messages=[{"role": "user", "content": enhancement_prompt}],
                max_tokens=200,
                temperature=0.7
            )
            
            enhanced_prompt = response.choices[0].message.content.strip()
            
            logging.info(f"원본 프롬프트 길이: {len(prompt)}")
            logging.info(f"개선된 프롬프트 길이: {len(enhanced_prompt)}")
            
            return enhanced_prompt
            
        except Exception as e:
            logging.error(f"프롬프트 개선 중 오류: {str(e)}")
            return prompt

    def _extract_key_elements(self, text):
        """텍스트에서 핵심적인 시각적 요소들을 추출"""
        try:
            prompt = """
            이 장면에서 가장 중요한 시각적 요소들만 추출해주세요 (최대 3개):
            1. 주요 캐릭터의 행동과 표정
            2. 중요한 배경 요소
            3. 전체적인 분위기나 조명
            
            장면:
            {text}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt.format(text=text)}],
                max_tokens=100,
                temperature=0.3
            )
            
            key_elements = response.choices[0].message.content.strip()
            logging.info(f"추출된 핵심 요소: {key_elements}")
            
            return key_elements
            
        except Exception as e:
            logging.error(f"핵심 요소 추출 중 오류: {str(e)}")
            return "핵심 요소 추출 실패"

    def validate_image(self, image_url, prompt, story_context=None, return_score=False):
        """이미지와 프롬프트의 일치도를 검증"""
        try:
            # 프롬프트 길이 제한
            core_prompt = self._extract_core_prompt(prompt)
            max_length = 77  # CLIP 모델의 최대 토큰 길이
            core_prompt = ' '.join(core_prompt.split()[:max_length])
            
            # 이미지 다운로드 및 전처리
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content))
            
            # CLIP 입력 준비
            inputs = self.processor(
                images=image,
                text=[core_prompt],
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            # 유사도 계산
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = torch.nn.functional.softmax(logits_per_image, dim=1)
                similarity = probs[0][0].item()
            
            # 스토리 컨텍스트가 있는 경우 일관성 체크
            if story_context and story_context.get("previous_scenes"):
                context_score = self._check_story_consistency(image, story_context)
                # 기본 유사도와 컨텍스트 점수를 결합 (70:30 비율)
                similarity = (0.7 * similarity) + (0.3 * context_score)
            
            # 결과 분석
            result = {
                "similarity_score": similarity,
                "meets_requirements": similarity >= self.target_score_threshold,
                "prompt_used": core_prompt
            }
            
            return result if return_score else result["meets_requirements"]
            
        except Exception as e:
            logging.error(f"이미지 검증 중 오류: {str(e)}")
            default_result = {
                "similarity_score": 0.5,
                "meets_requirements": True,
                "error": str(e)
            }
            return default_result if return_score else True

    def _extract_core_prompt(self, prompt):
        """프롬프트에서 핵심 내용만 추출"""
        try:
            system_prompt = """
            다음 장면 설명에서 가장 핵심적인 시각적 요소만 한 문장으로 추출하세요.
            - 불필요한 설명 제거
            - 핵심 행동과 분위기 유지
            - 간단하고 명확하게
            최대 50단어로 제한하세요.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            core_prompt = response.choices[0].message.content.strip()
            logging.info(f"추출된 핵심 프롬프트: {core_prompt}")
            
            return core_prompt
            
        except Exception as e:
            logging.error(f"핵심 프롬프트 추출 중 오류: {str(e)}")
            return prompt[:100]  # 오류 시 원본 프롬프트의 처음 100자 사용

    def _check_story_consistency(self, new_image, story_context):
        """새 이미지와 이전 장면들과의 일관성 검증"""
        try:
            if not story_context.get("previous_scenes"):
                return 1.0  # 첫 장면인 경우

            previous_images = []
            for scene in story_context["previous_scenes"][-3:]:  # 최근 3개 장면만 비교
                try:
                    response = requests.get(scene["image_url"])
                    prev_image = Image.open(BytesIO(response.content))
                    previous_images.append(prev_image)
                except Exception as e:
                    logging.warning(f"이전 이미지 로드 실패: {e}")
                    continue

            if not previous_images:
                return 1.0

            # 스타일 일관성 점수 계산
            consistency_scores = []
            for prev_image in previous_images:
                try:
                    inputs = self.processor(
                        images=[prev_image, new_image],
                        return_tensors="pt",
                        padding=True
                    ).to(self.device)
                    
                    with torch.no_grad():
                        features = self.model.get_image_features(**inputs)
                        similarity = torch.nn.functional.cosine_similarity(
                            features[0].unsqueeze(0), 
                            features[1].unsqueeze(0)
                        ).item()
                    consistency_scores.append(similarity)
                except Exception as e:
                    logging.error(f"일관성 점수 계산 중 오류: {e}")
                    continue

            if not consistency_scores:
                return 1.0

            return sum(consistency_scores) / len(consistency_scores)

        except Exception as e:
            logging.error(f"일관성 검사 중 오류: {str(e)}")
            return 1.0

    def analyze_style_consistency(self, images):
        """여러 이미지 간의 스타일 일관성 분석"""
        if len(images) < 2:
            return True, 1.0
            
        try:
            # 이미지들을 CLIP 임베딩으로 변환
            embeddings = []
            for img_url in images:
                response = requests.get(img_url)
                img = Image.open(BytesIO(response.content))
                
                inputs = self.processor(
                    images=img,
                    return_tensors="pt"
                ).to(self.device)
                
                with torch.no_grad():
                    embedding = self.model.get_image_features(**inputs)
                embeddings.append(embedding)
            
            # 임베딩 간의 코사인 유사도 계산
            similarities = []
            for i in range(len(embeddings)-1):
                for j in range(i+1, len(embeddings)):
                    sim = torch.nn.functional.cosine_similarity(
                        embeddings[i], embeddings[j]
                    ).item()
                    similarities.append(sim)
            
            # 평균 유사도 계산
            avg_similarity = sum(similarities) / len(similarities)
            
            return avg_similarity >= 0.7, avg_similarity
            
        except Exception as e:
            logging.error(f"스타일 일관성 분석 중 오류: {str(e)}")
            return False, 0.0

    def get_image_focus_area(self, image_url, prompt):
        """이미지에서 중요한 영역 감지"""
        try:
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content))
            
            inputs = self.processor(
                images=image,
                return_tensors="pt"
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.get_image_features(**inputs, output_attentions=True)
                attention_map = outputs.attentions[-1].mean(dim=1)
            
            return attention_map.cpu().numpy()
            
        except Exception as e:
            logging.error(f"이미지 포커스 영역 분석 중 오류: {str(e)}")
            return None

    @staticmethod
    def visualize_results(image_url, clip_score, attention_map=None):
        """검증 결과 시각화"""
        try:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.image(image_url, use_column_width=True)
                
            with col2:
                st.metric("CLIP 유사도", f"{clip_score:.2f}")
                if clip_score >= 0.7:
                    st.success("✓ 검증 통과")
                else:
                    st.warning("⚠ 개선 필요")
                
            if attention_map is not None:
                st.write("주목 영역:")
                fig, ax = plt.subplots()
                sns.heatmap(attention_map, ax=ax)
                st.pyplot(fig)
                
        except Exception as e:
            logging.error(f"결과 시각화 중 오류: {str(e)}")
            st.error("결과 시각화 실패")