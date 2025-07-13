import logging
import asyncio
import google.generativeai as genai
from config.settings import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# --- Gemini AI 설정 ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

def _sync_call_gemini(prompt: str) -> str:
    """동기적으로 Gemini AI를 호출하는 함수"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API 오류: {e}")
        return "죄송합니다. AI 모델과 통신 중 오류가 발생했습니다. 😅"

async def call_gemini(prompt: str) -> str:
    """Gemini AI에 프롬프트를 전송하고 응답을 받아오는 함수 (비동기 래퍼)"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_call_gemini, prompt) 