import pytz

# --- API 키 및 토큰 ---
GEMINI_API_KEY = "AIzaSyCmH1flv0HSRp8xYa1Y8oL7xnpyyQVuIw8"
BOT_TOKEN = "8064422632:AAFkFqQDA_35OCa5-BFxeHPA9_hil4cY8Rg"

# --- 시간대 설정 ---
MSK = pytz.timezone('Europe/Moscow')

# --- 데이터 파일 및 상수 ---
USER_DATA_FILE = 'user_data.json'

# --- 퀘스트 데이터 ---
QUEST_DATA = {
    'q1': {
        'title': "카페에서 주문하기",
        'stages': {
            1: {
                'description': "당신은 모스크바의 한 카페에 들어왔습니다. 점원이 인사를 건넵니다. 뭐라고 답해야 할까요?",
                'bot_message': "Здравствуйте! Что будете заказывать? (안녕하세요! 무엇을 주문하시겠어요?)",
                'action_prompt': "인사하고 커피를 주문해보세요. (예: 안녕하세요, 아메리카노 한 잔 주세요.)",
                'keywords': ['кофе', 'американо', 'латте', 'капучино', 'чай']
            },
            2: {
                'description': "주문을 완료했습니다! 이제 점원이 결제를 요청합니다.",
                'bot_message': "Отлично! С вас 300 рублей. (좋아요! 300루블입니다.)",
                'action_prompt': "카드로 계산하겠다고 말해보세요.",
                'keywords': ['карта', 'картой']
            },
            3: {
                'description': "결제까지 마쳤습니다. 잠시 후 점원이 주문한 음료가 나왔다고 알려줍니다.",
                'bot_message': "Ваш кофе готов! (주문하신 커피 나왔습니다!)",
                'action_prompt': "감사를 표하고 퀘스트를 완료하세요!",
                'keywords': ['спасибо', 'благодарю']
            }
        }
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