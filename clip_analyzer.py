import torch
from PIL import Image
import logging
from transformers import CLIPProcessor, CLIPModel
from openai import OpenAI

class CLIPAnalyzer:
    def __init__(self):
        try:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
            self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.client = OpenAI()
            
        except Exception as e:
            raise RuntimeError(f"CLIP 모델 초기화 실패: {str(e)}")

    def summarize_text(self, text):
        """
        GPT를 사용하여 텍스트의 핵심 의미를 유지하면서 요약
        """
        try:
            prompt = f"""
            다음 장면 설명의 핵심 시각적 요소들만 간단히 추출해주세요. 
            가장 중요한 시각적 특징 3-4개만 포함하여 한 문장으로 만들어주세요.

            장면 설명:
            {text}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            logging.info(f"원본 텍스트: {text[:100]}...")
            logging.info(f"요약된 텍스트: {summary}")
            return summary
            
        except Exception as e:
            logging.error(f"텍스트 요약 중 오류 발생: {str(e)}")
            return text[:77]  # 요약 실패시 기본 truncation

    def validate_image(self, image_url, prompt):
        try:
            import requests
            
            # 이미지 다운로드
            response = requests.get(image_url)
            image = Image.open(requests.get(image_url, stream=True).raw)
            
            # 프롬프트 의미적 요약
            summarized_prompt = self.summarize_text(prompt)
            
            # 입력 처리
            inputs = self.processor(
                images=image,
                text=[summarized_prompt],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=77
            ).to(self.device)
            
            # 유사도 계산
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = torch.nn.functional.softmax(logits_per_image, dim=1)
                similarity = probs[0][0].item()
            
            suggestions = []
            if similarity < 0.7:
                if similarity < 0.5:
                    try:
                        # GPT를 사용하여 구체적인 개선 제안 생성
                        suggestion_prompt = f"""
                        이미지와 프롬프트의 일치도가 낮습니다 ({similarity:.2f}). 
                        다음 프롬프트를 분석하여, 이미지 생성에 더 효과적인 방향으로 
                        개선할 수 있는 구체적인 제안사항을 2-3개 제시해주세요:

                        프롬프트: {prompt}
                        """
                        
                        response = self.client.chat.completions.create(
                            model="gpt-4",
                            messages=[{"role": "user", "content": suggestion_prompt}],
                            max_tokens=150,
                            temperature=0.7
                        )
                        
                        improvement_suggestions = response.choices[0].message.content.strip().split('\n')
                        suggestions.extend(improvement_suggestions)
                    except:
                        suggestions.append("프롬프트를 더 구체적이고 시각적인 설명으로 개선해보세요.")
            
            return {
                "similarity_score": similarity,
                "meets_requirements": similarity >= 0.7,
                "suggestions": suggestions,
                "summarized_prompt": summarized_prompt  # 디버깅용 요약된 프롬프트 포함
            }
            
        except Exception as e:
            logging.error(f"이미지 검증 중 오류 발생: {str(e)}")
            return {
                "similarity_score": 0.0,
                "meets_requirements": False,
                "suggestions": [f"이미지 검증 실패: {str(e)}"],
                "summarized_prompt": None
            }

    def enhance_prompt(self, prompt, style, mood):
        """
        프롬프트를 개선하고 시각적 요소를 강화
        """
        try:
            enhancement_prompt = f"""
            다음 장면 설명을 이미지 생성에 더 적합하도록 개선해주세요.
            시각적으로 명확한 요소들을 강조하고, 
            스타일({style})과 분위기({mood})를 자연스럽게 반영해주세요.
            
            원본 설명:
            {prompt}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": enhancement_prompt}],
                max_tokens=200,
                temperature=0.7
            )
            
            enhanced_prompt = response.choices[0].message.content.strip()
            return enhanced_prompt
            
        except Exception as e:
            logging.error(f"프롬프트 개선 중 오류 발생: {str(e)}")
            return prompt