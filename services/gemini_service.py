import logging
import asyncio
import google.generativeai as genai
from config.settings import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# --- Gemini AI 설정 ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 기본 번역 사전 (API 실패 시 사용)
BASIC_TRANSLATIONS = {
    "안녕": {"russian": "Привет", "pronunciation": "프리볍"},
    "안녕하세요": {"russian": "Здравствуйте", "pronunciation": "즈드라스트부이체"},
    "감사합니다": {"russian": "Спасибо", "pronunciation": "스파시바"},
    "죄송합니다": {"russian": "Извините", "pronunciation": "이즈비니체"},
    "네": {"russian": "Да", "pronunciation": "다"},
    "아니요": {"russian": "Нет", "pronunciation": "녜트"},
    "좋아요": {"russian": "Хорошо", "pronunciation": "하라쇼"},
    "물": {"russian": "Вода", "pronunciation": "바다"},
    "빵": {"russian": "Хлеб", "pronunciation": "흘렙"},
    "커피": {"russian": "Кофе", "pronunciation": "꼬페"},
    "차": {"russian": "Чай", "pronunciation": "차이"},
    "집": {"russian": "Дом", "pronunciation": "돔"},
    "학교": {"russian": "Школа", "pronunciation": "슈콜라"},
    "친구": {"russian": "Друг", "pronunciation": "드룩"},
    "사랑": {"russian": "Любовь", "pronunciation": "류보비"}
}

def get_basic_translation(text: str) -> str:
    """기본 번역 사전에서 번역 찾기"""
    text_clean = text.strip().lower()
    for korean, russian_data in BASIC_TRANSLATIONS.items():
        if korean in text_clean:
            return f"**{russian_data['russian']}** [{russian_data['pronunciation']}]"
    return None

def _sync_call_gemini(prompt: str) -> str:
    """동기적으로 Gemini AI를 호출하는 함수"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API 오류: {e}")
        
        # 번역 요청인 경우 기본 번역 시도
        if "번역" in prompt and any(word in prompt for word in BASIC_TRANSLATIONS.keys()):
            for word in BASIC_TRANSLATIONS.keys():
                if word in prompt:
                    basic_trans = get_basic_translation(word)
                    if basic_trans:
                        return f"🔄 기본 번역: {basic_trans}\n\n💡 AI 서비스 일시 중단으로 기본 번역을 제공했습니다."
        
        return "죄송합니다. AI 모델과 통신 중 오류가 발생했습니다. 😅"

async def call_gemini(prompt: str) -> str:
    """Gemini AI에 프롬프트를 전송하고 응답을 받아오는 함수 (비동기 래퍼)"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_call_gemini, prompt) 