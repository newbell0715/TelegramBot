import os
import pytz
from typing import Dict, Any

# --- API 키 및 토큰 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCmH1flv0HSRp8xYa1Y8oL7xnpyyQVuIw8")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8064422632:AAFkFqQDA_35OCa5-BFxeHPA9_hil4cY8Rg")
ADMIN_USER_IDS = [123456789]  # 관리자 ID 추가

# --- 시간대 설정 ---
MSK = pytz.timezone('Europe/Moscow')

# --- 데이터 파일 및 상수 ---
USER_DATA_FILE = 'user_data.json'
MODEL_STATUS_FILE = 'model_status.json'

# --- 모델 설정 ---
MODEL_CONFIG = [
    {'name': 'gemini-2.5-pro', 'display_name': 'Gemini 2.5 Pro'},
    {'name': 'gemini-1.5-pro-latest', 'display_name': 'Gemini 1.5 Pro'},
    {'name': 'gemini-1.5-flash', 'display_name': 'Gemini 1.5 Flash'}
]

# --- 플랜 설정 ---
PLANS = {
    'Free': {
        'daily_corrections': 5,
        'daily_translations': 10,
        'daily_tts': 5,
        'quiz_attempts': 3,
        'features': ['기본 번역', '간단 교정', '일일 학습']
    },
    'Pro': {
        'daily_corrections': -1,  # 무제한
        'daily_translations': -1,
        'daily_tts': -1,
        'quiz_attempts': -1,
        'features': ['무제한 사용', '고급 교정', '개인화 학습', '우선 지원', '통계 분석']
    },
    'Premium': {
        'daily_corrections': -1,
        'daily_translations': -1,
        'daily_tts': -1,
        'quiz_attempts': -1,
        'features': ['Pro 모든 기능', '실시간 챗봇', '음성 인식', '개인 튜터', '1:1 지원']
    }
}

# --- 확장된 퀘스트 데이터 ---
QUEST_DATA = {
    'easy_cafe': {
        'title': "🟢 [쉬움] 카페에서 주문하기",
        'difficulty': 'easy',
        'reward_exp': 10,
        'stages': {
            1: {
                'description': "당신은 모스크바의 한 카페에 들어왔습니다. 점원이 인사를 건넵니다.",
                'bot_message': "Здравствуйте! Что будете заказывать?",
                'bot_translation': "(안녕하세요! 무엇을 주문하시겠어요?)",
                'action_prompt': "인사하고 커피를 주문해보세요.",
                'keywords': ['кофе', 'американо', 'латте', 'капучино', 'чай', 'привет', 'здравствуйте'],
                'hints': ["커피 = кофе", "주세요 = пожалуйста"]
            },
            2: {
                'description': "주문을 완료했습니다! 이제 점원이 결제를 요청합니다.",
                'bot_message': "Отлично! С вас 300 рублей.",
                'bot_translation': "(좋아요! 300루블입니다.)",
                'action_prompt': "카드로 계산하겠다고 말해보세요.",
                'keywords': ['карта', 'картой', 'оплата'],
                'hints': ["카드 = карта", "계산 = оплата"]
            },
            3: {
                'description': "결제까지 마쳤습니다. 커피가 준비되었다고 알려줍니다.",
                'bot_message': "Ваш кофе готов!",
                'bot_translation': "(주문하신 커피 나왔습니다!)",
                'action_prompt': "감사를 표하고 퀘스트를 완료하세요!",
                'keywords': ['спасибо', 'благодарю'],
                'hints': ["감사합니다 = спасибо"]
            }
        }
    },
    'hard_restaurant': {
        'title': "🔴 [어려움] 레스토랑에서 식사하기",
        'difficulty': 'hard',
        'reward_exp': 25,
        'stages': {
            1: {
                'description': "고급 레스토랑에 예약하고 도착했습니다. 웨이터가 메뉴를 가져다줍니다.",
                'bot_message': "Добро пожаловать! Вот наше меню. Что бы вы хотели заказать на ужин?",
                'bot_translation': "(환영합니다! 여기 메뉴입니다. 저녁으로 무엇을 주문하시겠어요?)",
                'action_prompt': "메뉴를 보고 음식과 음료를 주문해보세요.",
                'keywords': ['борщ', 'блины', 'водка', 'вино', 'заказать', 'хочу'],
                'hints': ["주문하다 = заказать", "원하다 = хотеть"]
            }
        }
    }
}

# --- 퀴즈 데이터 ---
QUIZ_CATEGORIES = {
    'vocabulary': {
        'name': '단어 퀴즈',
        'emoji': '📚',
        'description': '러시아어 단어의 뜻을 맞춰보세요'
    },
    'grammar': {
        'name': '문법 퀴즈', 
        'emoji': '📝',
        'description': '러시아어 문법 규칙을 테스트해보세요'
    },
    'pronunciation': {
        'name': '발음 퀴즈',
        'emoji': '🗣️',
        'description': '올바른 발음을 선택해보세요'
    }
}

# --- 언어 매핑 ---
LANGUAGE_MAPPING = {
    'russian': '러시아어',
    'russia': '러시아어', 
    'ru': '러시아어',
    'english': '영어',
    'en': '영어',
    'korean': '한국어',
    'korea': '한국어',
    'kr': '한국어'
}

# --- 캐시 설정 ---
CACHE_TTL = 3600  # 1시간
MAX_CACHE_SIZE = 1000

# --- UI 요소 ---
EMOJIS = {
    'success': '✅',
    'error': '❌', 
    'warning': '⚠️',
    'info': 'ℹ️',
    'loading': '⏳',
    'fire': '🔥',
    'star': '⭐',
    'trophy': '🏆',
    'medal': '🏅',
    'crown': '👑',
    'gem': '💎'
}

# --- 결제 설정 ---
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")
PRICES = {
    'pro_monthly': 5000,  # 5,000원
    'premium_monthly': 9900,  # 9,900원
    'pro_yearly': 50000,   # 50,000원 (월 4,167원)
    'premium_yearly': 99000  # 99,000원 (월 8,250원)
} 