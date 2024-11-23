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

    def enhance_prompt(self, prompt, style, mood):
        """
        프롬프트를 개선하고 시각적 요소를 강화하는 메소드
        
        Parameters:
            prompt (str): 원본 프롬프트
            style (str): 원하는 스타일
            mood (str): 원하는 분위기
        
        Returns:
            str: 개선된 프롬프트
        """
        try:
            # 먼저 핵심 요소들 추출
            key_elements = self.extract_key_elements(prompt)
            
            enhancement_prompt = f"""
            다음 장면 설명을 개선해주세요:
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
                model="gpt-4",
                messages=[{"role": "user", "content": enhancement_prompt}],
                max_tokens=300,
                temperature=0.7
            )
            
            enhanced_prompt = response.choices[0].message.content.strip()
            
            logging.info(f"원본 프롬프트: {prompt[:100]}...")
            logging.info(f"추출된 핵심 요소: {key_elements}")
            logging.info(f"개선된 프롬프트: {enhanced_prompt[:100]}...")
            
            return enhanced_prompt
            
        except Exception as e:
            logging.error(f"프롬프트 개선 중 오류 발생: {str(e)}")
            return prompt

    def extract_key_elements(self, text):
        """텍스트에서 핵심적인 시각적 요소들을 추출"""
        try:
            prompt = f"""
            다음 장면에서 가장 중요한 시각적 요소들만 추출해주세요.
            순서대로 중요도를 평가하여 가장 중요한 3-4개의 요소만 선택하세요:
            1. 캐릭터의 주요 행동과 상호작용
            2. 캐릭터의 감정과 표정
            3. 주요 배경 요소
            4. 전체적인 분위기

            장면:
            {text}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"핵심 요소 추출 중 오류: {str(e)}")
            return text

    def summarize_text(self, text):
        """텍스트의 핵심 시각적 요소를 유지하며 CLIP에 적합하게 요약"""
        try:
            # 먼저 핵심 요소 추출
            key_elements = self.extract_key_elements(text)
            
            # 추출된 요소들을 CLIP 형식으로 변환
            prompt = f"""
            다음 시각적 요소들을 CLIP이 이해하기 쉽도록 77자 이내의 간단한 문장으로 만들어주세요.
            - 접속사나 불필요한 수식어는 제거
            - 행동, 감정, 상황을 명확하게 표현
            - 구체적인 시각적 디테일 유지
            - 중요한 순서대로 배치

            핵심 요소들:
            {key_elements}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            
            # 토큰 수 체크 및 필요시 추가 축소
            if len(summary) > 77:
                trim_prompt = f"""
                다음 설명을 77자 이내로 줄이되, 
                가장 중요한 행동과 감정 표현을 유지하세요:

                {summary}
                """
                
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": trim_prompt}],
                    max_tokens=100,
                    temperature=0.3
                )
                summary = response.choices[0].message.content.strip()
            
            logging.info(f"원본 텍스트: {text[:100]}...")
            logging.info(f"추출된 핵심 요소: {key_elements}")
            logging.info(f"최종 요약: {summary}")
            return summary
            
        except Exception as e:
            logging.error(f"텍스트 요약 중 오류: {str(e)}")
            text_truncated = text[:77]  
            last_period = text_truncated.rfind('.')
            last_comma = text_truncated.rfind(',')
            cut_point = max(last_period, last_comma)
            if cut_point > 30:
                return text_truncated[:cut_point + 1]
            return text_truncated

    def validate_image(self, image_url, prompt):
        """이미지와 프롬프트의 일치도를 검증"""
        try:
            import requests
            
            # 이미지 다운로드
            response = requests.get(image_url)
            image = Image.open(requests.get(image_url, stream=True).raw)
            
            # 프롬프트에서 핵심 시각 요소 추출 및 요약
            key_elements = self.extract_key_elements(prompt)
            summarized_prompt = self.summarize_text(key_elements)
            
            # 입력 처리
            inputs = self.processor(
                images=image,
                text=[summarized_prompt],
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            # 유사도 계산
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = torch.nn.functional.softmax(logits_per_image, dim=1)
                similarity = probs[0][0].item()
            
            suggestions = []
            if similarity < 0.7:
                try:
                    suggestion_prompt = f"""
                    이미지와 프롬프트의 유사도가 {similarity:.2f}입니다.
                    다음 요소들을 기반으로 이미지 생성을 개선할 방법을 제안해주세요:

                    핵심 요소:
                    {key_elements}

                    현재 요약:
                    {summarized_prompt}

                    각 요소별로 구체적인 개선 방안을 1-2개 제시해주세요.
                    """
                    
                    response = self.client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": suggestion_prompt}],
                        max_tokens=200,
                        temperature=0.7
                    )
                    
                    suggestions.extend(response.choices[0].message.content.strip().split('\n'))
                except:
                    suggestions.append("핵심 시각적 요소들의 표현을 더 구체화해주세요.")
            
            return {
                "similarity_score": similarity,
                "meets_requirements": similarity >= 0.7,
                "suggestions": suggestions,
                "key_elements": key_elements,
                "summarized_prompt": summarized_prompt
            }
            
        except Exception as e:
            logging.error(f"이미지 검증 중 오류: {str(e)}")
            return {
                "similarity_score": 0.0,
                "meets_requirements": False,
                "suggestions": [f"이미지 검증 실패: {str(e)}"],
                "key_elements": None,
                "summarized_prompt": None
            }