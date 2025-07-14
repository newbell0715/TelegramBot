import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import google.generativeai as genai
import pytz
from functools import lru_cache
from cachetools import TTLCache

from config.settings import GEMINI_API_KEY, MODEL_CONFIG

logger = logging.getLogger(__name__)

# 응답 캐시 (동일한 프롬프트에 대한 반복 요청 방지)
response_cache = TTLCache(maxsize=500, ttl=1800)  # 30분 캐시

class GeminiService:
    """향상된 Gemini AI 서비스"""
    
    def __init__(self):
        self.model_status = self._load_model_status()
        self.current_model = None
        self._configure_api()
    
    def _load_model_status(self) -> Dict[str, Any]:
        """모델 상태 로드"""
        try:
            if os.path.exists('model_status.json'):
                with open('model_status.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        
        return {
            'current_index': 0,
            'quota_exceeded_time': None,
            'last_primary_attempt': None,
            'failure_count': 0,
            'daily_requests': 0,
            'last_reset_date': datetime.now().date().isoformat()
        }
    
    def _save_model_status(self) -> None:
        """모델 상태 저장"""
        try:
            with open('model_status.json', 'w', encoding='utf-8') as f:
                json.dump(self.model_status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"모델 상태 저장 오류: {e}")
    
    def _configure_api(self) -> None:
        """API 설정"""
        genai.configure(api_key=GEMINI_API_KEY)
        self.current_model = self._get_model()
    
    def _get_model(self, idx: Optional[int] = None) -> genai.GenerativeModel:
        """모델 인스턴스 가져오기"""
        if idx is None:
            idx = self.model_status['current_index']
        
        model_config = MODEL_CONFIG[idx]
        return genai.GenerativeModel(
            model_name=model_config['name'],
            generation_config={
                'temperature': 0.7,
                'top_p': 0.8,
                'top_k': 40,
                'max_output_tokens': 2048,
            }
        )
    
    def _reset_daily_limits(self) -> None:
        """일일 제한 리셋"""
        today = datetime.now().date().isoformat()
        if self.model_status['last_reset_date'] != today:
            self.model_status['daily_requests'] = 0
            self.model_status['last_reset_date'] = today
            self._save_model_status()
    
    def _should_fallback_to_primary(self) -> bool:
        """기본 모델로 복귀할지 확인"""
        if self.model_status['current_index'] == 0:
            return False
        
        # 할당량 초과 후 24시간 경과 시 복귀 시도
        if self.model_status.get('quota_exceeded_time'):
            exceeded_time = datetime.fromisoformat(self.model_status['quota_exceeded_time'])
            if datetime.now() - exceeded_time > timedelta(hours=24):
                return True
        
        return False
    
    async def generate_content(self, prompt: str, use_cache: bool = True) -> str:
        """AI 콘텐츠 생성 (향상된 버전)"""
        # 캐시 확인
        if use_cache and prompt in response_cache:
            logger.info("캐시된 응답 사용")
            return response_cache[prompt]
        
        self._reset_daily_limits()
        
        # 기본 모델 복귀 체크
        if self._should_fallback_to_primary():
            self.model_status['current_index'] = 0
            self.model_status['failure_count'] = 0
            self._save_model_status()
        
        # 모델별로 시도
        for idx in range(self.model_status['current_index'], len(MODEL_CONFIG)):
            try:
                model = self._get_model(idx)
                
                # 비동기 실행
                response = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: model.generate_content(prompt)
                )
                
                if response and response.text:
                    # 성공 시 통계 업데이트
                    self.model_status['daily_requests'] += 1
                    if idx != 0:
                        # 폴백 모델 성공 시 다음에 기본 모델 시도
                        self.model_status['current_index'] = 0
                        self.model_status['failure_count'] = 0
                    
                    self._save_model_status()
                    
                    # 캐시 저장
                    if use_cache:
                        response_cache[prompt] = response.text
                    
                    logger.info(f"✅ {MODEL_CONFIG[idx]['display_name']} 사용 성공")
                    return response.text
                
            except Exception as e:
                error_str = str(e).lower()
                logger.error(f"❌ {MODEL_CONFIG[idx]['display_name']} 에러: {e}")
                
                # 할당량/429/404 에러 시 다음 모델로
                if any(keyword in error_str for keyword in 
                       ['quota', '429', 'rate limit', 'resource_exhausted', 'not found', '404']):
                    self.model_status['current_index'] = idx + 1
                    self.model_status['quota_exceeded_time'] = datetime.now().isoformat()
                    self.model_status['failure_count'] = 0
                    self._save_model_status()
                    continue
                
                # 기타 에러의 경우 재시도 카운트 증가
                self.model_status['failure_count'] += 1
                self._save_model_status()
                
                if self.model_status['failure_count'] >= 3 and idx < len(MODEL_CONFIG) - 1:
                    self.model_status['current_index'] = idx + 1
                    self.model_status['failure_count'] = 0
                    self._save_model_status()
                    continue
                
                # 재시도 로직
                if self.model_status['failure_count'] < 3:
                    await asyncio.sleep(2 ** self.model_status['failure_count'])  # 지수 백오프
                    continue
        
        # 모든 모델 실패
        return self._get_fallback_response()
    
    def _get_fallback_response(self) -> str:
        """폴백 응답"""
        return "죄송합니다. 현재 AI 서비스에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요. 😅"
    
    async def translate_text(self, text: str, target_language: str, detailed: bool = False) -> str:
        """번역 서비스"""
        if detailed:
            prompt = f"""
다음 텍스트를 {target_language}로 번역해주세요: {text}

다음 형식으로 답변해주세요:
1. 번역: [자연스러운 번역]
2. 대안 번역: [다른 표현]
3. 문법 설명: [주요 문법 포인트]
4. 발음 가이드: [발음 도움말]
"""
        else:
            prompt = f"다음 텍스트를 {target_language}로 자연스럽게 번역해주세요: {text}"
        
        return await self.generate_content(prompt)
    
    async def correct_writing(self, text: str, language: str = "러시아어") -> str:
        """작문 교정 서비스"""
        prompt = f"""
당신은 친절한 {language} 원어민 선생님입니다. 다음 문장을 교정해주세요:

학생 문장: "{text}"

다음 형식으로 답변해주세요:
📝 **원본**: {text}
✨ **교정**: [올바른 문장]
📊 **점수**: [1-10점]
💡 **설명**: [구체적인 교정 이유]
🎯 **팁**: [학습에 도움되는 조언]
"""
        return await self.generate_content(prompt)
    
    async def generate_quiz_question(self, category: str, difficulty: str = "medium") -> str:
        """퀴즈 질문 생성"""
        prompt = f"""
{difficulty} 난이도의 러시아어 {category} 퀴즈를 만들어주세요.

형식:
❓ **문제**: [질문]
A) [선택지1]
B) [선택지2] 
C) [선택지3]
D) [선택지4]

정답: [정답 설명]
"""
        return await self.generate_content(prompt)
    
    async def chat_response(self, message: str, context: Optional[str] = None) -> str:
        """자연스러운 대화 응답"""
        if context:
            prompt = f"이전 대화 맥락: {context}\n\n사용자 메시지: {message}\n\n친근하고 도움이 되는 응답을 해주세요."
        else:
            prompt = f"사용자 메시지: {message}\n\n친근하고 도움이 되는 응답을 해주세요."
        
        return await self.generate_content(prompt, use_cache=False)
    
    def get_status(self) -> Dict[str, Any]:
        """서비스 상태 정보"""
        current_model = MODEL_CONFIG[self.model_status['current_index']]['display_name']
        
        return {
            'current_model': current_model,
            'daily_requests': self.model_status['daily_requests'],
            'is_primary': self.model_status['current_index'] == 0,
            'failure_count': self.model_status['failure_count'],
            'cache_size': len(response_cache),
            'last_reset': self.model_status['last_reset_date']
        }

# 전역 인스턴스
gemini_service = GeminiService()

# 편의 함수들
async def call_gemini(prompt: str) -> str:
    """기본 Gemini 호출"""
    return await gemini_service.generate_content(prompt)

async def translate_with_gemini(text: str, target_language: str, detailed: bool = False) -> str:
    """번역 호출"""
    return await gemini_service.translate_text(text, target_language, detailed)

async def correct_with_gemini(text: str) -> str:
    """교정 호출"""
    return await gemini_service.correct_writing(text)

async def chat_with_gemini(message: str, context: Optional[str] = None) -> str:
    """채팅 호출"""
    return await gemini_service.chat_response(message, context) 