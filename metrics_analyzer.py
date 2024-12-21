import logging
from PIL import Image
import numpy as np
from io import BytesIO
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional
import streamlit as st
import cv2

@dataclass
class GenerationMetrics:
    clip_score: float
    generation_time: float
    attempt_count: int
    success: bool

@dataclass
class ImageQualityMetrics:
    sharpness: float
    contrast: float
    color_diversity: float
    composition_balance: float

@dataclass
class SceneContinuityMetrics:
    style_consistency: float
    character_consistency: float
    visual_coherence: float

@dataclass
class UserFeedbackMetrics:
    overall_satisfaction: int
    style_accuracy: int
    story_coherence: int
    visual_quality: int

class MetricsAnalyzer:
    def __init__(self):
        self.setup_logging()
        self.session_metrics = {
            'generation_metrics': [],
            'image_quality_metrics': [],
            'scene_continuity_metrics': None,
            'user_feedback': None,
            'timestamp': datetime.now()
        }

    @staticmethod
    def setup_logging():
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def calculate_image_metrics(self, image_url: str) -> ImageQualityMetrics:
        """이미지 품질 관련 메트릭 계산"""
        try:
            # 이미지 다운로드
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content))
            img_array = np.array(image)
            
            # OpenCV로 변환
            if len(img_array.shape) == 3:
                img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                img_gray = img_array

            # 선명도 계산
            laplacian_var = cv2.Laplacian(img_gray, cv2.CV_64F).var()
            sharpness = min(laplacian_var / 1000, 1.0)  # 정규화

            # 대비 계산
            contrast = img_gray.std() / 128  # 정규화

            # 색상 다양성 계산
            if len(img_array.shape) == 3:
                unique_colors = len(np.unique(img_array.reshape(-1, img_array.shape[-1]), axis=0))
                color_diversity = min(unique_colors / 1000, 1.0)  # 정규화
            else:
                color_diversity = 0.0

            # 구도 균형 계산 (중심점 기준)
            height, width = img_gray.shape
            center_y, center_x = height // 2, width // 2
            quadrants = [
                img_gray[:center_y, :center_x].mean(),
                img_gray[:center_y, center_x:].mean(),
                img_gray[center_y:, :center_x].mean(),
                img_gray[center_y:, center_x:].mean()
            ]
            composition_balance = 1 - (max(quadrants) - min(quadrants)) / 255

            return ImageQualityMetrics(
                sharpness=float(sharpness),
                contrast=float(contrast),
                color_diversity=float(color_diversity),
                composition_balance=float(composition_balance)
            )

        except Exception as e:
            logging.error(f"이미지 메트릭 계산 실패: {str(e)}")
            return ImageQualityMetrics(0.0, 0.0, 0.0, 0.0)

    def track_generation_metrics(self, clip_score: float, generation_time: float, 
                               attempt_count: int) -> GenerationMetrics:
        """생성 과정 메트릭 추적"""
        metrics = GenerationMetrics(
            clip_score=clip_score,
            generation_time=generation_time,
            attempt_count=attempt_count,
            success=clip_score >= 0.7
        )
        
        self.session_metrics['generation_metrics'].append(metrics)
        return metrics

    def evaluate_scene_continuity(self, scene_sequence: List[str]) -> SceneContinuityMetrics:
        """장면 연속성 평가"""
        try:
            if len(scene_sequence) < 2:
                return SceneContinuityMetrics(1.0, 1.0, 1.0)

            # 스타일 일관성 계산
            style_scores = []
            for i in range(len(scene_sequence) - 1):
                current_metrics = self.calculate_image_metrics(scene_sequence[i])
                next_metrics = self.calculate_image_metrics(scene_sequence[i + 1])
                
                style_similarity = 1 - abs(current_metrics.color_diversity - next_metrics.color_diversity)
                style_scores.append(style_similarity)

            # 캐릭터 일관성 (이미지 간 특징점 매칭으로 대체)
            character_scores = []
            for i in range(len(scene_sequence) - 1):
                response_current = requests.get(scene_sequence[i])
                response_next = requests.get(scene_sequence[i + 1])
                
                img_current = cv2.imdecode(np.frombuffer(response_current.content, np.uint8), 1)
                img_next = cv2.imdecode(np.frombuffer(response_next.content, np.uint8), 1)

                # SIFT 특징점 검출
                sift = cv2.SIFT_create()
                kp1, des1 = sift.detectAndCompute(img_current, None)
                kp2, des2 = sift.detectAndCompute(img_next, None)

                if des1 is not None and des2 is not None:
                    # 특징점 매칭
                    bf = cv2.BFMatcher()
                    matches = bf.knnMatch(des1, des2, k=2)
                    
                    # 좋은 매칭 선별
                    good_matches = []
                    for m, n in matches:
                        if m.distance < 0.75 * n.distance:
                            good_matches.append(m)
                    
                    character_consistency = len(good_matches) / max(len(kp1), len(kp2))
                    character_scores.append(min(character_consistency, 1.0))
                else:
                    character_scores.append(0.0)

            metrics = SceneContinuityMetrics(
                style_consistency=float(np.mean(style_scores)),
                character_consistency=float(np.mean(character_scores)),
                visual_coherence=float(np.mean([np.mean(style_scores), np.mean(character_scores)]))
            )
            
            self.session_metrics['scene_continuity_metrics'] = metrics
            return metrics

        except Exception as e:
            logging.error(f"장면 연속성 평가 실패: {str(e)}")
            return SceneContinuityMetrics(0.0, 0.0, 0.0)

    def collect_user_feedback(self) -> UserFeedbackMetrics:
        """사용자 피드백 수집"""
        try:
            st.write("### 🎯 생성된 결과 평가")
            feedback = UserFeedbackMetrics(
                overall_satisfaction=st.slider('전반적인 만족도', 1, 5, 3),
                style_accuracy=st.slider('스타일 정확도', 1, 5, 3),
                story_coherence=st.slider('스토리 일관성', 1, 5, 3),
                visual_quality=st.slider('시각적 품질', 1, 5, 3)
            )
            
            self.session_metrics['user_feedback'] = feedback
            return feedback

        except Exception as e:
            logging.error(f"사용자 피드백 수집 실패: {str(e)}")
            return UserFeedbackMetrics(0, 0, 0, 0)

    def get_session_summary(self) -> Dict:
        """세션의 전체 메트릭 요약"""
        try:
            generation_metrics = self.session_metrics['generation_metrics']
            
            summary = {
                'avg_clip_score': np.mean([m.clip_score for m in generation_metrics]),
                'avg_generation_time': np.mean([m.generation_time for m in generation_metrics]),
                'success_rate': len([m for m in generation_metrics if m.success]) / len(generation_metrics),
                'avg_attempts': np.mean([m.attempt_count for m in generation_metrics])
            }

            if self.session_metrics['scene_continuity_metrics']:
                continuity = self.session_metrics['scene_continuity_metrics']
                summary.update({
                    'style_consistency': continuity.style_consistency,
                    'character_consistency': continuity.character_consistency,
                    'visual_coherence': continuity.visual_coherence
                })

            if self.session_metrics['user_feedback']:
                feedback = self.session_metrics['user_feedback']
                summary.update({
                    'user_satisfaction': feedback.overall_satisfaction,
                    'style_accuracy': feedback.style_accuracy,
                    'story_coherence': feedback.story_coherence,
                    'visual_quality': feedback.visual_quality
                })

            return summary

        except Exception as e:
            logging.error(f"세션 요약 생성 실패: {str(e)}")
            return {}