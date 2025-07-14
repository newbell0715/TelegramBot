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

# --- 명령어 설명 및 기능 ---
COMMAND_DESCRIPTIONS = {
    'start': {
        'name': '시작하기',
        'emoji': '🚀',
        'description': '봇을 시작하고 인사말과 주요 기능을 확인합니다',
        'usage': '/start',
        'features': ['봇 초기화', '환영 메시지', '주요 기능 소개']
    },
    'help': {
        'name': '도움말',
        'emoji': '❓',
        'description': '모든 명령어와 사용법을 상세히 안내합니다',
        'usage': '/help',
        'features': ['전체 명령어 목록', '사용법 안내', '예시 제공']
    },
    'quest': {
        'name': '스토리 퀘스트',
        'emoji': '🏆',
        'description': '실제 상황을 시뮬레이션하여 러시아어 회화를 학습합니다',
        'usage': '/quest',
        'features': ['대화형 스토리', '단계별 학습', '실전 회화 연습', '힌트 제공']
    },
    'action': {
        'name': '퀘스트 행동',
        'emoji': '💬',
        'description': '퀘스트에서 상황에 맞는 대답을 입력합니다',
        'usage': '/action [러시아어 문장]',
        'features': ['상황별 대화', '키워드 인식', '자동 진행', '피드백 제공']
    },
    'write': {
        'name': 'AI 작문 교정',
        'emoji': '✍️',
        'description': '러시아어 문장을 AI가 문법과 표현을 교정해줍니다',
        'usage': '/write [러시아어 문장]',
        'features': ['문법 검사', '자연스러운 표현 제안', '상세한 설명', '칭찬과 동기부여']
    },
    'trs': {
        'name': '간단 번역',
        'emoji': '⚡',
        'description': '빠르고 정확한 번역을 제공합니다',
        'usage': '/trs [언어] [텍스트]',
        'features': ['즉시 번역', '다국어 지원', '깔끔한 결과', '언어 자동인식']
    },
    'trl': {
        'name': '상세 번역',
        'emoji': '📚',
        'description': '번역과 함께 문법 분석과 단어 설명을 제공합니다',
        'usage': '/trl [언어] [텍스트]',
        'features': ['상세 문법 분석', '단어별 설명', '여러 번역 제안', '학습 효과 극대화']
    },
    'ls': {
        'name': '음성 변환',
        'emoji': '🎵',
        'description': '텍스트를 자연스러운 음성으로 변환합니다',
        'usage': '/ls [텍스트]',
        'features': ['한국어/러시아어 TTS', '자동 언어 감지', '고품질 음성', '발음 학습 지원']
    },
    'trls': {
        'name': '번역+음성',
        'emoji': '🔊',
        'description': '번역과 음성 변환을 한번에 제공합니다',
        'usage': '/trls [언어] [텍스트]',
        'features': ['번역 + TTS', '학습 최적화', '발음 연습', '효율적 학습']
    },
    'quiz': {
        'name': '러시아어 퀴즈',
        'emoji': '🧠',
        'description': '단어, 문법, 발음 퀴즈로 실력을 테스트합니다',
        'usage': '/quiz [카테고리]',
        'features': ['다양한 카테고리', '점수 시스템', '랭킹', 'AI 생성 문제']
    },
    'leaderboard': {
        'name': '리더보드',
        'emoji': '🏅',
        'description': '퀴즈 점수와 학습 활동 순위를 확인합니다',
        'usage': '/leaderboard',
        'features': ['실시간 순위', '다양한 카테고리', '경쟁 요소', '동기부여']
    },
    'my_progress': {
        'name': '학습 진도',
        'emoji': '📊',
        'description': '개인 학습 통계와 성과를 확인합니다',
        'usage': '/my_progress',
        'features': ['상세 통계', '성장 그래프', '달성도', '개인화 피드백']
    },
    'subscribe_daily': {
        'name': '일일 학습 구독',
        'emoji': '📅',
        'description': '매일 러시아어 학습 콘텐츠를 받아봅니다',
        'usage': '/subscribe_daily',
        'features': ['매일 새로운 단어', '회화 예문', '정기 학습', '습관 형성']
    },
    'model_status': {
        'name': 'AI 모델 상태',
        'emoji': '🤖',
        'description': '현재 사용 중인 AI 모델의 상태를 확인합니다',
        'usage': '/model_status',
        'features': ['실시간 상태', '모델 정보', '성능 지표', '시스템 모니터링']
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