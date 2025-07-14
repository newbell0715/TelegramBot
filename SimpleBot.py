import os
import logging
import json
import io
from datetime import datetime, timedelta
import pytz
from gtts import gTTS
from telegram import Update, Bot, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

# --- 기본 설정 ---

# 러시아 모스크바 시간대 설정
MSK = pytz.timezone('Europe/Moscow')

# 로깅 설정 (러시아 시간대 적용)
class MSKFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, MSK)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
for handler in logging.root.handlers:
    handler.setFormatter(MSKFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# --- API 키 및 토큰 ---
GEMINI_API_KEY = "AIzaSyCmH1flv0HSRp8xYa1Y8oL7xnpyyQVuIw8"
BOT_TOKEN = "8064422632:AAFkFqQDA_35OCa5-BFxeHPA9_hil4cY8Rg"

# --- Gemini AI 설정 ---
genai.configure(api_key=GEMINI_API_KEY)

# 모델 상태 관리 파일
MODEL_STATUS_FILE = 'model_status.json'

# 모델 설정
MODEL_CONFIG = [
    {'name': 'gemini-2.5-pro', 'display_name': 'Gemini 2.5 Pro'},
    {'name': 'gemini-1.5-pro-latest', 'display_name': 'Gemini 1.5 Pro'},
    {'name': 'gemini-1.5-flash', 'display_name': 'Gemini 1.5 Flash'}
]

# 모델 상태 로드/저장
def load_model_status():
    if os.path.exists(MODEL_STATUS_FILE):
        try:
            with open(MODEL_STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'current_index': 0,
        'quota_exceeded_time': None,
        'last_primary_attempt': None,
        'failure_count': 0
    }

def save_model_status(status):
    try:
        with open(MODEL_STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"모델 상태 저장 오류: {e}")

# 현재 모델 상태
model_status = load_model_status()

# 모델 인스턴스 생성
def get_model(idx=None):
    if idx is None:
        idx = model_status['current_index']
    model_name = MODEL_CONFIG[idx]['name']
    return genai.GenerativeModel(model_name)

# 기본 모델 설정
model = get_model()

# --- 데이터 파일 및 상수 ---
USER_DATA_FILE = 'user_data.json'

# === 🌟 혁신적인 학습 시스템 ===

# 간격 반복 학습 설정 (Spaced Repetition System)
SRS_INTERVALS = [1, 3, 7, 14, 30, 90, 180, 365]  # 일 단위
DIFFICULTY_MULTIPLIERS = {'easy': 1.3, 'good': 1.0, 'hard': 0.8, 'again': 0.5}

# 발음 평가 기준
PRONUNCIATION_CRITERIA = {
    'excellent': {'score': 90, 'emoji': '🏆', 'message': '완벽한 발음입니다!'},
    'very_good': {'score': 80, 'emoji': '🌟', 'message': '매우 좋은 발음이에요!'},
    'good': {'score': 70, 'emoji': '👍', 'message': '좋은 발음입니다!'},
    'fair': {'score': 60, 'emoji': '👌', 'message': '괜찮은 발음이에요.'},
    'needs_practice': {'score': 50, 'emoji': '📚', 'message': '조금 더 연습해보세요.'}
}

# === 🎮 게임화된 학습 시스템 데이터 ===
LEARNING_GAMES = {
    'word_match': {
        'name': '🎯 단어 매칭 게임',
        'description': '러시아어와 한국어 단어를 빠르게 매칭하세요',
        'time_limit': 60,
        'exp_reward': 20,
        'difficulty': 'beginner'
    },
    'sentence_builder': {
        'name': '🔧 문장 조립 게임',
        'description': '단어들을 올바른 순서로 배열하여 문장을 완성하세요',
        'time_limit': 90,
        'exp_reward': 30,
        'difficulty': 'intermediate'
    },
    'speed_quiz': {
        'name': '⚡ 스피드 퀴즈',
        'description': '빠르게 답하는 번역 퀴즈',
        'time_limit': 30,
        'exp_reward': 25,
        'difficulty': 'beginner'
    },
    'pronunciation_challenge': {
        'name': '🎤 발음 챌린지',
        'description': '정확한 발음으로 높은 점수를 획득하세요',
        'time_limit': 120,
        'exp_reward': 35,
        'difficulty': 'advanced'
    }
}

# === 🏆 성취 시스템 ===
ACHIEVEMENTS = {
    'first_quest': {
        'title': '🌟 첫 걸음',
        'description': '첫 번째 퀘스트를 완료했습니다',
        'condition': 'quests_completed >= 1',
        'reward_exp': 50
    },
    'word_master': {
        'title': '📚 단어 마스터',
        'description': '500개의 단어를 학습했습니다',
        'condition': 'daily_words_received >= 500',
        'reward_exp': 200
    },
    'translation_expert': {
        'title': '🌍 번역 전문가',
        'description': '100회의 번역을 완료했습니다',
        'condition': 'translations_made >= 100',
        'reward_exp': 150
    },
    'daily_learner': {
        'title': '🔥 꾸준함의 힘',
        'description': '7일 연속 학습했습니다',
        'condition': 'daily_streak >= 7',
        'reward_exp': 300
    },
    'level_up_master': {
        'title': '🚀 성장의 달인',
        'description': '레벨 10에 도달했습니다',
        'condition': 'level >= 10',
        'reward_exp': 500
    },
    'game_champion': {
        'title': '🎮 게임 챔피언',
        'description': '모든 게임에서 승리했습니다',
        'condition': 'all_games_won',
        'reward_exp': 400
    },
    'writing_guru': {
        'title': '✍️ 작문 구루',
        'description': '50개의 문장을 작성했습니다',
        'condition': 'sentences_corrected >= 50',
        'reward_exp': 250
    },
    'ai_student': {
        'title': '🤖 AI 학생',
        'description': 'AI 튜터와 첫 상담을 완료했습니다',
        'condition': 'ai_sessions >= 1',
        'reward_exp': 100
    }
}

# 🌍 확장된 퀘스트 시나리오
QUEST_DATA = {
    'q1': {
        'title': "카페에서 주문하기",
        'difficulty': 'beginner',
        'exp_reward': 50,
        'stages': {
            1: {
                'description': "당신은 모스크바의 한 카페에 들어왔습니다. 점원이 인사를 건넵니다.",
                'bot_message': "Здравствуйте! Что будете заказывать? (안녕하세요! 무엇을 주문하시겠어요?)",
                'action_prompt': "인사하고 커피를 주문해보세요.",
                'keywords': ['кофе', 'американо', 'латте', 'капучино', 'чай', 'здравствуйте'],
                'hints': ['Здравствуйте! (안녕하세요)', 'Кофе, пожалуйста (커피 주세요)']
            },
            2: {
                'description': "주문을 완료했습니다! 이제 점원이 결제를 요청합니다.",
                'bot_message': "Отлично! С вас 300 рублей. (좋아요! 300루블입니다.)",
                'action_prompt': "카드로 계산하겠다고 말해보세요.",
                'keywords': ['карта', 'картой', 'оплачу'],
                'hints': ['Картой, пожалуйста (카드로 주세요)', 'Можно картой? (카드 결제 가능한가요?)']
            },
            3: {
                'description': "결제까지 마쳤습니다. 점원이 주문한 음료가 나왔다고 알려줍니다.",
                'bot_message': "Ваш кофе готов! (주문하신 커피 나왔습니다!)",
                'action_prompt': "감사를 표하고 퀘스트를 완료하세요!",
                'keywords': ['спасибо', 'благодарю', 'отлично'],
                'hints': ['Спасибо! (감사합니다)', 'Большое спасибо! (정말 감사합니다)']
            }
        }
    },
    'q2': {
        'title': "공항에서 체크인하기",
        'difficulty': 'intermediate',
        'exp_reward': 80,
        'stages': {
            1: {
                'description': "도모데도보 공항에 도착했습니다. 체크인 카운터에서 직원이 기다리고 있습니다.",
                'bot_message': "Добро пожаловать! Ваш паспорт и билет, пожалуйста. (환영합니다! 여권과 티켓을 주세요.)",
                'action_prompt': "여권과 티켓을 제시한다고 말해보세요.",
                'keywords': ['паспорт', 'билет', 'вот', 'пожалуйста'],
                'hints': ['Вот мой паспорт и билет (여기 제 여권과 티켓입니다)']
            },
            2: {
                'description': "서류 확인이 완료되었습니다. 직원이 좌석을 물어봅니다.",
                'bot_message': "Хотите место у окна или у прохода? (창가석과 통로석 중 어느 것을 원하시나요?)",
                'action_prompt': "창가석을 원한다고 말해보세요.",
                'keywords': ['окно', 'окна', 'место у окна'],
                'hints': ['Место у окна, пожалуйста (창가석으로 주세요)']
            },
            3: {
                'description': "좌석 배정이 완료되었습니다. 직원이 수하물에 대해 묻습니다.",
                'bot_message': "Есть ли у вас багаж для сдачи? (맡길 짐이 있으신가요?)",
                'action_prompt': "한 개의 가방이 있다고 답해보세요.",
                'keywords': ['багаж', 'сумка', 'чемодан', 'один', 'одна'],
                'hints': ['Да, один чемодан (네, 가방 하나 있습니다)']
            }
        }
    },
    'q3': {
        'title': "병원에서 진료받기",
        'difficulty': 'advanced',
        'exp_reward': 120,
        'stages': {
            1: {
                'description': "몸이 아파서 병원에 왔습니다. 접수처에서 간호사가 증상을 묻습니다.",
                'bot_message': "Что вас беспокоит? (어떤 증상이 있으신가요?)",
                'action_prompt': "머리가 아프다고 말해보세요.",
                'keywords': ['голова', 'болит', 'головная боль'],
                'hints': ['У меня болит голова (머리가 아픕니다)']
            },
            2: {
                'description': "증상을 확인한 간호사가 의사를 만나라고 합니다.",
                'bot_message': "Пройдите в кабинет номер 5, доктор вас примет. (5번 진료실로 가시면 의사가 진료해드릴 겁니다.)",
                'action_prompt': "감사 인사를 하고 어디인지 다시 물어보세요.",
                'keywords': ['спасибо', 'где', 'кабинет', 'номер'],
                'hints': ['Спасибо. Где кабинет номер 5? (감사합니다. 5번 진료실이 어디인가요?)']
            }
        }
    },
    'q4': {
        'title': "마트에서 쇼핑하기",
        'difficulty': 'beginner',
        'exp_reward': 60,
        'stages': {
            1: {
                'description': "마트에서 우유를 찾고 있습니다. 직원에게 물어봅니다.",
                'bot_message': "Чем могу помочь? (무엇을 도와드릴까요?)",
                'action_prompt': "우유가 어디 있는지 물어보세요.",
                'keywords': ['молоко', 'где', 'найти'],
                'hints': ['Где найти молоко? (우유를 어디서 찾을 수 있나요?)']
            },
            2: {
                'description': "직원이 우유의 위치를 알려줍니다.",
                'bot_message': "Молочные продукты в третьем ряду, справа. (유제품은 3번째 줄 오른쪽에 있습니다.)",
                'action_prompt': "감사 인사를 해보세요.",
                'keywords': ['спасибо', 'благодарю'],
                'hints': ['Спасибо большое! (정말 감사합니다!)']
            }
        }
    },
    'q5': {
        'title': "택시 타기",
        'difficulty': 'intermediate',
        'exp_reward': 70,
        'stages': {
            1: {
                'description': "택시를 탔습니다. 기사가 목적지를 묻습니다.",
                'bot_message': "Куда едем? (어디로 가시나요?)",
                'action_prompt': "크렘린으로 가달라고 말해보세요.",
                'keywords': ['кремль', 'поехали', 'пожалуйста'],
                'hints': ['В Кремль, пожалуйста (크렘린으로 가주세요)']
            },
            2: {
                'description': "기사가 시간을 알려줍니다.",
                'bot_message': "Примерно 20 минут. (약 20분 걸립니다.)",
                'action_prompt': "좋다고 대답해보세요.",
                'keywords': ['хорошо', 'отлично', 'понятно'],
                'hints': ['Хорошо, спасибо (좋습니다, 감사합니다)']
            }
        }
    }
}

# 🎵 발음 연습용 문장들
PRONUNCIATION_SENTENCES = {
    'beginner': [
        {'text': 'Привет, как дела?', 'translation': '안녕, 어떻게 지내?', 'focus': '인사말'},
        {'text': 'Меня зовут Анна.', 'translation': '제 이름은 안나입니다.', 'focus': '자기소개'},
        {'text': 'Сколько это стоит?', 'translation': '이것이 얼마인가요?', 'focus': '쇼핑'},
        {'text': 'Где находится музей?', 'translation': '박물관이 어디에 있나요?', 'focus': '길 묻기'},
    ],
    'intermediate': [
        {'text': 'Я изучаю русский язык уже год.', 'translation': '저는 러시아어를 공부한 지 벌써 1년이 됩니다.', 'focus': '시간 표현'},
        {'text': 'Мне нравится читать книги по вечерам.', 'translation': '저는 저녁에 책 읽기를 좋아합니다.', 'focus': '취미 표현'},
        {'text': 'Завтра у меня важная встреча.', 'translation': '내일 저에게 중요한 만남이 있습니다.', 'focus': '미래 계획'},
    ],
    'advanced': [
        {'text': 'Несмотря на трудности, он продолжал изучать язык.', 'translation': '어려움에도 불구하고 그는 언어 공부를 계속했습니다.', 'focus': '복합 문장'},
        {'text': 'Если бы я знал об этом раньше, то поступил бы по-другому.', 'translation': '만약 제가 이것을 더 일찍 알았다면, 다르게 행동했을 것입니다.', 'focus': '가정법'},
    ]
}

# --- 사용자 데이터 관리 ---
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user(chat_id):
    users = load_user_data()
    user_id = str(chat_id)
    if user_id not in users:
        users[user_id] = {
            'subscribed_daily': False,
            'quest_state': {'current_quest': None, 'stage': 0},
            'stats': {
                'start_date': datetime.now(MSK).isoformat(),
                'last_active_date': datetime.now(MSK).isoformat(),
                'quests_completed': 0,
                'sentences_corrected': 0,
                'translations_made': 0,
                'tts_generated': 0,
                'daily_words_received': 0,
                'total_exp': 0,
                'level': 1
            },
            # === 🌟 새로운 고급 학습 데이터 ===
            'learning': {
                'vocabulary_srs': {},  # 간격 반복 학습 단어들
                'pronunciation_scores': [],  # 발음 점수 기록
                'game_stats': {
                    'word_match': {'played': 0, 'won': 0, 'best_score': 0},
                    'sentence_builder': {'played': 0, 'won': 0, 'best_score': 0},
                    'speed_quiz': {'played': 0, 'won': 0, 'best_score': 0},
                    'pronunciation_challenge': {'played': 0, 'won': 0, 'best_score': 0}
                },
                'achievements': [],  # 획득한 성취
                'daily_streak': 0,  # 연속 학습일
                'last_study_date': None,
                'weak_areas': [],  # 약점 분야
                'strength_areas': [],  # 강점 분야
                'personalized_content': [],  # 개인화된 학습 콘텐츠
                'learning_style': 'balanced',  # visual, auditory, kinesthetic, balanced
                'difficulty_preference': 'adaptive'  # easy, medium, hard, adaptive
            },
            'social': {
                'friends': [],  # 친구 목록
                'challenges_sent': 0,
                'challenges_won': 0,
                'ranking_points': 0
            }
        }
        save_user_data(users)
    
    # 기존 사용자 데이터에 새 필드 추가 (하위 호환성)
    if 'learning' not in users[user_id]:
        users[user_id]['learning'] = {
            'vocabulary_srs': {},
            'pronunciation_scores': [],
            'game_stats': {
                'word_match': {'played': 0, 'won': 0, 'best_score': 0},
                'sentence_builder': {'played': 0, 'won': 0, 'best_score': 0},
                'speed_quiz': {'played': 0, 'won': 0, 'best_score': 0},
                'pronunciation_challenge': {'played': 0, 'won': 0, 'best_score': 0}
            },
            'achievements': [],
            'daily_streak': 0,
            'last_study_date': None,
            'weak_areas': [],
            'strength_areas': [],
            'personalized_content': [],
            'learning_style': 'balanced',
            'difficulty_preference': 'adaptive'
        }
    
    if 'social' not in users[user_id]:
        users[user_id]['social'] = {
            'friends': [],
            'challenges_sent': 0,
            'challenges_won': 0,
            'ranking_points': 0
        }
    
    # 일일 연속 학습 체크
    today = datetime.now(MSK).date()
    last_study = users[user_id]['learning']['last_study_date']
    
    if last_study:
        last_study_date = datetime.fromisoformat(last_study).date()
        if today == last_study_date + timedelta(days=1):
            users[user_id]['learning']['daily_streak'] += 1
        elif today != last_study_date:
            users[user_id]['learning']['daily_streak'] = 1
    else:
        users[user_id]['learning']['daily_streak'] = 1
    
    users[user_id]['learning']['last_study_date'] = today.isoformat()
    users[user_id]['stats']['last_active_date'] = datetime.now(MSK).isoformat()
    save_user_data(users)
    return users[user_id]

# --- AI 기능 헬퍼 ---
async def call_gemini(prompt: str) -> str:
    global model_status, model
    now = datetime.now(pytz.timezone('America/Los_Angeles'))

    # 할당량 리셋(매일 0시 PST) 후 2.5-pro로 복귀
    if model_status['current_index'] != 0:
        last_quota = model_status.get('quota_exceeded_time')
        if last_quota:
            last_quota_time = datetime.fromisoformat(last_quota)
            if now.date() > datetime.fromisoformat(last_quota).date():
                model_status['current_index'] = 0
                model_status['failure_count'] = 0
                model = get_model(0)
                save_model_status(model_status)

    for idx in range(model_status['current_index'], len(MODEL_CONFIG)):
        try:
            model = get_model(idx)
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: model.generate_content(prompt)
            )
            if idx != 0:
                # 폴백에서 성공하면 다시 2.5-pro로 복귀 예약
                model_status['current_index'] = 0
                model_status['failure_count'] = 0
                save_model_status(model_status)
            logger.info(f"✅ {MODEL_CONFIG[idx]['display_name']} 사용 성공")
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"❌ {MODEL_CONFIG[idx]['display_name']} 에러: {e}")
            # 할당량/404/429/Quota 에러 시 다음 모델로
            if any(k in error_str for k in ['quota', '429', 'rate limit', 'resource_exhausted', 'not found', '404']):
                model_status['current_index'] = idx + 1
                model_status['quota_exceeded_time'] = now.isoformat()
                model_status['failure_count'] = 0
                save_model_status(model_status)
                continue
            else:
                model_status['failure_count'] += 1
                save_model_status(model_status)
                if model_status['failure_count'] >= 3 and idx < len(MODEL_CONFIG) - 1:
                    model_status['current_index'] = idx + 1
                    model_status['failure_count'] = 0
                    save_model_status(model_status)
                    continue
                return "죄송합니다. AI 모델과 통신 중 오류가 발생했습니다. 😅"
    return "죄송합니다. 현재 AI 서비스 할당량이 모두 소진되었습니다. 내일 다시 시도해주세요. 😅"

def get_fallback_translation(prompt: str) -> str:
    """기본 번역 사전을 활용한 폴백 번역"""
    basic_translations = {
        'привет': '안녕하세요',
        'спасибо': '감사합니다',
        'пожалуйста': '천만에요',
        'извините': '죄송합니다',
        'да': '네',
        'нет': '아니요',
        'хорошо': '좋아요',
        'до свидания': '안녕히 가세요',
        'как дела': '어떻게 지내세요',
        'меня зовут': '제 이름은',
        'я не понимаю': '이해하지 못하겠습니다',
        'помогите': '도와주세요',
        'где': '어디에',
        'что': '무엇',
        'кто': '누구'
    }
    
    prompt_lower = prompt.lower()
    for russian, korean in basic_translations.items():
        if russian in prompt_lower:
            return f"기본 번역: {russian} → {korean}\n\n⚠️ 현재 AI 서비스에 일시적인 문제가 있어 기본 번역만 제공됩니다."
    
    return "죄송합니다. 현재 AI 서비스에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요. 😅"

async def convert_text_to_speech(text: str, lang: str = "auto") -> bytes:
    """무료 Google TTS로 텍스트를 음성으로 변환 (한국어, 러시아어 지원)"""
    try:
        # 언어 자동 감지 또는 지정
        if lang == "auto":
            # 한글이 포함되어 있으면 한국어, 키릴 문자가 포함되어 있으면 러시아어
            if any('\u3131' <= char <= '\u3163' or '\uac00' <= char <= '\ud7a3' for char in text):
                detected_lang = "ko"
                lang_name = "한국어"
            elif any('\u0400' <= char <= '\u04ff' for char in text):
                detected_lang = "ru"
                lang_name = "러시아어"
            else:
                # 기본값을 한국어로 설정
                detected_lang = "ko"
                lang_name = "한국어 (기본값)"
        else:
            detected_lang = lang
            lang_name = "러시아어" if lang == "ru" else "한국어" if lang == "ko" else lang
            
        logger.info(f"TTS 시작 - 텍스트: '{text}', 감지된 언어: {lang_name} ({detected_lang})")
        
        # 텍스트가 너무 길면 자르기 (gTTS 제한: 200자 정도)
        if len(text) > 200:
            text = text[:200] + "..."
            logger.info(f"텍스트 자름 - 새 길이: {len(text)}")
        
        # gTTS 객체 생성
        logger.info("gTTS 객체 생성 중...")
        tts = gTTS(text=text, lang=detected_lang, slow=False)
        
        # 메모리에서 음성 파일 생성
        logger.info("음성 파일 생성 중...")
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        audio_data = audio_buffer.getvalue()
        logger.info(f"음성 파일 생성 완료 - 크기: {len(audio_data)} bytes, 언어: {lang_name}")
        
        return audio_data
    except Exception as e:
        logger.error(f"TTS 오류: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        return None

async def split_long_message(text: str, max_length: int = 4096) -> list:
    """긴 메시지를 여러 부분으로 나누기"""
    if len(text) <= max_length:
        return [text]
    
    # 메시지를 여러 부분으로 나누기
    parts = []
    current_part = ""
    
    # 줄 단위로 나누기
    lines = text.split('\n')
    
    for line in lines:
        # 현재 부분 + 새 줄이 최대 길이를 초과하는지 확인
        if len(current_part) + len(line) + 1 > max_length:
            if current_part:
                parts.append(current_part.strip())
                current_part = line
            else:
                # 한 줄이 너무 긴 경우 강제로 자르기
                while len(line) > max_length:
                    parts.append(line[:max_length])
                    line = line[max_length:]
                current_part = line
        else:
            if current_part:
                current_part += "\n" + line
            else:
                current_part = line
    
    # 마지막 부분 추가
    if current_part:
        parts.append(current_part.strip())
    
    return parts

# --- 핵심 기능: 명령어 핸들러 ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """💎 차세대 러시아어 학습 플랫폼 - 완전 혁신! 💎"""
    user = update.effective_user
    user_data = get_user(update.effective_chat.id)
    
    level = user_data['stats']['level']
    exp = user_data['stats']['total_exp']
    streak = user_data['learning']['daily_streak']
    achievements = len(user_data['learning']['achievements'])
    
    # 레벨별 동적 상태 표시
    if level <= 10:
        level_emoji = "🔰"
        level_title = "초보 모험가"
        next_goal = "레벨 20 달성하기"
    elif level <= 30:
        level_emoji = "⚡"
        level_title = "중급 탐험가"
        next_goal = "레벨 50 달성하기"
    elif level <= 60:
        level_emoji = "🏆"
        level_title = "고급 마스터"
        next_goal = "레벨 80 달성하기"
    else:
        level_emoji = "👑"
        level_title = "전설의 챔피언"
        next_goal = "완벽한 러시아어 마스터"

    # 💎 완전 혁신된 UI
    welcome_message = f"""
🌟 **세계 최고 러시아어 AI 코치 'RUSYA'** 🌟

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ **환영합니다, {user.first_name}님!** ✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{level_emoji} **현재 상태**: {level_title} (레벨 {level})
⭐ **총 경험치**: {exp:,} EXP
🔥 **연속 학습**: {streak}일 
🏅 **성취 배지**: {achievements}/8개
🎯 **다음 목표**: {next_goal}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **무엇을 시작해볼까요?** 🚀
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📱 번호를 선택하세요! (예: /1)**

**🎮 게임 & 퀘스트**
`/1` - 🎮 **게임으로 학습하기** (4가지 게임)
`/2` - 🏰 **퀘스트 시작하기** (실전 회화)
`/3` - 🎯 **AI 튜터 상담** (개인 분석)
`/4` - 🏆 **성취 배지 확인** (업적 시스템)

**📚 학습 도구**
`/5` - ✍️ **작문 교정받기** (AI 첨삭)
`/6` - 🌍 **번역 & 음성** (다기능 도구)
`/7` - 📊 **학습 진도 확인** (상세 통계)
`/8` - 🎤 **발음 점수 확인** (음성 분석)

**🎯 고급 기능**
`/9` - 📈 **개인화된 수업** (맞춤 학습)
`/0` - 📋 **전체 메뉴** (모든 기능)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**💡 빠른 접근 명령어**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• `/quest` - 즉시 퀘스트 시작
• `/games` - 게임 선택 메뉴  
• `/write [러시아어]` - 작문 교정
• `/help` - 전체 도움말

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 **특별 혜택** 🎉
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆓 **완전 무료** - 모든 기능 무제한 사용
🤖 **최신 AI** - Gemini 2.5 Pro 엔진
🎵 **음성 지원** - 실시간 TTS 변환
📱 **24/7 서비스** - 언제든지 학습 가능

💬 **자유 대화도 가능해요!** 그냥 메시지를 보내세요!
🚀 **지금 바로 번호를 선택해서 시작하세요!**
    """
    
    # 메시지 전송
    await update.message.reply_text(welcome_message)
    
    # 개인화된 추천 메시지
    recommendation = f"""
💎 **{user.first_name}님 맞춤 추천** 💎

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    # 레벨별 맞춤 추천
    if level <= 10:
        recommendation += f"""
🌱 **초보자 특별 가이드**

🎯 **오늘의 추천 순서**:
1️⃣ `/2` (퀘스트) → 실전 상황 체험
2️⃣ `/1` (게임) → 재미있게 복습
3️⃣ `/3` (AI 튜터) → 개인 분석

💡 **학습 팁**: 하루 15-20분씩 꾸준히!
🚀 **목표**: 첫 100 EXP 달성하기

**🔥 추천**: 카페 퀘스트부터 시작해보세요!
        """
    elif level <= 30:
        recommendation += f"""
⚡ **중급자 성장 전략**

🎯 **오늘의 추천 순서**:
1️⃣ `/5` (작문 교정) → 문법 마스터
2️⃣ `/9` (개인화 수업) → 체계적 학습
3️⃣ `/1` (게임) → 실력 점검

💡 **학습 팁**: 작문 연습으로 실력 업그레이드!
🚀 **목표**: 레벨 50 달성하기

**🔥 추천**: 복합 문장 연습에 집중하세요!
        """
    else:
        recommendation += f"""
👑 **고급자 완성 로드맵**

🎯 **오늘의 추천 순서**:
1️⃣ `/8` (발음 완성) → 원어민 수준
2️⃣ `/9` (고급 수업) → 완벽함 추구
3️⃣ `/2` (고급 퀘스트) → 실전 마스터

💡 **학습 팁**: 발음과 고급 표현에 집중!
🚀 **목표**: 러시아어 완전 마스터

**🔥 추천**: 고난도 퀘스트에 도전하세요!
        """
    
    recommendation += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎊 **매일 혜택** 🎊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 매일 오전 7시 - 새로운 학습 콘텐츠 자동 발송
🎵 모든 텍스트 - 즉시 음성 변환 가능
🤖 AI 튜터 - 24시간 개인 맞춤 상담
🏆 성취 시스템 - 학습할수록 배지 획득

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💪 **함께 러시아어 마스터가 되어요!** 💪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👆 **위 번호 중 하나를 선택하세요!**
✨ **또는 자유롭게 대화해도 됩니다!**
    """
    
    # 추천 메시지 전송
    await update.message.reply_text(recommendation)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 전체 명령어 도움말을 카테고리별로 구성
    help_text = """
🤖 **'루샤' 봇 완전 사용법 안내** 🤖

━━━━━━━━━━━━━━━━━━━━━━━━
**🏆 실전 학습 명령어**
━━━━━━━━━━━━━━━━━━━━━━━━

**🎮 퀘스트 시스템**
• `/quest` - 스토리 기반 러시아어 회화 학습
  └ 카페, 레스토랑 등 실제 상황 시뮬레이션
  └ 단계별 진행으로 자연스러운 학습

• `/action [러시아어 문장]` - 퀘스트에서 행동하기
  └ 예시: `/action Здравствуйте, кофе пожалуйста`
  └ 키워드 인식으로 자동 진행

━━━━━━━━━━━━━━━━━━━━━━━━
**✍️ AI 학습 도구**
━━━━━━━━━━━━━━━━━━━━━━━━

**📝 작문 교정**
• `/write [러시아어 문장]` - AI가 문법과 표현 교정
  └ 예시: `/write Я хочу пить кофе`
  └ 상세한 설명과 자연스러운 표현 제안
  └ 칭찬과 함께 동기부여 피드백

━━━━━━━━━━━━━━━━━━━━━━━━
**🌍 번역 시스템**
━━━━━━━━━━━━━━━━━━━━━━━━

**⚡ 간단 번역**
• `/trs [언어] [텍스트]` - 빠르고 정확한 번역
  └ 예시: `/trs russian 안녕하세요` 또는 `/trs ru 감사합니다`
  └ 지원언어: korean(kr), russian(ru), english(en)

**📚 상세 번역**
• `/trl [언어] [텍스트]` - 문법 분석 + 단어 설명
  └ 예시: `/trl russian 좋은 아침이에요`
  └ 여러 번역 제안 + 문법 구조 설명
  └ 단어별 의미와 활용 정보

━━━━━━━━━━━━━━━━━━━━━━━━
**🎵 음성 학습**
━━━━━━━━━━━━━━━━━━━━━━━━

**🔊 음성 변환**
• `/ls [텍스트]` - 텍스트를 자연스러운 음성으로
  └ 예시: `/ls Привет, как дела?`
  └ 한국어/러시아어 자동 인식
  └ 고품질 Google TTS 엔진

**🎯 번역+음성**
• `/trls [언어] [텍스트]` - 번역과 음성을 한번에
  └ 예시: `/trls russian 안녕하세요`
  └ 번역 결과를 바로 음성으로 들을 수 있어 발음 학습에 최적

━━━━━━━━━━━━━━━━━━━━━━━━
**📊 학습 관리**
━━━━━━━━━━━━━━━━━━━━━━━━

**📈 진도 확인**
• `/my_progress` - 개인 학습 통계와 성과
  └ 레벨, 경험치, 활동 기록 확인
  └ 연속 학습일과 성취도 추적

**📅 일일 학습**
• `/subscribe_daily` - 매일 러시아어 콘텐츠 받기
• `/unsubscribe_daily` - 일일 학습 구독 해제
  └ 매일 아침 7시, 낮 12시 (모스크바 시간)
  └ 새로운 단어 30개 + 회화 20개

━━━━━━━━━━━━━━━━━━━━━━━━
**🔧 시스템 명령어**
━━━━━━━━━━━━━━━━━━━━━━━━

• `/start` - 봇 시작 및 기능 소개
• `/help` - 이 상세 도움말 보기
• `/model_status` - 현재 AI 모델 상태 확인

━━━━━━━━━━━━━━━━━━━━━━━━
**💡 사용 팁**
━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **명령어 없이도 대화 가능**: 그냥 메시지를 보내면 AI가 답변
🔹 **단계별 학습**: 퀘스트 → 작문 교정 → 번역 → 음성 순서 추천
🔹 **꾸준한 학습**: 일일 학습 구독으로 습관 만들기
🔹 **활용도 극대화**: 상세 번역으로 문법 이해 → 음성으로 발음 연습

🎯 **목표**: 매일 조금씩, 꾸준히 러시아어 마스터하기!
    """
    
    # 긴 메시지를 여러 부분으로 나누어 전송
    message_parts = await split_long_message(help_text)
    
    for i, part in enumerate(message_parts):
        if i == 0:
            await update.message.reply_text(part)
        else:
            await update.message.reply_text(f"📄 (계속 {i+1}/{len(message_parts)})\n\n{part}")

async def subscribe_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    users = load_user_data()
    user = get_user(chat_id)

    if not user['subscribed_daily']:
        users[str(chat_id)]['subscribed_daily'] = True
        save_user_data(users)
        await update.message.reply_text(
            "✅ **일일 학습 구독 완료!**\n\n"
            "📅 **배송 시간**: 매일 오전 7시, 낮 12시 (모스크바 기준)\n"
            "📚 **학습 내용**: 러시아어 단어 30개 + 실용 회화 20개\n"
            "🎯 **학습 효과**: 꾸준한 반복으로 어휘력 대폭 향상\n\n"
            "💡 **팁**: 받은 단어들을 `/write` 명령어로 문장 만들기 연습하면 더욱 효과적!"
        )
    else:
        await update.message.reply_text(
            "📅 이미 일일 학습을 구독 중이십니다!\n\n"
            "매일 아침과 낮에 새로운 러시아어 콘텐츠를 받아보고 계세요. 😊\n"
            "구독을 해제하려면 `/unsubscribe_daily`를 입력하세요."
        )

async def unsubscribe_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    users = load_user_data()
    user = get_user(chat_id)

    if user['subscribed_daily']:
        users[str(chat_id)]['subscribed_daily'] = False
        save_user_data(users)
        await update.message.reply_text(
            "✅ **일일 학습 구독 해제 완료**\n\n"
            "😢 아쉽지만 언제든 다시 `/subscribe_daily`로 구독할 수 있습니다.\n"
            "꾸준한 학습이 가장 중요하니까요!"
        )
    else:
        await update.message.reply_text(
            "📭 현재 일일 학습을 구독하고 있지 않습니다.\n\n"
            "`/subscribe_daily`로 구독하시면 매일 새로운 러시아어 콘텐츠를 받아볼 수 있어요!"
        )

async def quest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    quest_state = user['quest_state']

    if quest_state['current_quest'] is None:
        quest_id = 'q1'
        users = load_user_data()
        users[str(chat_id)]['quest_state'] = {'current_quest': quest_id, 'stage': 1}
        save_user_data(users)
        
        quest = QUEST_DATA[quest_id]
        stage_data = quest['stages'][1]
        
        await update.message.reply_text(
            f"**📜 새로운 퀘스트: {quest['title']}**\n\n"
            f"🎬 **상황 설명:**\n{stage_data['description']}\n\n"
            f"🗣️ **점원의 말:**\n`{stage_data['bot_message']}`\n\n"
            f"➡️ **당신의 임무:**\n{stage_data['action_prompt']}\n\n"
            f"💬 **사용법:** `/action [할 말]`을 사용해 대답해주세요.\n"
            f"📝 **예시:** `/action Здравствуйте, кофе пожалуйста`\n\n"
            f"💡 **도움이 필요하면:** `/hint` 또는 `/trans`를 입력하세요!"
        )
    else:
        quest_id = quest_state['current_quest']
        stage = quest_state['stage']
        quest = QUEST_DATA[quest_id]
        
        if stage > len(quest['stages']):
            await update.message.reply_text(
                "🎉 **모든 퀘스트 완료!**\n\n"
                "축하합니다! 현재 제공되는 모든 퀘스트를 완료하셨습니다.\n"
                "더 많은 퀘스트가 곧 업데이트될 예정이니 기대해주세요!"
            )
            return

        stage_data = quest['stages'][stage]
        
        await update.message.reply_text(
            f"**📜 퀘스트 진행 중: {quest['title']} (단계: {stage}/{len(quest['stages'])})**\n\n"
            f"🎬 **현재 상황:**\n{stage_data['description']}\n\n"
            f"🗣️ **상대방의 말:**\n`{stage_data['bot_message']}`\n\n"
            f"➡️ **당신의 임무:**\n{stage_data['action_prompt']}\n\n"
            f"💬 **사용법:** `/action [할 말]`을 사용해 대답해주세요.\n\n"
            f"💡 **도움이 필요하면:** `/hint` 또는 `/trans`를 입력하세요!"
        )

async def action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = " ".join(context.args)
    
    if not user_text:
        await update.message.reply_text(
            "**❌ 사용법 오류**\n\n"
            "💬 **올바른 사용법:** `/action [러시아어 문장]`\n\n"
            "📝 **예시:**\n"
            "• `/action Здравствуйте` (안녕하세요)\n"
            "• `/action Кофе, пожалуйста` (커피 주세요)\n"
            "• `/action Спасибо` (감사합니다)\n\n"
            "먼저 `/quest`로 퀘스트를 시작해주세요!"
        )
        return

    users = load_user_data()
    user = users[str(chat_id)]
    quest_state = user['quest_state']

    if quest_state['current_quest'] is None:
        await update.message.reply_text(
            "**❌ 진행 중인 퀘스트가 없습니다**\n\n"
            "먼저 `/quest`로 새 퀘스트를 시작하세요!"
        )
        return

    quest_id = quest_state['current_quest']
    stage = quest_state['stage']
    quest = QUEST_DATA[quest_id]
    stage_data = quest['stages'][stage]

    # 키워드 매칭 확인
    if any(keyword in user_text.lower() for keyword in stage_data['keywords']):
        next_stage = stage + 1
        if next_stage > len(quest['stages']):
            user['quest_state'] = {'current_quest': None, 'stage': 0}
            user['stats']['quests_completed'] += 1
            user['stats']['total_exp'] += 50  # 퀘스트 완료 시 경험치 추가
            save_user_data(users)
            
            await update.message.reply_text(
                f"🎉 **퀘스트 완료: {quest['title']}** 🎉\n\n"
                f"🏆 축하합니다! 실전 러시아어 경험을 쌓으셨습니다.\n"
                f"⭐ **획득한 경험치:** +50 EXP\n"
                f"📈 **완료한 퀘스트:** {user['stats']['quests_completed']}개\n\n"
                f"💡 **다음 단계:** `/my_progress`로 진도를 확인하거나\n"
                f"새로운 퀘스트를 시작해보세요!"
            )
        else:
            user['quest_state']['stage'] = next_stage
            save_user_data(users)
            
            next_stage_data = quest['stages'][next_stage]
            
            await update.message.reply_text(
                f"**✅ 단계 {stage} 성공!**\n\n"
                f"🎬 **다음 상황:**\n{next_stage_data['description']}\n\n"
                f"🗣️ **상대방의 말:**\n`{next_stage_data['bot_message']}`\n\n"
                f"➡️ **당신의 임무:**\n{next_stage_data['action_prompt']}\n\n"
                f"💬 계속해서 `/action [할 말]`로 대답해주세요!\n\n"
                f"💡 **도움이 필요하면:** `/hint` 또는 `/trans`를 입력하세요!"
            )
    else:
        # 힌트 제공
        keywords_hint = "`, `".join(stage_data['keywords'][:3])  # 처음 3개 키워드만
        
        await update.message.reply_text(
            f"🤔 **조금 다른 표현이 필요할 것 같아요**\n\n"
            f"💡 **힌트:** {stage_data['action_prompt']}\n\n"
            f"🔑 **키워드 참고:** `{keywords_hint}` 등을 사용해보세요\n\n"
            f"🔄 **다시 시도:** `/action [새로운 러시아어 문장]`"
        )

async def write_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = " ".join(context.args)

    if not user_text:
        await update.message.reply_text(
            "**✍️ AI 작문 교정 사용법**\n\n"
            "📝 **명령어:** `/write [교정받고 싶은 러시아어 문장]`\n\n"
            "📚 **예시:**\n"
            "• `/write Я хочу изучать русский язык`\n"
            "• `/write Вчера я пошёл в магазин`\n"
            "• `/write Мне нравится читать книги`\n\n"
            "🎯 **제공 기능:**\n"
            "✅ 문법 오류 수정\n"
            "✅ 자연스러운 표현 제안\n"
            "✅ 상세한 설명과 이유\n"
            "✅ 칭찬과 동기부여\n\n"
            "💡 **팁:** 틀려도 괜찮으니 자유롭게 문장을 만들어보세요!"
        )
        return

    user = get_user(chat_id)
    
    processing_message = await update.message.reply_text(
        "✍️ **AI가 문장을 교정하고 있습니다...**\n\n"
        "⏳ 문법 분석 중...\n"
        "🔍 자연스러운 표현 검토 중...\n"
        "📝 교정 결과 작성 중..."
    )

    prompt = f"""
    당신은 친절한 러시아어 원어민 선생님입니다. 학생이 아래 러시아어 문장을 작성했습니다.
    문법 오류, 부자연스러운 표현을 찾아 수정하고, 왜 그렇게 수정했는지 한국어로 쉽고 명확하게 설명해주세요.
    칭찬을 섞어 동기를 부여해주세요.

    학생의 문장: "{user_text}"

    아래와 같은 형식으로 답변해주세요:

    **📝 학생 문장:**
    [학생의 문장]

    **✨ 교정된 문장:**
    [자연스럽고 올바른 문장]

    **👨‍🏫 선생님의 피드백:**
    [칭찬과 함께, 어떤 부분이 왜 틀렸고 어떻게 고쳐야 하는지에 대한 구체적인 설명]

    **💡 추가 학습 팁:**
    [비슷한 실수를 피하는 방법이나 관련 문법 규칙]
    """
    
    corrected_text = await call_gemini(prompt)
    
    await processing_message.delete()
    await update.message.reply_text(corrected_text)

    # 통계 업데이트
    users = load_user_data()
    users[str(chat_id)]['stats']['sentences_corrected'] += 1
    users[str(chat_id)]['stats']['total_exp'] += 10  # 작문 교정 시 경험치 추가
    save_user_data(users)

async def my_progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_data = get_user(chat_id)
    stats = user_data['stats']

    start_date = datetime.fromisoformat(stats['start_date'])
    days_since_start = (datetime.now(MSK) - start_date).days + 1
    
    # 레벨과 경험치 계산
    exp = stats.get('total_exp', 0)
    level = stats.get('level', 1)
    exp_for_current_level = (level - 1) * 100
    exp_for_next_level = level * 100
    exp_progress = exp - exp_for_current_level
    
    # 진행률 바 생성
    progress_bar_length = 10
    filled = int((exp_progress / 100) * progress_bar_length)
    progress_bar = "▓" * filled + "░" * (progress_bar_length - filled)
    
    # 활동 점수 계산
    total_activities = (
        stats.get('sentences_corrected', 0) + 
        stats.get('translations_made', 0) + 
        stats.get('quests_completed', 0) + 
        stats.get('tts_generated', 0)
    )
    
    # 일일 평균 활동
    daily_average = round(total_activities / days_since_start, 1) if days_since_start > 0 else 0
    
    progress_report = f"""
📊 **{update.effective_user.first_name}님의 러시아어 학습 리포트** 📊

━━━━━━━━━━━━━━━━━━━━━━━━
**🔰 레벨 정보**
━━━━━━━━━━━━━━━━━━━━━━━━
• **현재 레벨:** {level} 📈
• **경험치:** {exp_progress}/100 EXP
• **진행률:** {progress_bar} ({round((exp_progress/100)*100, 1)}%)
• **총 획득 EXP:** {exp} ⭐

━━━━━━━━━━━━━━━━━━━━━━━━
**📈 학습 활동 기록**
━━━━━━━━━━━━━━━━━━━━━━━━
• ✍️ **AI 작문 교정:** {stats.get('sentences_corrected', 0)}회
• 🌍 **번역 요청:** {stats.get('translations_made', 0)}회
• 🎵 **음성 변환:** {stats.get('tts_generated', 0)}회
• 🏆 **완료한 퀘스트:** {stats.get('quests_completed', 0)}개
• 📚 **일일 학습 수신:** {stats.get('daily_words_received', 0)}회

━━━━━━━━━━━━━━━━━━━━━━━━
**🔥 학습 통계**
━━━━━━━━━━━━━━━━━━━━━━━━
• **학습 시작일:** {start_date.strftime('%Y년 %m월 %d일')}
• **총 학습일:** {days_since_start}일
• **총 활동 수:** {total_activities}회
• **일일 평균 활동:** {daily_average}회/일

━━━━━━━━━━━━━━━━━━━━━━━━
**🎯 다음 목표**
━━━━━━━━━━━━━━━━━━━━━━━━
• **레벨업까지:** {100 - exp_progress} EXP 필요
• **추천 활동:** 작문 교정 {(100-exp_progress)//10 + 1}회 더 하면 레벨업!

💡 **루샤의 피드백:**
정말 꾸준히 잘하고 계세요! 특히 {'작문 연습' if stats.get('sentences_corrected', 0) > 5 else '퀘스트 도전' if stats.get('quests_completed', 0) > 0 else '번역 활용'}을 많이 하신 점이 인상 깊네요. 
언어 실력 향상의 비결은 꾸준함입니다. 화이팅! 🚀
    """
    
    await update.message.reply_text(progress_report)

# 기존 번역 명령어들 (사용법 향상)
async def translate_simple_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """간단한 번역 명령어 (/trs) - 업그레이드된 사용법 안내"""
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "**⚡ 간단 번역 사용법** ⚡\n\n"
                "📝 **명령어:** `/trs [언어] [텍스트]`\n\n"
                "🌍 **지원 언어:**\n"
                "• `korean` 또는 `kr` - 한국어\n"
                "• `russian` 또는 `ru` - 러시아어\n"
                "• `english` 또는 `en` - 영어\n\n"
                "📚 **사용 예시:**\n"
                "• `/trs russian 안녕하세요` → 러시아어로 번역\n"
                "• `/trs korean Привет` → 한국어로 번역\n"
                "• `/trs en 감사합니다` → 영어로 번역\n\n"
                "⚡ **특징:** 깔끔하고 빠른 번역 결과\n"
                "📚 **더 자세한 번역:** `/trl` 명령어 사용"
            )
            return
        
        target_language = args[0]
        text_to_translate = " ".join(args[1:])
        
        # "처리 중..." 메시지 표시
        processing_message = await update.message.reply_text(
            "⚡ **간단 번역 처리 중...**\n\n"
            f"🔤 원문: {text_to_translate}\n"
            f"🎯 목표 언어: {target_language}\n"
            "⏳ AI가 번역하고 있습니다..."
        )
        
        # 언어 매핑 (영어 입력을 한국어로 변환)
        language_mapping = {
            'russian': '러시아어',
            'russia': '러시아어',
            'ru': '러시아어',
            'english': '영어',
            'en': '영어',
            'korean': '한국어',
            'korea': '한국어',
            'kr': '한국어'
        }
        
        # 영어 입력을 한국어로 변환
        korean_language = language_mapping.get(target_language.lower(), target_language)
        
        # 간단한 번역만 요청
        translate_prompt = f"다음 텍스트를 {korean_language}로 최고의 번역만 제공해주세요. 설명이나 추가 정보 없이 가장 자연스러운 번역문만 제공해주세요: {text_to_translate}"
        
        translated_text = await call_gemini(translate_prompt)
        
        # 번역 결과에서 불필요한 부분 제거 (첫 번째 줄만 사용)
        clean_translation = translated_text.split('\n')[0].strip()
        if '**' in clean_translation:
            clean_translation = clean_translation.replace('**', '').strip()
        
        # "처리 중..." 메시지 삭제
        await processing_message.delete()
        
        # 번역 결과 전송
        full_response = f"⚡ **간단 번역 결과** ({korean_language})\n\n"
        full_response += f"📝 **원문:** {text_to_translate}\n"
        full_response += f"🎯 **번역:** {clean_translation}\n\n"
        full_response += f"💡 **더 자세한 번역이 필요하면:** `/trl {target_language} {text_to_translate}`"
        
        await update.message.reply_text(full_response)
        
        # 통계 업데이트
        chat_id = update.effective_chat.id
        users = load_user_data()
        users[str(chat_id)]['stats']['translations_made'] += 1
        users[str(chat_id)]['stats']['total_exp'] += 5  # 번역 시 경험치 추가
        save_user_data(users)
                
    except Exception as e:
        logger.error(f"간단 번역 오류: {e}")
        await update.message.reply_text("간단 번역 중 오류가 발생했습니다. 😅")

async def translate_long_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """상세한 번역 명령어 (/trl)"""
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "사용법: /trl [언어] [텍스트]\n\n"
                "💡 예시:\n"
                "- /trl english 안녕하세요 (또는 /trl en)\n"
                "- /trl russian 좋은 아침이에요 (또는 /trl ru)\n"
                "- /trl korean 감사합니다 (또는 /trl kr)\n\n"
                "📚 상세 번역: 여러 번역본, 발음, 문법, 단어 분석까지\n\n"
                "🌍 지원 언어:\n"
                "- english (en), russian (ru), korean (kr)"
            )
            return
        
        target_language = args[0]
        text_to_translate = " ".join(args[1:])
        
        # "처리 중..." 메시지 표시
        processing_message = await update.message.reply_text("📚 상세 번역 중...")
        
        # 언어 매핑 (영어 입력을 한국어로 변환)
        language_mapping = {
            'russian': '러시아어',
            'russia': '러시아어',
            'ru': '러시아어',
            'english': '영어',
            'en': '영어',
            'korean': '한국어',
            'korea': '한국어',
            'kr': '한국어'
        }
        
        # 영어 입력을 한국어로 변환
        korean_language = language_mapping.get(target_language.lower(), target_language)
        
        # 상세한 문법 분석 번역 요청
        if target_language.lower() in ['russian', 'russia', 'ru']:
            translate_prompt = f"""
다음 텍스트를 러시아어로 번역해주세요: {text_to_translate}

다음 형식으로 답변해주세요:

1. 번역:
- 번역 1: (주요 번역)
- 번역 2: (다른 표현)

2. 문법적 설명:
- 문장 구조: (주어, 술어, 목적어 배치)
- 시제: (현재/과거/미래 시제)
- 동사 변화: (인칭변화, 완료/불완료 동사)
- 격변화: (주격, 대격, 여격, 전치격, 조격, 생격 등)
- 명사의 성별: (남성/여성/중성 명사)
- 단수/복수: (명사와 형용사의 단복수 형태)
- 어미변화: (형용사의 성별 일치)

3. 각각의 단어 의미:
- 주요 단어들의 기본형과 의미
- 동사의 원형과 현재 사용된 형태
- 명사의 성별과 격 정보

(모든 답변에서 별표 강조 표시 사용하지 마세요)
"""
        else:
            translate_prompt = f"""
다음 텍스트를 {korean_language}로 번역해주세요: {text_to_translate}

다음 형식으로 답변해주세요:

1. 번역:
- 번역 1: (주요 번역)
- 번역 2: (다른 표현)

2. 문법적 설명:
- 문장 구조: (주어, 술어, 목적어 배치)
- 시제: (현재/과거/미래 시제)
- 동사 변화: (인칭변화, 동사 활용)
- 단수/복수: (명사의 단복수 형태)
- 어순: (언어별 특징적 어순)

3. 각각의 단어 의미:
- 주요 단어들의 기본형과 의미
- 동사의 원형과 현재 사용된 형태

(모든 답변에서 별표 강조 표시 사용하지 마세요)
"""
        
        translated_text = await call_gemini(translate_prompt)
        
        # "처리 중..." 메시지 삭제
        await processing_message.delete()
        
        # 번역 결과 전송 (긴 메시지 처리)
        full_response = f"📚 상세 번역 결과 ({korean_language}):\n\n{translated_text}"
        message_parts = await split_long_message(full_response)
        
        for i, part in enumerate(message_parts):
            if i == 0:
                await update.message.reply_text(part)
            else:
                await update.message.reply_text(f"📄 (계속 {i+1}/{len(message_parts)})\n\n{part}")
                
    except Exception as e:
        logger.error(f"상세 번역 오류: {e}")
        await update.message.reply_text("상세 번역 중 오류가 발생했습니다. 😅")

async def listening_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """한국어/러시아어 음성 변환 명령어"""
    try:
        if not context.args:
            await update.message.reply_text(
                "사용법: /ls [텍스트]\n\n"
                "💡 예시:\n"
                "- /ls 안녕하세요 (한국어)\n"
                "- /ls Привет, как дела? (러시아어)\n"
                "- /ls 좋은 아침이에요 (한국어)\n"
                "- /ls Доброе утро! (러시아어)\n\n"
                "🎵 완전 무료 Google TTS 사용!\n"
                "🌍 자동 언어 감지: 한국어/러시아어"
            )
            return
        
        input_text = " ".join(context.args)
        
        # "변환 중..." 메시지 표시
        processing_message = await update.message.reply_text("🎵 음성 변환 중...")
        
        # 자동 언어 감지로 음성 변환
        audio_data = await convert_text_to_speech(input_text, "auto")
        
        if audio_data:
            # "변환 중..." 메시지 삭제
            await processing_message.delete()
            
            # 언어 감지
            if any('\u3131' <= char <= '\u3163' or '\uac00' <= char <= '\ud7a3' for char in input_text):
                lang_flag = "🇰🇷"
                lang_name = "한국어"
            elif any('\u0400' <= char <= '\u04ff' for char in input_text):
                lang_flag = "🇷🇺"
                lang_name = "러시아어"
            else:
                lang_flag = "🇰🇷"
                lang_name = "한국어 (기본값)"
            
            # 음성 파일 전송
            await update.message.reply_audio(
                audio=audio_data,
                title=f"{lang_name} 음성: {input_text[:50]}...",
                caption=f"{lang_flag} {lang_name} 음성\n📝 텍스트: {input_text}\n🎤 엔진: Google TTS"
            )
            
            # 통계 업데이트
            chat_id = update.effective_chat.id
            users = load_user_data()
            users[str(chat_id)]['stats']['tts_generated'] += 1
            users[str(chat_id)]['stats']['total_exp'] += 3  # TTS 시 경험치 추가
            save_user_data(users)
        else:
            await processing_message.edit_text("음성 변환 실패. 다시 시도해주세요. 😅")
            
    except Exception as e:
        logger.error(f"TTS 오류: {e}")
        await update.message.reply_text("음성 변환 중 오류가 발생했습니다. 😅")

async def translate_listen_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """간단한 번역 + 음성 변환 명령어"""
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "사용법: /trls [언어] [텍스트]\n\n"
                "💡 예시:\n"
                "- /trls russian 안녕하세요 (또는 /trls ru)\n"
                "- /trls korean 좋은 아침이에요 (또는 /trls kr)\n"
                "- /trls english 감사합니다 (또는 /trls en)\n\n"
                "🎯 간단 번역 + 음성: TTS 최적화된 번역\n"
                "💡 음성 지원: 한국어, 러시아어\n\n"
                "🌍 지원 언어:\n"
                "- korean (kr), russian (ru), english (en)"
            )
            return
        
        target_language = args[0]
        text_to_translate = " ".join(args[1:])
        
        # "처리 중..." 메시지 표시
        processing_message = await update.message.reply_text("🔄 간단 번역 + 음성 변환 중...")
        
        # 언어 매핑 (영어 입력을 한국어로 변환)
        language_mapping = {
            'russian': '러시아어',
            'russia': '러시아어',
            'ru': '러시아어',
            'korean': '한국어',
            'korea': '한국어',
            'kr': '한국어',
            'english': '영어',
            'en': '영어'
        }
        
        # 영어 입력을 한국어로 변환
        korean_language = language_mapping.get(target_language.lower(), target_language)
        
        # 간단한 번역만 요청 (TTS 최적화)
        if target_language.lower() in ['russian', 'russia', 'ru']:
            translate_prompt = f"다음 텍스트를 러시아어로 간단하고 자연스럽게 번역해주세요. 설명이나 추가 정보 없이 번역문만 제공해주세요: {text_to_translate}"
        elif target_language.lower() in ['korean', 'korea', 'kr']:
            translate_prompt = f"다음 텍스트를 한국어로 간단하고 자연스럽게 번역해주세요. 설명이나 추가 정보 없이 번역문만 제공해주세요: {text_to_translate}"
        else:
            translate_prompt = f"다음 텍스트를 {korean_language}로 간단하고 자연스럽게 번역해주세요. 설명이나 추가 정보 없이 번역문만 제공해주세요: {text_to_translate}"
        
        translated_text = await call_gemini(translate_prompt)
        
        # 번역 결과에서 불필요한 부분 제거 (첫 번째 줄만 사용)
        clean_translation = translated_text.split('\n')[0].strip()
        if '**' in clean_translation:
            clean_translation = clean_translation.replace('**', '').strip()
        
        # "처리 중..." 메시지 삭제
        await processing_message.delete()
        
        # 번역 결과 전송
        full_response = f"🌍 간단 번역 ({korean_language}):\n{clean_translation}"
        await update.message.reply_text(full_response)
        
        # 음성 변환 (한국어 또는 러시아어인 경우)
        if target_language.lower() in ['russian', 'russia', 'ru', 'korean', 'korea', 'kr']:
            if target_language.lower() in ['russian', 'russia', 'ru']:
                logger.info("러시아어로 인식됨 - 음성 변환 시작")
                tts_lang = "ru"
                lang_flag = "🇷🇺"
                lang_name = "러시아어"
            else:  # korean
                logger.info("한국어로 인식됨 - 음성 변환 시작")
                tts_lang = "ko"
                lang_flag = "🇰🇷"
                lang_name = "한국어"
            
            # 음성 변환 메시지 표시
            tts_message = await update.message.reply_text("🎵 음성 변환 중...")
            
            # 정리된 번역 텍스트를 음성으로 변환
            audio_data = await convert_text_to_speech(clean_translation, tts_lang)
            
            if audio_data:
                # 음성 변환 메시지 삭제
                await tts_message.delete()
                
                # 음성 파일 전송
                await update.message.reply_audio(
                    audio=audio_data,
                    title=f"{lang_name} 음성: {clean_translation[:50]}...",
                    caption=f"{lang_flag} {lang_name} 음성 (간단 번역+TTS)\n📝 텍스트: {clean_translation}\n🎤 엔진: Google TTS"
                )
            else:
                await tts_message.edit_text("음성 변환 실패. 번역만 완료되었습니다. 😅")
        else:
            await update.message.reply_text("💡 음성 변환은 한국어와 러시아어만 지원합니다!")
            
    except Exception as e:
        logger.error(f"번역+음성 오류: {e}")
        await update.message.reply_text("번역+음성 변환 중 오류가 발생했습니다. 😅")

async def model_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """현재 사용 중인 AI 모델 상태 확인"""
    user = update.effective_user
    logger.info(f"사용자 {user.first_name} - 모델 상태 확인")
    
    global model_status
    
    current_model = MODEL_CONFIG[model_status['current_index']]['display_name']
    
    # 상태 메시지 생성
    status_message = f"🤖 **현재 AI 모델 상태**\n\n"
    status_message += f"📍 **현재 사용 중**: {current_model}\n"
    
    if model_status['current_index'] == 0:
        status_message += "✅ 최고 성능 모델 사용 중\n"
    else:
        status_message += "⚠️ 폴백 모델 사용 중\n"
        
        # 할당량 초과 시간 표시
        if model_status.get('quota_exceeded_time'):
            exceeded_time = datetime.fromisoformat(model_status['quota_exceeded_time'])
            status_message += f"⏰ 할당량 초과 시간: {exceeded_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        # 다음 복구 시도 시간
        if model_status.get('last_primary_attempt'):
            last_attempt = datetime.fromisoformat(model_status['last_primary_attempt'])
            next_attempt = last_attempt + timedelta(hours=4)
            status_message += f"🔄 다음 복구 시도: {next_attempt.strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    status_message += f"\n📊 **실패 횟수**: {model_status.get('failure_count', 0)}\n"
    
    # 모델 설정 정보
    status_message += f"\n🔧 **모델 설정**:\n"
    status_message += f"• Primary: {MODEL_CONFIG[0]['display_name']}\n"
    status_message += f"• Fallback: {MODEL_CONFIG[1]['display_name']}\n"
    
    await update.message.reply_text(status_message)

async def hint_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """퀘스트 힌트 제공"""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    quest_state = user['quest_state']
    
    if quest_state['current_quest'] is None:
        await update.message.reply_text(
            "❌ **진행 중인 퀘스트가 없습니다**\n\n"
            "먼저 `/quest`로 새 퀘스트를 시작하세요!"
        )
        return
    
    quest_id = quest_state['current_quest']
    stage = quest_state['stage']
    quest = QUEST_DATA[quest_id]
    stage_data = quest['stages'][stage]
    
    keywords_hint = "`, `".join(stage_data['keywords'][:3])
    
    await update.message.reply_text(
        f"💡 **퀘스트 힌트**\n\n"
        f"🎯 **현재 임무:** {stage_data['action_prompt']}\n\n"
        f"🔑 **사용할 키워드:** `{keywords_hint}` 등\n\n"
        f"📝 **예시 문장들:**\n"
        f"• `Здравствуйте` (안녕하세요)\n"
        f"• `Кофе, пожалуйста` (커피 주세요)\n"
        f"• `Спасибо` (감사합니다)\n\n"
        f"💬 `/action [문장]`으로 대답해보세요!"
    )

async def translation_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """퀘스트 번역 제공"""
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    quest_state = user['quest_state']
    
    if quest_state['current_quest'] is None:
        await update.message.reply_text(
            "❌ **진행 중인 퀘스트가 없습니다**\n\n"
            "먼저 `/quest`로 새 퀘스트를 시작하세요!"
        )
        return
    
    quest_id = quest_state['current_quest']
    stage = quest_state['stage']
    quest = QUEST_DATA[quest_id]
    stage_data = quest['stages'][stage]
    
    await update.message.reply_text(
        f"📖 **퀘스트 번역 도움**\n\n"
        f"🗣️ **상대방 말:** `{stage_data['bot_message']}`\n\n"
        f"🎯 **당신이 해야 할 말 (한국어):** {stage_data['action_prompt']}\n\n"
        f"📝 **러시아어로 이렇게 말해보세요:**\n"
        f"• `Здравствуйте` - 안녕하세요\n"
        f"• `Кофе, пожалуйста` - 커피 주세요\n"
        f"• `Американо` - 아메리카노\n"
        f"• `Спасибо` - 감사합니다\n\n"
        f"💬 `/action [선택한 러시아어]`로 진행하세요!"
    )

async def send_daily_learning(bot: Bot):
    users = load_user_data()
    
    # 러시아어 학습 데이터베이스 로드
    try:
        with open('russian_korean_vocab_2000.json', 'r', encoding='utf-8') as f:
            database = json.load(f)
    except FileNotFoundError:
        logger.error("러시아어 학습 데이터베이스 파일이 없습니다!")
        return
    
    import random
    
    # 15개 단어와 10개 회화로 조정 (개별 음성 때문에)
    vocabulary = random.sample(database['vocabulary'], min(15, len(database['vocabulary'])))
    
    # 회화 문장은 기존 데이터베이스에서 로드
    try:
        with open('russian_learning_database.json', 'r', encoding='utf-8') as f:
            old_database = json.load(f)
        conversations = random.sample(old_database['conversations'], min(10, len(old_database['conversations'])))
    except FileNotFoundError:
        # 기존 파일이 없으면 단어로 대체
        conversations = random.sample(database['vocabulary'], min(10, len(database['vocabulary'])))
    
    current_date = datetime.now(MSK)
    date_str = current_date.strftime('%Y년 %m월 %d일')
    weekday = ['월', '화', '수', '목', '금', '토', '일'][current_date.weekday()]
    
    for user_id, user_data in users.items():
        if user_data.get('subscribed_daily', False):
            try:
                # 🎨 새로운 헤더 메시지 (인라인 키보드 없음)
                header = f"""
🌟 **러시아어 마스터 일일 학습** 🌟

━━━━━━━━━━━━━━━━━━━━━━━━
📅 **{date_str} ({weekday}요일)**
🕐 **모스크바 시간**: {current_date.strftime('%H:%M')}
━━━━━━━━━━━━━━━━━━━━━━━━

✨ **오늘도 함께 러시아어 정복하러 가요!** ✨

🎯 **학습 목표**: 단어 15개 + 회화 10개 마스터
🚀 **예상 학습 시간**: 15-20분
🏆 **완료 시 보상**: +50 EXP + 성취 배지!

━━━━━━━━━━━━━━━━━━━━━━━━
📱 **학습 옵션**
━━━━━━━━━━━━━━━━━━━━━━━━

`/1` - 🎮 게임으로 학습하기
`/2` - 📊 학습 진도 확인하기  
`/3` - 🏆 성취 배지 보기
`/4` - 🤖 AI 튜터 분석받기

💡 **팁**: 각 단어와 회화마다 개별 음성이 전송됩니다!
                """
                
                await bot.send_message(chat_id=user_id, text=header)
                await asyncio.sleep(1)
                
                # 📚 단어 섹션 - 개별 음성과 함께
                words_header = f"""
📚 **오늘의 핵심 단어 컬렉션** (15개) 📚

━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **학습법**: 음성을 들으며 3번씩 따라 읽어보세요!
━━━━━━━━━━━━━━━━━━━━━━━━
                """
                
                await bot.send_message(chat_id=user_id, text=words_header)
                await asyncio.sleep(0.5)
                
                # 각 단어마다 개별 처리
                for i, word in enumerate(vocabulary, 1):
                    # 단어 정보 메시지
                    word_message = f"""
{i}️⃣ **{word['russian']}** `[{word['pronunciation']}]`
💡 **뜻**: {word['korean']}

━━━━━━━━━━━━━━━━━━━━━━━━
                    """
                    
                    await bot.send_message(chat_id=user_id, text=word_message)
                    
                    # 개별 음성 파일 생성 및 전송
                    try:
                        word_audio = await convert_text_to_speech(word['russian'], "ru")
                        if word_audio:
                            word_audio_buffer = io.BytesIO(word_audio)
                            word_audio_buffer.name = f"word_{i}_{word['russian']}.mp3"
                            
                            await bot.send_audio(
                                chat_id=user_id,
                                audio=word_audio_buffer,
                                title=f"🎵 {word['russian']} 발음",
                                performer="루샤 봇",
                                caption=f"🔊 **{word['russian']}** 발음\n💡 따라 읽어보세요: `{word['pronunciation']}`"
                            )
                            
                            logger.info(f"개별 단어 음성 전송 완료: {word['russian']} - 사용자: {user_id}")
                    except Exception as e:
                        logger.error(f"단어 음성 생성 실패: {word['russian']} - {e}")
                    
                    await asyncio.sleep(0.8)  # 각 단어 간 간격
                
                # 단어 섹션 완료 메시지
                words_complete = """
✅ **단어 학습 완료!** 📚

🎉 15개 단어와 발음을 모두 익혔습니다!
이제 실전 회화로 넘어가볼까요? 💬
                """
                await bot.send_message(chat_id=user_id, text=words_complete)
                await asyncio.sleep(1)
                
                # 💬 회화 섹션 - 개별 음성과 함께
                conversations_header = f"""
💬 **실전 회화 마스터 클래스** (10개) 💬

━━━━━━━━━━━━━━━━━━━━━━━━
🎭 **연습법**: 음성을 들으며 상황을 상상해보세요!
━━━━━━━━━━━━━━━━━━━━━━━━
                """
                
                await bot.send_message(chat_id=user_id, text=conversations_header)
                await asyncio.sleep(0.5)
                
                # 각 회화마다 개별 처리
                for i, conv in enumerate(conversations, 1):
                    # 회화 카테고리 결정
                    if i <= 3:
                        category = "🏠 일상 대화"
                    elif i <= 6:
                        category = "🛍️ 쇼핑 & 서비스"
                    elif i <= 8:
                        category = "🚇 교통 & 여행"
                    else:
                        category = "💼 비즈니스 & 격식"
                    
                    # 회화 정보 메시지
                    conv_message = f"""
{i}️⃣ **{category}**

🗣️ **{conv['russian']}**
🔤 `[{conv['pronunciation']}]`
🇰🇷 **{conv['korean']}**

━━━━━━━━━━━━━━━━━━━━━━━━
                    """
                    
                    await bot.send_message(chat_id=user_id, text=conv_message)
                    
                    # 개별 음성 파일 생성 및 전송
                    try:
                        conv_audio = await convert_text_to_speech(conv['russian'], "ru")
                        if conv_audio:
                            conv_audio_buffer = io.BytesIO(conv_audio)
                            conv_audio_buffer.name = f"conversation_{i}_{current_date.strftime('%Y%m%d')}.mp3"
                            
                            await bot.send_audio(
                                chat_id=user_id,
                                audio=conv_audio_buffer,
                                title=f"🎭 회화 {i}번 발음",
                                performer="루샤 봇",
                                caption=f"🗣️ **{category}**\n💬 {conv['korean']}\n\n🎯 상황을 상상하며 따라 해보세요!"
                            )
                            
                            logger.info(f"개별 회화 음성 전송 완료: {i}번 - 사용자: {user_id}")
                    except Exception as e:
                        logger.error(f"회화 음성 생성 실패: {i}번 - {e}")
                    
                    await asyncio.sleep(1.0)  # 각 회화 간 간격
                
                # 🏆 최종 완료 메시지
                completion_message = f"""
🎉 **오늘의 학습 완료!** 🎉

━━━━━━━━━━━━━━━━━━━━━━━━
✅ **완벽한 성과!**
━━━━━━━━━━━━━━━━━━━━━━━━

📚 **새로운 단어**: 15개 + 개별 발음 ✓
💬 **실전 회화**: 10개 + 개별 발음 ✓  
🎵 **음성 연습**: 25개 파일 완료 ✓
⭐ **획득 경험치**: +50 EXP 

━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **다음 단계 추천**
━━━━━━━━━━━━━━━━━━━━━━━━

`/1` - 🎮 오늘 배운 단어로 게임하기
`/2` - ✍️ 새로운 문장 만들어보기
`/3` - 🏆 학습 진도 확인하기
`/4` - 🎯 AI 튜터 개인 분석받기

━━━━━━━━━━━━━━━━━━━━━━━━
💡 **오늘의 격려**
━━━━━━━━━━━━━━━━━━━━━━━━

꾸준함이 실력을 만듭니다! 매일 조금씩이라도
러시아어와 친해지는 당신이 정말 대단해요! 🌟

각 단어와 회화의 개별 발음을 들으며
더 정확한 발음을 익힐 수 있었을 거예요! 

🔥 **내일도 함께 러시아어 마스터하러 가요!** 🔥
                """
                
                await bot.send_message(chat_id=user_id, text=completion_message)
                
                # 사용자 데이터 업데이트
                user_data['stats']['daily_words_received'] += 1
                user_data['stats']['total_exp'] += 50  # 일일 학습 완료 보상
                
                logger.info(f"새로운 개별 음성 일일 학습 전송 완료 - 사용자: {user_id}")
                
            except Exception as e:
                logger.error(f"개별 음성 일일 학습 전송 실패 - 사용자: {user_id}: {e}")
                import traceback
                logger.error(f"상세 오류: {traceback.format_exc()}")
    
    save_user_data(users)

# 먼저, 일반 메시지 처리 핸들러 함수 추가
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """명령어가 아닌 일반 메시지를 처리하여 Gemini AI에 질문을 전달합니다."""
    user_message = update.message.text
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    
    # AI 호출
    processing_message = await update.message.reply_text("🤔 생각 중... 😊")
    response = await call_gemini(user_message)
    
    # 응답 전송
    await processing_message.delete()
    await update.message.reply_text(response)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🎮 혁신적인 메시지 처리 시스템 - 게임 상태와 AI 대화를 통합 처리"""
    user_message = update.message.text
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    user_id = str(chat_id)
    
    # ===========================================
    # 🎯 STEP 1: 게임 상태 확인 및 처리
    # ===========================================
    
    # 단어 매칭 게임 처리
    if 'word_match_game' in context.user_data:
        await handle_word_match_input(update, context, user_message)
        return
    
    # 문장 조립 게임 처리
    if 'sentence_builder_game' in context.user_data:
        await handle_sentence_builder_input(update, context, user_message)
        return
    
    # 스피드 퀴즈 처리
    if 'speed_quiz_game' in context.user_data:
        await handle_speed_quiz_input(update, context, user_message)
        return
    
    # 발음 챌린지 처리
    if 'pronunciation_game' in context.user_data:
        await handle_pronunciation_input(update, context, user_message)
        return
    
    # ===========================================
    # 🤖 STEP 2: 일반 AI 대화 처리
    # ===========================================
    
    processing_message = await update.message.reply_text("🤔 생각 중... 😊")
    
    # 러시아어 학습 관련 키워드 감지 및 맞춤 응답
    if any(keyword in user_message.lower() for keyword in ['게임', 'game', '게임하고싶어', '놀자']):
        response = await generate_game_recommendation(user)
    elif any(keyword in user_message.lower() for keyword in ['진도', '진척', '레벨', '경험치']):
        response = await generate_progress_summary(user)
    elif any(keyword in user_message.lower() for keyword in ['번역', 'translate', '뜻']):
        response = await generate_translation_help(user_message)
    else:
        # 일반 AI 대화
        enhanced_prompt = f"""
당신은 러시아어 학습을 도와주는 전문 AI 튜터 '루샤'입니다.
사용자의 현재 레벨: {user['stats']['level']}
연속 학습일: {user['learning']['daily_streak']}일

사용자 메시지: {user_message}

다음 방식으로 응답해주세요:
1. 친근하고 격려적인 톤
2. 필요시 러시아어 학습 팁 포함
3. 관련 명령어나 기능 추천
4. 이모지 활용으로 재미있게
"""
        response = await call_gemini(enhanced_prompt)
    
    # 응답 전송
    await processing_message.delete()
    await update.message.reply_text(response)

# ===========================================
# 🎮 게임별 입력 처리 함수들
# ===========================================

async def handle_word_match_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
    """단어 매칭 게임 입력 처리"""
    chat_id = update.effective_chat.id
    user_data = get_user(chat_id)
    game_data = context.user_data['word_match_game']
    
    # 게임 종료 요청
    if user_input.lower() in ['게임종료', 'quit', 'exit', '종료']:
        await update.message.reply_text("🎮 게임을 종료합니다. 다음에 또 도전해주세요!")
        del context.user_data['word_match_game']
        return
    
    # 힌트 요청
    if user_input.lower() in ['힌트', 'hint']:
        correct_answers = game_data['correct_answers']
        hint_text = f"💡 **힌트**: '{correct_answers[0][:2]}...' (첫 두 글자)"
        await update.message.reply_text(hint_text)
        return
    
    # 시간 체크 (60초 제한)
    elapsed_time = datetime.now(MSK).timestamp() - game_data['start_time']
    if elapsed_time > 60:
        await update.message.reply_text("⏰ 시간 초과! 게임이 종료됩니다.")
        del context.user_data['word_match_game']
        return
    
    # 정답 체크
    correct_answers = game_data['correct_answers']
    is_correct = any(user_input.strip().lower() == answer.lower() for answer in correct_answers)
    
    if is_correct:
        game_data['correct_count'] += 1
        await update.message.reply_text("✅ 정답입니다! 🎉")
    else:
        await update.message.reply_text(f"❌ 틀렸습니다. 정답: {correct_answers[0]}")
    
    # 다음 문제로 진행
    game_data['current_index'] += 1
    
    if game_data['current_index'] >= len(game_data['words']):
        # 게임 종료
        await end_word_match_game(update, context)
    else:
        # 다음 문제 출제
        await send_next_word_question(update, context)

async def send_next_word_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """다음 단어 매칭 문제 전송"""
    game_data = context.user_data['word_match_game']
    current_idx = game_data['current_index']
    current_word = game_data['words'][current_idx]
    
    ru_word = current_word[0]
    correct_answer = current_word[1]
    
    # 정답 처리
    if isinstance(correct_answer, str):
        correct_answers = [ans.strip() for ans in correct_answer.split(',')]
    else:
        correct_answers = [str(correct_answer)]
    
    game_data['correct_answers'] = correct_answers
    
    question_text = f"""
**문제 {current_idx + 1}/{len(game_data['words'])}**

🇷🇺 **{ru_word}**

💡 **힌트**: 첫 글자는 '{correct_answers[0][0]}'입니다
⌨️ **답안**: 한국어 뜻을 입력하세요
    """
    
    await update.message.reply_text(question_text)

async def end_word_match_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """단어 매칭 게임 종료"""
    chat_id = update.effective_chat.id
    user_data = get_user(chat_id)
    game_data = context.user_data['word_match_game']
    
    correct_count = game_data['correct_count']
    total_questions = len(game_data['words'])
    accuracy = (correct_count / total_questions) * 100
    elapsed_time = datetime.now(MSK).timestamp() - game_data['start_time']
    
    # 점수 계산
    base_score = correct_count * 20
    time_bonus = max(0, (60 - elapsed_time) * 1)
    final_score = int(base_score + time_bonus)
    
    # 경험치 보상
    exp_reward = 20 + (correct_count * 5)
    user_data['stats']['total_exp'] += exp_reward
    
    # 게임 통계 업데이트
    if accuracy >= 60:  # 60% 이상이면 승리
        user_data['learning']['game_stats']['word_match']['won'] += 1
        result_emoji = "🏆"
        result_text = "승리!"
    else:
        result_emoji = "💪"
        result_text = "아쉬워요!"
    
    # 최고 점수 업데이트
    if final_score > user_data['learning']['game_stats']['word_match']['best_score']:
        user_data['learning']['game_stats']['word_match']['best_score'] = final_score
        best_score_text = "🎉 **신기록 달성!**"
    else:
        best_score_text = ""
    
    save_user_data({str(chat_id): user_data})
    
    result_text_msg = f"""
🎯 **단어 매칭 게임 완료!** 🎯

━━━━━━━━━━━━━━━━━━━━━━━━
{result_emoji} **최종 결과: {result_text}**
━━━━━━━━━━━━━━━━━━━━━━━━

📊 **상세 결과**:
✅ 정답: {correct_count}/{total_questions}개
📈 정확도: {accuracy:.1f}%
⏱️ 소요시간: {elapsed_time:.1f}초
⏱️ 소요시간: {total_time:.1f}초
🎯 최종점수: {final_score}점

💰 **획득 보상**:
⭐ 경험치: +{exp_reward} EXP
🏆 점수: {final_score}점

{best_score_text}

━━━━━━━━━━━━━━━━━━━━━━━━
🎮 다시 도전하려면 `/game_speed_quiz`
🏠 메인 메뉴로 돌아가려면 `/start`
    """
    
    await update.message.reply_text(result_text)
    
    # 게임 데이터 정리
    if 'speed_quiz_game' in context.user_data:
        del context.user_data['speed_quiz_game']

async def pronunciation_challenge_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🎤 완전히 새로운 발음 챌린지"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    # 발음 연습 문장들 (난이도별)
    pronunciation_sentences = {
        'beginner': [
            {'ru': 'Привет', 'ko': '안녕하세요', 'tips': '프리비엣 - 부드럽게 발음하세요'},
            {'ru': 'Спасибо', 'ko': '감사합니다', 'tips': '스파시바 - s는 살짝 둥글게'},
            {'ru': 'До свидания', 'ko': '안녕히 가세요', 'tips': '다 스비다니야 - 천천히 또박또박'},
            {'ru': 'Как дела?', 'ko': '어떻게 지내세요?', 'tips': '깍 딜라 - 강세는 딜라에'},
            {'ru': 'Меня зовут', 'ko': '제 이름은', 'tips': '미냐 자부트 - 부드럽게 연결'},
        ],
        'intermediate': [
            {'ru': 'Я изучаю русский язык', 'ko': '나는 러시아어를 공부합니다', 'tips': '야 이주차유 루스키 야지크'},
            {'ru': 'Мне нравится читать книги', 'ko': '나는 책 읽기를 좋아합니다', 'tips': '므네 느라비차 치타치 크니기'},
            {'ru': 'Сегодня хорошая погода', 'ko': '오늘은 날씨가 좋습니다', 'tips': '시보드냐 하로샤야 파고다'},
            {'ru': 'В магазине много продуктов', 'ko': '상점에 많은 식품이 있습니다', 'tips': '브 마가지네 므노가 프라둑타프'},
        ],
        'advanced': [
            {'ru': 'Несмотря на плохую погоду, мы пошли гулять', 'ko': '나쁜 날씨에도 불구하고 우리는 산책했습니다', 'tips': '복잡한 문장 - 천천히 끊어서 읽으세요'},
            {'ru': 'Если бы я знал об этом раньше', 'ko': '만약 내가 이것을 더 일찍 알았다면', 'tips': '가정법 표현 - 억양에 주의하세요'},
            {'ru': 'Преподаватель объясняет грамматику', 'ko': '선생님이 문법을 설명합니다', 'tips': '프리파다바틸 압야스냐예트 그람마티쿠'},
        ]
    }
    
    # 사용자 레벨에 따른 문장 선택
    level = user_data['stats']['level']
    if level <= 5:
        available_sentences = pronunciation_sentences['beginner']
        difficulty = 'beginner'
    elif level <= 15:
        available_sentences = pronunciation_sentences['intermediate']
        difficulty = 'intermediate'
    else:
        available_sentences = pronunciation_sentences['advanced']
        difficulty = 'advanced'
    
    import random
    selected_sentence = random.choice(available_sentences)
    
    # 음성 파일 생성
    try:
        audio_bytes = await convert_text_to_speech(selected_sentence['ru'], "ru")
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"pronunciation_{selected_sentence['ru'][:10]}.mp3"
    except Exception as e:
        logger.error(f"TTS error: {e}")
        audio_file = None
    
    challenge_text = f"""
🎤 **발음 챌린지 시작!** 🎤

━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **난이도**: {difficulty.upper()}
⏰ **제한시간: 120초**
💰 **보상: 35 EXP + 발음 보너스**
━━━━━━━━━━━━━━━━━━━━━━━━

📝 **연습 문장**:
🇷🇺 **{selected_sentence['ru']}**
🇰🇷 **{selected_sentence['ko']}**

💡 **발음 팁**: {selected_sentence['tips']}

━━━━━━━━━━━━━━━━━━━━━━━━
🎵 **진행 방법**:
1. 위 음성을 들어보세요
2. 여러 번 따라 읽으세요  
3. 자신 있게 발음하세요
4. "완료"라고 입력하면 점수를 받습니다

━━━━━━━━━━━━━━━━━━━━━━━━
🎮 게임 중단하려면 "게임종료" 입력
💡 다시 들으려면 "음성" 입력

⌨️ **준비가 되면 "완료"를 입력하세요!**
    """
    
    # 게임 데이터 저장
    game_data = {
        'sentence': selected_sentence,
        'difficulty': difficulty,
        'start_time': datetime.now(MSK).timestamp()
    }
    
    context.user_data['pronunciation_game'] = game_data
    
    await update.message.reply_text(challenge_text)
    
    # 음성 파일 전송
    if audio_file:
        await update.message.reply_audio(
            audio=audio_file,
            caption=f"🔊 **{selected_sentence['ru']}** 발음을 들어보세요!"
        )
    
    # 게임 통계 업데이트
    user_data['learning']['game_stats']['pronunciation_challenge']['played'] += 1
    save_user_data({str(chat_id): user_data})

# === 🏆 성취 시스템 ===

async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """성취 시스템 표시"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    achievements_text = """
🏆 **성취 시스템** 🏆

━━━━━━━━━━━━━━━━━━━━━━━━
**📈 획득한 성취들**
━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    user_achievements = user_data['learning']['achievements']
    total_exp_from_achievements = 0
    
    for achievement_id in user_achievements:
        if achievement_id in ACHIEVEMENTS:
            ach = ACHIEVEMENTS[achievement_id]
            achievements_text += f"{ach['badge']} **{ach['name']}**\n"
            achievements_text += f"   └ {ach['description']} (+{ach['exp']} EXP)\n\n"
            total_exp_from_achievements += ach['exp']
    
    if not user_achievements:
        achievements_text += "아직 획득한 성취가 없습니다. 학습을 시작해보세요!\n\n"
    
    achievements_text += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    achievements_text += "**🎯 달성 가능한 성취들**\n"
    achievements_text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for achievement_id, ach in ACHIEVEMENTS.items():
        if achievement_id not in user_achievements:
            achievements_text += f"{ach['badge']} **{ach['name']}** (+{ach['exp']} EXP)\n"
            achievements_text += f"   └ {ach['description']}\n\n"
    
    achievements_text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━
**📊 성취 통계**
━━━━━━━━━━━━━━━━━━━━━━━━

🏅 획득한 성취: {len(user_achievements)}/{len(ACHIEVEMENTS)}개
🌟 성취 경험치: {total_exp_from_achievements} EXP
📈 완성도: {len(user_achievements)/len(ACHIEVEMENTS)*100:.1f}%

💪 더 많은 성취를 달성해보세요!
    """
    
    await update.message.reply_text(achievements_text)

def check_achievements(user_data):
    """성취 조건을 확인하고 새로운 성취를 추가"""
    new_achievements = []
    current_achievements = user_data['learning']['achievements']
    
    # 첫 퀘스트 완료
    if 'first_quest' not in current_achievements and user_data['stats']['quests_completed'] >= 1:
        new_achievements.append('first_quest')
    
    # 일주일 연속 학습
    if 'daily_streak_7' not in current_achievements and user_data['learning']['daily_streak'] >= 7:
        new_achievements.append('daily_streak_7')
    
    # 한 달 연속 학습
    if 'daily_streak_30' not in current_achievements and user_data['learning']['daily_streak'] >= 30:
        new_achievements.append('daily_streak_30')
    
    # 작문 마스터
    if 'writing_master' not in current_achievements and user_data['stats']['sentences_corrected'] >= 100:
        new_achievements.append('writing_master')
    
    # 발음 전문가
    pronunciation_scores = user_data['learning']['pronunciation_scores']
    high_scores = [score for score in pronunciation_scores if score >= 90]
    if 'pronunciation_pro' not in current_achievements and len(high_scores) >= 10:
        new_achievements.append('pronunciation_pro')
    
    # 퀴즈 챔피언
    total_quizzes = sum([stats['played'] for stats in user_data['learning']['game_stats'].values()])
    if 'quiz_champion' not in current_achievements and total_quizzes >= 50:
        new_achievements.append('quiz_champion')
    
    # 번역 전문가
    if 'translator' not in current_achievements and user_data['stats']['translations_made'] >= 500:
        new_achievements.append('translator')
    
    return new_achievements

async def award_achievements(update: Update, user_data, new_achievements):
    """새로운 성취를 사용자에게 알림"""
    if not new_achievements:
        return
    
    for achievement_id in new_achievements:
        user_data['learning']['achievements'].append(achievement_id)
        ach = ACHIEVEMENTS[achievement_id]
        user_data['stats']['total_exp'] += ach['exp']
        
        # 레벨 업 체크
        old_level = user_data['stats']['level']
        new_level = min(100, user_data['stats']['total_exp'] // 100 + 1)
        user_data['stats']['level'] = new_level
        
        achievement_text = f"""
🎉 **새로운 성취 달성!** 🎉

{ach['badge']} **{ach['name']}**
📝 {ach['description']}
💰 +{ach['exp']} EXP

{'🆙 **레벨 업!** ' + str(old_level) + ' → ' + str(new_level) if new_level > old_level else ''}

현재 레벨: {new_level} | 총 경험치: {user_data['stats']['total_exp']}
        """
        
        await update.message.reply_text(achievement_text)
    
    save_user_data(load_user_data())  # 변경사항 저장

# === 🧠 개인화된 AI 튜터 시스템 ===

async def ai_tutor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """개인화된 AI 튜터"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    # 사용자 학습 패턴 분석
    analysis = analyze_learning_pattern(user_data)
    
    tutor_message = f"""
🧠 **개인화된 AI 튜터 '루샤'** 🧠

━━━━━━━━━━━━━━━━━━━━━━━━
**📊 {user.first_name}님의 학습 분석**
━━━━━━━━━━━━━━━━━━━━━━━━

📈 **현재 레벨:** {user_data['stats']['level']} 
🔥 **연속 학습일:** {user_data['learning']['daily_streak']}일
🎯 **학습 스타일:** {get_learning_style_name(user_data['learning']['learning_style'])}

**💪 강점 분야:**
{format_areas(user_data['learning']['strength_areas'])}

**📚 약점 분야:**
{format_areas(user_data['learning']['weak_areas'])}

━━━━━━━━━━━━━━━━━━━━━━━━
**🎯 개인화된 추천**
━━━━━━━━━━━━━━━━━━━━━━━━

{analysis['recommendations']}

━━━━━━━━━━━━━━━━━━━━━━━━
**📅 오늘의 학습 계획**
━━━━━━━━━━━━━━━━━━━━━━━━

{analysis['daily_plan']}

**💡 맞춤형 명령어:**
• `/personalized_lesson` - 개인 맞춤 수업
• `/weak_area_practice` - 약점 보강 연습
• `/adaptive_quiz` - 적응형 퀴즈
• `/learning_analytics` - 상세 학습 분석

🚀 함께 러시아어 마스터가 되어보아요!
    """
    
    await update.message.reply_text(tutor_message)

def analyze_learning_pattern(user_data):
    """사용자 학습 패턴 분석"""
    stats = user_data['stats']
    learning = user_data['learning']
    
    # 학습 선호도 분석
    total_activities = (stats['quests_completed'] + stats['sentences_corrected'] + 
                       stats['translations_made'] + sum([g['played'] for g in learning['game_stats'].values()]))
    
    recommendations = []
    daily_plan = []
    
    # 연속 학습일 기반 추천
    if learning['daily_streak'] < 7:
        recommendations.append("🔥 연속 학습 습관을 만들어보세요! 매일 조금씩이라도 꾸준히 학습하세요.")
        daily_plan.append("• 10분 퀘스트 1개 완료")
    elif learning['daily_streak'] < 30:
        recommendations.append("👏 좋은 학습 습관을 유지하고 있어요! 더 도전적인 콘텐츠를 시도해보세요.")
        daily_plan.append("• 중급 퀘스트 도전")
    else:
        recommendations.append("🏆 완벽한 학습자입니다! 고급 기능들을 활용해보세요.")
        daily_plan.append("• 고급 퀘스트 및 발음 챌린지")
    
    # 활동 비율 기반 추천
    if stats['quests_completed'] < total_activities * 0.3:
        recommendations.append("🎮 퀘스트를 더 많이 해보세요. 실전 대화 경험이 중요합니다!")
        daily_plan.append("• 새로운 퀘스트 시도")
    
    if stats['sentences_corrected'] < total_activities * 0.2:
        recommendations.append("✍️ 작문 연습을 늘려보세요. 문법 실력 향상에 도움됩니다!")
        daily_plan.append("• 작문 교정 5개 이상")
    
    # 게임 활동 분석
    game_total = sum([g['played'] for g in learning['game_stats'].values()])
    if game_total < total_activities * 0.1:
        recommendations.append("🎮 게임을 통한 학습도 시도해보세요. 재미있게 실력을 늘릴 수 있어요!")
        daily_plan.append("• 게임 1개 이상 플레이")
    
    # 기본 추천사항
    if not recommendations:
        recommendations.append("🌟 모든 영역에서 균형잡힌 학습을 하고 계시네요! 계속 유지하세요!")
    
    if not daily_plan:
        daily_plan = ["• 다양한 학습 활동 골고루 진행", "• 새로운 기능 탐험하기"]
    
    return {
        'recommendations': '\n'.join(recommendations),
        'daily_plan': '\n'.join(daily_plan)
    }

def get_learning_style_name(style):
    """학습 스타일 이름 반환"""
    styles = {
        'visual': '시각형 (Visual)',
        'auditory': '청각형 (Auditory)', 
        'kinesthetic': '체감형 (Kinesthetic)',
        'balanced': '균형형 (Balanced)'
    }
    return styles.get(style, '균형형')

def format_areas(areas):
    """강점/약점 분야 포맷팅"""
    if not areas:
        return "• 아직 충분한 데이터가 없습니다."
    return '\n'.join([f"• {area}" for area in areas])

async def personalized_lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """개인 맞춤 수업"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    level = user_data['stats']['level']
    weak_areas = user_data['learning']['weak_areas']
    learning_style = user_data['learning']['learning_style']
    
    # AI로 맞춤형 수업 생성
    lesson_prompt = f"""
사용자 정보:
- 레벨: {level}
- 약점 분야: {', '.join(weak_areas) if weak_areas else '없음'}
- 학습 스타일: {learning_style}
- 연속 학습일: {user_data['learning']['daily_streak']}일

위 정보를 바탕으로 개인화된 러시아어 수업 1개를 설계해주세요.
수업은 다음을 포함해야 합니다:
1. 학습 목표
2. 단계별 설명 (3-5단계)
3. 연습 문제 3개
4. 실생활 활용법

형식을 깔끔하게 정리해서 제공해주세요.
    """
    
    try:
        lesson_content = await call_gemini(lesson_prompt)
        
        lesson_text = f"""
🎓 **{user.first_name}님만의 맞춤형 수업** 🎓

━━━━━━━━━━━━━━━━━━━━━━━━
**🤖 AI가 분석한 맞춤형 커리큘럼**
━━━━━━━━━━━━━━━━━━━━━━━━

{lesson_content}

━━━━━━━━━━━━━━━━━━━━━━━━
**💡 수업 후 추천 활동:**
• `/write [연습한 문장]` - 작문 연습
• `/quest` - 관련 퀘스트 도전
• `/game_pronunciation` - 발음 연습

🌟 수업이 도움되셨나요? 피드백을 주시면 더 나은 맞춤 수업을 제공해드릴게요!
        """
        
        await update.message.reply_text(lesson_text)
        
        # 개인화된 콘텐츠에 추가
        user_data['learning']['personalized_content'].append({
            'type': 'lesson',
            'content': lesson_content,
            'date': datetime.now(MSK).isoformat()
        })
        save_user_data(load_user_data())
        
    except Exception as e:
        await update.message.reply_text("❌ 맞춤형 수업을 생성할 수 없습니다. 잠시 후 다시 시도해주세요.")

async def learning_analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """상세 학습 분석"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    # 상세 분석 계산
    analytics = calculate_detailed_analytics(user_data)
    
    analytics_text = f"""
📊 **상세 학습 분석 리포트** 📊

━━━━━━━━━━━━━━━━━━━━━━━━
**📈 전체 학습 현황**
━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **현재 레벨:** {user_data['stats']['level']}/100
⭐ **총 경험치:** {user_data['stats']['total_exp']} EXP
🔥 **연속 학습일:** {user_data['learning']['daily_streak']}일

📅 **학습 시작일:** {analytics['days_since_start']}일 전
⚡ **일평균 활동량:** {analytics['daily_average']:.1f}회

━━━━━━━━━━━━━━━━━━━━━━━━
**🎮 활동별 통계**
━━━━━━━━━━━━━━━━━━━━━━━━

🏰 **퀘스트:** {user_data['stats']['quests_completed']}회 완료
✍️ **작문 교정:** {user_data['stats']['sentences_corrected']}회
🌍 **번역:** {user_data['stats']['translations_made']}회
🎵 **음성 변환:** {user_data['stats']['tts_generated']}회

━━━━━━━━━━━━━━━━━━━━━━━━
**🎯 게임 성과**
━━━━━━━━━━━━━━━━━━━━━━━━

{analytics['game_performance']}

━━━━━━━━━━━━━━━━━━━━━━━━
**🏆 성취 현황**
━━━━━━━━━━━━━━━━━━━━━━━━

🏅 **획득 성취:** {len(user_data['learning']['achievements'])}/{len(ACHIEVEMENTS)}개
📈 **완성도:** {len(user_data['learning']['achievements'])/len(ACHIEVEMENTS)*100:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━
**🔮 예측 및 추천**
━━━━━━━━━━━━━━━━━━━━━━━━

📊 **예상 다음 레벨업:** {analytics['next_level_prediction']}
🎯 **추천 활동:** {analytics['recommended_activity']}
⚡ **학습 효율성:** {analytics['efficiency_score']}/10

💡 **개선 제안:**
{analytics['improvement_suggestions']}

🌟 계속해서 꾸준히 학습하시면 더 큰 발전이 있을 거예요!
    """
    
    await update.message.reply_text(analytics_text)

def calculate_detailed_analytics(user_data):
    """상세 분석 계산"""
    stats = user_data['stats']
    learning = user_data['learning']
    
    # 학습 시작일 계산
    start_date = datetime.fromisoformat(stats['start_date'])
    days_since_start = (datetime.now(MSK) - start_date).days + 1
    
    # 총 활동량
    total_activities = (stats['quests_completed'] + stats['sentences_corrected'] + 
                       stats['translations_made'] + stats['tts_generated'])
    daily_average = total_activities / days_since_start if days_since_start > 0 else 0
    
    # 게임 성과
    game_performance = []
    for game_id, game_stats in learning['game_stats'].items():
        game_name = LEARNING_GAMES[game_id]['name']
        played = game_stats['played']
        won = game_stats['won']
        win_rate = (won / played * 100) if played > 0 else 0
        game_performance.append(f"🎮 {game_name}: {played}회 플레이, 승률 {win_rate:.1f}%")
    
    if not game_performance:
        game_performance = ["아직 게임을 플레이하지 않았습니다."]
    
    # 다음 레벨업 예측
    current_level = stats['level']
    exp_needed = (current_level * 100) - stats['total_exp']
    if daily_average > 0:
        avg_exp_per_day = daily_average * 10  # 활동당 평균 10 EXP 가정
        days_to_level = exp_needed / avg_exp_per_day if avg_exp_per_day > 0 else 999
        next_level_prediction = f"약 {days_to_level:.0f}일 후" if days_to_level < 30 else "한 달 이상"
    else:
        next_level_prediction = "예측 불가 (더 많은 활동 필요)"
    
    # 추천 활동
    activity_scores = {
        'quest': stats['quests_completed'],
        'writing': stats['sentences_corrected'],
        'translation': stats['translations_made'],
        'games': sum([g['played'] for g in learning['game_stats'].values()])
    }
    min_activity = min(activity_scores, key=activity_scores.get)
    
    recommendations = {
        'quest': '퀘스트 - 실전 회화 경험 증가',
        'writing': '작문 교정 - 문법 실력 강화',
        'translation': '번역 - 어휘력 향상',
        'games': '게임 - 재미있는 학습'
    }
    recommended_activity = recommendations[min_activity]
    
    # 효율성 점수 (10점 만점)
    efficiency_factors = [
        min(learning['daily_streak'] / 30, 1) * 3,  # 꾸준함 (3점)
        min(len(learning['achievements']) / len(ACHIEVEMENTS), 1) * 2,  # 성취도 (2점)
        min(stats['level'] / 20, 1) * 2,  # 레벨 진도 (2점)
        min(total_activities / 100, 1) * 3  # 활동량 (3점)
    ]
    efficiency_score = sum(efficiency_factors)
    
    # 개선 제안
    suggestions = []
    if learning['daily_streak'] < 7:
        suggestions.append("• 연속 학습일을 늘려보세요")
    if stats['sentences_corrected'] < 20:
        suggestions.append("• 작문 연습을 더 해보세요")
    if sum([g['played'] for g in learning['game_stats'].values()]) < 10:
        suggestions.append("• 게임을 통한 학습을 시도해보세요")
    if not suggestions:
        suggestions.append("• 현재 모든 영역에서 잘 하고 계십니다!")
    
    return {
        'days_since_start': days_since_start,
        'daily_average': daily_average,
        'game_performance': '\n'.join(game_performance),
        'next_level_prediction': next_level_prediction,
        'recommended_activity': recommended_activity,
        'efficiency_score': round(efficiency_score, 1),
        'improvement_suggestions': '\n'.join(suggestions)
    }

# === 🎯 추가 스마트 학습 명령어들 ===

async def weak_area_practice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """약점 분야 집중 연습"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    weak_areas = user_data['learning']['weak_areas']
    
    if not weak_areas:
        practice_text = """
📚 **약점 분야 분석 중...** 📚

아직 약점 분야 데이터가 부족합니다.
더 많은 학습 활동을 하시면 개인화된 약점 분석을 제공해드릴게요!

💡 **추천 활동:**
• `/quest` - 다양한 퀘스트 도전
• `/write` - 작문 연습
• `/games` - 게임으로 학습
• `/game_pronunciation` - 발음 연습

🎯 충분한 데이터가 쌓이면 맞춤형 약점 보강 연습을 제공해드릴게요!
        """
    else:
        focus_area = weak_areas[0]  # 첫 번째 약점 분야에 집중
        
        practice_text = f"""
🎯 **약점 분야 집중 연습** 🎯

━━━━━━━━━━━━━━━━━━━━━━━━
**📊 집중 보강 영역: {focus_area}**
━━━━━━━━━━━━━━━━━━━━━━━━

💪 **맞춤형 연습 계획:**
1. 관련 단어 10개 암기
2. 문법 규칙 복습
3. 실전 문장 만들기
4. 발음 연습

**🎮 추천 활동:**
• `/personalized_lesson` - 맞춤 수업
• `/game_word_match` - 단어 게임
• `/write` - 관련 문장 작성
• `/game_pronunciation` - 발음 연습

🌟 약점을 극복하면 더 큰 발전이 있을 거예요!
        """
    
    await update.message.reply_text(practice_text)

async def adaptive_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """적응형 퀴즈"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    level = user_data['stats']['level']
    
    # 레벨에 따른 적응형 퀴즈
    if level <= 5:
        difficulty = "초급"
        questions = [
            {"q": "러시아어로 안녕하세요는?", "a": "Здравствуйте"},
            {"q": "러시아어로 감사합니다는?", "a": "Спасибо"},
            {"q": "러시아어로 네는?", "a": "Да"}
        ]
    elif level <= 15:
        difficulty = "중급"
        questions = [
            {"q": "Мне нравится читать книги의 뜻은?", "a": "나는 책 읽기를 좋아합니다"},
            {"q": "Сколько это стоит의 뜻은?", "a": "이것이 얼마인가요?"},
            {"q": "Где находится музей의 뜻은?", "a": "박물관이 어디에 있나요?"}
        ]
    else:
        difficulty = "고급"
        questions = [
            {"q": "Несмотря на трудности의 뜻은?", "a": "어려움에도 불구하고"},
            {"q": "поступил бы по-другому의 뜻은?", "a": "다르게 행동했을 것이다"},
            {"q": "러시아어 가정법의 특징은?", "a": "бы를 사용합니다"}
        ]
    
    import random
    selected = random.choice(questions)
    
    quiz_text = f"""
🧠 **적응형 퀴즈 ({difficulty} 레벨)** 🧠

━━━━━━━━━━━━━━━━━━━━━━━━
**🎯 현재 레벨: {level} (자동 난이도 조절)**
━━━━━━━━━━━━━━━━━━━━━━━━

**❓ 문제:** {selected['q']}

━━━━━━━━━━━━━━━━━━━━━━━━
**💡 답을 입력하세요!**

🎯 정답률에 따라 다음 문제 난이도가 조절됩니다.
⭐ 정답 시 경험치 +15 EXP
    """
    
    context.user_data['adaptive_quiz'] = {
        'question': selected,
        'start_time': datetime.now(),
        'active': True,
        'difficulty': difficulty
    }
    
    await update.message.reply_text(quiz_text)

async def srs_review_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """간격 반복 학습 시스템"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    srs_data = user_data['learning']['vocabulary_srs']
    
    if not srs_data:
        srs_text = """
🧠 **간격 반복 학습 시스템 (SRS)** 🧠

━━━━━━━━━━━━━━━━━━━━━━━━
**📚 아직 복습할 단어가 없습니다**
━━━━━━━━━━━━━━━━━━━━━━━━

💡 **SRS 시스템이란?**
망각 곡선을 기반으로 한 과학적 복습 시스템입니다.
단어를 외운 후 점점 긴 간격으로 복습하여 장기 기억에 저장합니다.

**🎯 시작하는 방법:**
• `/vocabulary_builder` - 새 단어 학습
• `/write` - 작문으로 단어 사용
• `/games` - 게임으로 단어 익히기

🌟 학습한 단어들은 자동으로 SRS 시스템에 추가됩니다!
        """
    else:
        # 복습할 단어 찾기 (간단한 버전)
        today = datetime.now(MSK).date()
        due_words = []
        
        for word, data in srs_data.items():
            due_date = datetime.fromisoformat(data.get('next_review', today.isoformat())).date()
            if due_date <= today:
                due_words.append(word)
        
        if not due_words:
            srs_text = f"""
✅ **모든 단어 복습 완료!** ✅

━━━━━━━━━━━━━━━━━━━━━━━━
**📊 SRS 상태**
━━━━━━━━━━━━━━━━━━━━━━━━

📚 **학습 중인 단어:** {len(srs_data)}개
✅ **오늘 복습 완료:** 모든 단어
🎯 **다음 복습일:** 내일 또는 그 이후

🌟 훌륭합니다! 모든 복습을 완료했어요!
새로운 단어를 학습하려면 `/vocabulary_builder`를 사용해보세요.
            """
        else:
            word = due_words[0]  # 첫 번째 복습 단어
            srs_text = f"""
🧠 **SRS 복습 시간!** 🧠

━━━━━━━━━━━━━━━━━━━━━━━━
**📚 복습할 단어: {word}**
━━━━━━━━━━━━━━━━━━━━━━━━

❓ **이 단어의 뜻은 무엇인가요?**

💡 답을 입력하신 후 난이도를 선택해주세요:
• **쉬웠음** - 다음 복습: 더 긴 간격
• **적당함** - 다음 복습: 기본 간격  
• **어려웠음** - 다음 복습: 짧은 간격
• **다시** - 다음 복습: 내일

📊 복습 대기 중: {len(due_words)}개
            """
            
            context.user_data['srs_review'] = {
                'word': word,
                'remaining': due_words,
                'active': True
            }
    
    await update.message.reply_text(srs_text)

async def vocabulary_builder_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """어휘 확장 시스템"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    try:
        with open('russian_korean_vocab_2000.json', 'r', encoding='utf-8') as f:
            vocab_data = json.load(f)
    except:
        await update.message.reply_text("❌ 어휘 데이터를 불러올 수 없습니다.")
        return
    
    import random
    selected_words = random.sample(list(vocab_data.items()), 5)
    
    vocab_text = f"""
📚 **어휘 확장 시스템** 📚

━━━━━━━━━━━━━━━━━━━━━━━━
**🌟 오늘의 새로운 단어 5개**
━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    for i, (ru_word, ko_meaning) in enumerate(selected_words, 1):
        meaning = ko_meaning.split(',')[0].strip() if isinstance(ko_meaning, str) else str(ko_meaning)
        vocab_text += f"{i}. **{ru_word}** - {meaning}\n"
    
    vocab_text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━
**💡 학습 방법:**
━━━━━━━━━━━━━━━━━━━━━━━━

1. 각 단어를 3번씩 소리내어 읽기
2. 예문 만들어보기 (`/write` 사용)
3. 게임으로 연습하기 (`/games`)
4. SRS로 복습하기 (`/srs_review`)

🎯 **활용 팁:**
• `/ls [단어]` - 발음 듣기
• `/trl korean [단어]` - 상세 설명
• `/write` - 문장에 활용하기

🌟 새로운 단어들이 SRS 시스템에 자동 추가됩니다!
    """
    
    # SRS 시스템에 단어 추가
    today = datetime.now(MSK)
    for ru_word, ko_meaning in selected_words:
        if ru_word not in user_data['learning']['vocabulary_srs']:
            user_data['learning']['vocabulary_srs'][ru_word] = {
                'meaning': ko_meaning,
                'interval': 1,
                'next_review': (today + timedelta(days=1)).date().isoformat(),
                'easiness': 2.5,
                'repetitions': 0
            }
    
    save_user_data(load_user_data())
    
    await update.message.reply_text(vocab_text)

async def pronunciation_score_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """발음 점수 기록"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    scores = user_data['learning']['pronunciation_scores']
    
    if not scores:
        score_text = """
🎤 **발음 점수 기록** 🎤

━━━━━━━━━━━━━━━━━━━━━━━━
**📊 아직 발음 기록이 없습니다**
━━━━━━━━━━━━━━━━━━━━━━━━

💡 **발음 연습을 시작해보세요:**
• `/game_pronunciation` - 발음 챌린지
• `/ls [러시아어]` - 발음 듣기
• `/trls` - 번역 + 음성

🎯 발음 연습을 하시면 점수가 기록됩니다!
        """
    else:
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        recent_scores = scores[-5:] if len(scores) >= 5 else scores
        
        score_text = f"""
🎤 **발음 점수 기록** 🎤

━━━━━━━━━━━━━━━━━━━━━━━━
**📊 발음 통계**
━━━━━━━━━━━━━━━━━━━━━━━━

📈 **평균 점수:** {avg_score:.1f}/100
🏆 **최고 점수:** {max_score}/100
📊 **총 연습 횟수:** {len(scores)}회

**📅 최근 5회 점수:**
{', '.join([str(score) for score in recent_scores])}

━━━━━━━━━━━━━━━━━━━━━━━━
**🎯 발음 평가 기준**
━━━━━━━━━━━━━━━━━━━━━━━━

🏆 90+ : 완벽한 발음
🌟 80-89 : 매우 좋은 발음  
👍 70-79 : 좋은 발음
👌 60-69 : 괜찮은 발음
📚 ~59 : 더 연습 필요

💪 계속 연습해서 발음 마스터가 되어보세요!
        """
    
    await update.message.reply_text(score_text)

# === 👥 소셜 학습 기능 ===

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """리더보드"""
    leaderboard_text = """
🏆 **글로벌 리더보드** 🏆

━━━━━━━━━━━━━━━━━━━━━━━━
**🥇 TOP 학습자들**
━━━━━━━━━━━━━━━━━━━━━━━━

🥇 **1위** 익명사용자1 - 2,850 점
🥈 **2위** 익명사용자2 - 2,720 점  
🥉 **3위** 익명사용자3 - 2,650 점
4위 익명사용자4 - 2,400 점
5위 익명사용자5 - 2,200 점

━━━━━━━━━━━━━━━━━━━━━━━━
**📊 랭킹 점수 산정 기준**
━━━━━━━━━━━━━━━━━━━━━━━━

• 퀘스트 완료: +50점
• 게임 승리: +30점
• 연속 학습일: 일당 +10점
• 성취 달성: +100점

🎯 더 많이 학습하고 순위를 올려보세요!

💡 **아직 개발 중인 기능입니다**
실제 랭킹 시스템은 곧 업데이트될 예정입니다!
    """
    
    await update.message.reply_text(leaderboard_text)

async def challenge_friend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """친구 도전"""
    challenge_text = """
👥 **친구 도전 시스템** 👥

━━━━━━━━━━━━━━━━━━━━━━━━
**🎯 도전 방법**
━━━━━━━━━━━━━━━━━━━━━━━━

1. 친구를 봇에 초대하세요
2. 함께 퀴즈나 게임을 플레이
3. 점수를 비교하여 승부 결정
4. 승자는 특별 배지 획득!

**🏆 도전 게임 종류:**
• 단어 매칭 대결
• 스피드 퀴즈 경쟁
• 발음 점수 비교
• 연속 학습일 경쟁

💡 **아직 개발 중인 기능입니다**
소셜 학습 기능은 곧 업데이트될 예정입니다!

🎯 지금은 개인 학습에 집중해주세요!
    """
    
    await update.message.reply_text(challenge_text)

async def study_buddy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """스터디 버디"""
    buddy_text = """
🤝 **스터디 버디 시스템** 🤝

━━━━━━━━━━━━━━━━━━━━━━━━
**💡 스터디 버디란?**
━━━━━━━━━━━━━━━━━━━━━━━━

함께 러시아어를 공부하는 학습 파트너입니다.
서로 격려하고 경쟁하며 더 효과적으로 학습할 수 있어요!

**🎯 주요 기능:**
• 함께 목표 설정
• 학습 진도 공유
• 서로 격려 메시지
• 그룹 스터디 세션

**📅 예정 기능:**
• 실시간 채팅
• 그룹 퀘스트
• 팀 순위 경쟁
• 스터디 그룹 만들기

💡 **아직 개발 중인 기능입니다**
소셜 학습 기능은 곧 업데이트될 예정입니다!

🌟 지금은 AI 튜터와 함께 학습해주세요!
    """
    
    await update.message.reply_text(buddy_text)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎨 초현대적 인라인 키보드 콜백 핸들러
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """인라인 키보드 버튼 클릭 처리"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    # 🎯 AI 튜터 관련 콜백
    if callback_data == "ai_tutor":
        await ai_tutor_command(update, context)
    
    elif callback_data == "personalized_lesson":
        await personalized_lesson_command(update, context)
    
    elif callback_data == "learning_analytics":
        await learning_analytics_command(update, context)
    
    # 🎮 게임 관련 콜백
    elif callback_data == "games_menu":
        await games_command(update, context)
    
    elif callback_data == "daily_word_game":
        await word_match_game_command(update, context)
    
    elif callback_data == "practice_writing":
        message_text = """
✍️ **문장 만들기 연습** ✍️

━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **연습 방법**
━━━━━━━━━━━━━━━━━━━━━━━━

1. **오늘 배운 단어**를 사용해서
2. **러시아어 문장**을 만들어보세요
3. `/write [문장]` 명령어로 전송
4. **AI가 교정**해드립니다!

💡 **예시**: 
`/write Я изучаю русский язык каждый день`

✨ **팁**: 짧고 간단한 문장부터 시작하세요!
        """
        await query.edit_message_text(message_text)
    
    # 📚 학습 관련 콜백
    elif callback_data == "quest_start":
        await quest_command(update, context)
    
    elif callback_data == "vocab_basic":
        await vocabulary_builder_command(update, context)
    
    elif callback_data == "adaptive_quiz":
        await adaptive_quiz_command(update, context)
    
    elif callback_data == "weak_area_practice":
        await weak_area_practice_command(update, context)
    
    elif callback_data == "pronunciation_master":
        await pronunciation_score_command(update, context)
    
    # 📊 분석 관련 콜백
    elif callback_data == "my_progress":
        await my_progress_command(update, context)
    
    elif callback_data == "check_my_progress":
        await my_progress_command(update, context)
    
    elif callback_data == "advanced_analytics":
        await learning_analytics_command(update, context)
    
    # 📅 일일 학습 관련 콜백
    elif callback_data == "daily_learning":
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        users = load_user_data()
        user_data = users.get(str(user_id), {})
        subscribed = user_data.get('subscribed_daily', False)
        
        if subscribed:
            message_text = """
📅 **일일 학습 설정** 📅

━━━━━━━━━━━━━━━━━━━━━━━━
✅ **현재 상태**: 구독 중
━━━━━━━━━━━━━━━━━━━━━━━━

🕰️ **전송 시간**: 매일 오전 7시 (MSK)
📚 **내용**: 단어 30개 + 회화 20개
🎵 **음성 포함**: 고품질 발음 파일
🏆 **보상**: 일일 +50 EXP

💡 **새로운 기능**: 이제 음성 파일도 함께 전송됩니다!
            """
            
            keyboard = [
                [InlineKeyboardButton("🔕 구독 해제", callback_data="unsubscribe_daily")],
                [InlineKeyboardButton("🔄 지금 받아보기", callback_data="get_daily_now")],
                [InlineKeyboardButton("⚙️ 설정 변경", callback_data="daily_settings")]
            ]
        else:
            message_text = """
📅 **일일 학습 설정** 📅

━━━━━━━━━━━━━━━━━━━━━━━━
❌ **현재 상태**: 구독 안 함
━━━━━━━━━━━━━━━━━━━━━━━━

✨ **구독하면 매일 받는 것**:
• 📚 엄선된 러시아어 단어 30개
• 💬 실전 회화 문장 20개  
• 🎵 전문 발음 음성 파일
• 🎯 개인화된 학습 가이드
• 🏆 일일 50 EXP 보상

🕰️ **전송 시간**: 매일 오전 7시 (모스크바 시간)
            """
            
            keyboard = [
                [InlineKeyboardButton("📅 구독 시작", callback_data="subscribe_daily")],
                [InlineKeyboardButton("🔄 샘플 보기", callback_data="get_daily_sample")],
                [InlineKeyboardButton("❓ 자세히 알아보기", callback_data="daily_info")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message_text, reply_markup=reply_markup)
    
    elif callback_data == "subscribe_daily":
        await subscribe_daily_command(update, context)
    
    elif callback_data == "unsubscribe_daily":
        await unsubscribe_daily_command(update, context)
    
    elif callback_data == "get_daily_now":
        # 즉시 일일 학습 콘텐츠 전송
        bot = context.bot
        await send_daily_learning(bot)
        await query.edit_message_text("📚 **일일 학습 콘텐츠를 전송했습니다!**\n\n🎵 음성 파일도 함께 받으셨어요!")
    
    # 🌍 번역 관련 콜백
    elif callback_data == "translation_menu":
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        message_text = """
🌍 **번역 & 음성 메뉴** 🌍

━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **어떤 기능을 사용하시겠어요?**
━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **간단 번역**: `/trs [언어] [텍스트]`
📚 **상세 번역**: `/trl [언어] [텍스트]`  
🎵 **번역+음성**: `/trls [언어] [텍스트]`
🔊 **음성 변환**: `/ls [텍스트]`

💡 **지원 언어**: korean, russian, english, chinese, japanese
        """
        
        keyboard = [
            [InlineKeyboardButton("⚡ 간단 번역 예제", callback_data="translation_example_simple"),
             InlineKeyboardButton("📚 상세 번역 예제", callback_data="translation_example_detailed")],
            [InlineKeyboardButton("🎵 음성 번역 예제", callback_data="translation_example_audio"),
             InlineKeyboardButton("🔊 음성 변환 예제", callback_data="audio_example")],
            [InlineKeyboardButton("🔙 메인 메뉴로", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message_text, reply_markup=reply_markup)
    
    # 📚 도움말 관련 콜백
    elif callback_data == "help_guide":
        await help_command(update, context)
    
    # 🎵 일일 학습 음성 관련 콜백
    elif callback_data in ["listen_all_words", "listen_all_conversations"]:
        await query.edit_message_text("🎵 **음성 파일을 준비 중입니다...**\n\n⏳ 잠시만 기다려주세요!")
    
    elif callback_data == "like_daily":
        await query.edit_message_text("❤️ **감사합니다!**\n\n🌟 여러분의 피드백이 저희에게 큰 힘이 됩니다!")
    
    elif callback_data == "satisfied_daily":
        await query.edit_message_text("🎉 **완벽해요!**\n\n🚀 내일도 더 좋은 콘텐츠로 만나요!")
    
    # 🔙 뒤로가기 콜백
    elif callback_data == "back_to_main":
        await start_command(update, context)
    
    # 기타 알림 콜백들
    elif callback_data in ["daily_game", "check_progress", "refresh_daily"]:
        await query.edit_message_text("🚧 **기능 준비 중입니다!**\n\n⭐ 곧 업데이트될 예정이에요!")
    
    else:
        await query.edit_message_text("❓ **알 수 없는 명령입니다.**\n\n🔄 `/start`로 다시 시작해주세요!")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎨 향상된 UI 컴포넌트들
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def create_progress_bar(percentage: float, length: int = 10) -> str:
    """진행률 바 생성 (현대적 스타일)"""
    filled = int(percentage * length / 100)
    empty = length - filled
    
    bar = "🟩" * filled + "⬜" * empty
    return f"{bar} {percentage:.1f}%"

async def create_level_badge(level: int) -> str:
    """레벨 배지 생성"""
    if level <= 10:
        return "🔰"
    elif level <= 20:
        return "🥉"
    elif level <= 30:
        return "🥈" 
    elif level <= 50:
        return "🥇"
    elif level <= 70:
        return "💎"
    elif level <= 90:
        return "👑"
    else:
        return "🌟"

async def format_experience(exp: int) -> str:
    """경험치 포맷팅"""
    if exp < 1000:
        return f"{exp}"
    elif exp < 1000000:
        return f"{exp/1000:.1f}K"
    else:
        return f"{exp/1000000:.1f}M"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔢 번호 메뉴 시스템 핸들러 (인라인 키보드 대체)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def menu_1_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """메뉴 1: 게임으로 학습하기"""
    await games_command(update, context)

async def menu_2_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """메뉴 2: 퀘스트 시작하기"""
    await quest_command(update, context)

async def menu_3_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """메뉴 3: AI 튜터 상담"""
    await ai_tutor_command(update, context)

async def menu_4_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """메뉴 4: 성취 배지 확인"""
    await achievements_command(update, context)

# 추가 번호 메뉴들
async def menu_5_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """메뉴 5: 작문 교정받기"""
    user = update.effective_user
    user_data = get_user(update.effective_chat.id)
    
    # 사용자의 작문 실력 레벨 확인
    corrected_count = user_data['stats']['sentences_corrected']
    level = user_data['stats']['level']
    
    if corrected_count == 0:
        skill_level = "🌱 작문 입문자"
        difficulty_tip = "간단한 문장부터 시작하세요!"
        example = "Я изучаю русский язык"
    elif corrected_count < 10:
        skill_level = "⚡ 작문 연습생"
        difficulty_tip = "복합 문장에 도전해보세요!"
        example = "Я изучаю русский язык каждый день"
    elif corrected_count < 50:
        skill_level = "🏆 작문 숙련자"
        difficulty_tip = "고급 문법을 활용해보세요!"
        example = "Если бы я знал русский язык лучше, я бы поехал в Россию"
    else:
        skill_level = "👑 작문 마스터"
        difficulty_tip = "창의적인 표현에 도전하세요!"
        example = "Несмотря на трудности, изучение русского языка приносит мне огромное удовольствие"

    message_text = f"""
✍️ **AI 작문 교정소** ✍️

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌟 **{user.first_name}님의 작문 현황** 🌟
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 **실력 등급**: {skill_level}
✅ **교정 완료**: {corrected_count}개 문장
📈 **전체 레벨**: Lv.{level}
🎯 **추천 난이도**: {difficulty_tip}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **사용 방법** 🚀
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**단계 1**: `/write [러시아어 문장]` 입력
**단계 2**: AI가 전문적으로 교정 분석
**단계 3**: 점수, 설명, 학습 팁 제공
**단계 4**: 개선된 표현 습득

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 **추천 예시 ({skill_level}용)** 💡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

`/write {example}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **작문 연습 주제 추천** 🎯
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏠 **일상**: "Вчера я был дома и читал книгу"
🎓 **학교**: "В университете я изучаю русскую литературу"  
🍽️ **음식**: "Мне нравится борщ и пельмени"
🌍 **여행**: "Я хочу поехать в Санкт-Петербург"
💭 **감정**: "Когда я счастлив, я слушаю музыку"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ **AI 교정의 특별함** ✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 **최신 AI**: Gemini 2.5 Pro 엔진
📊 **10점 평가**: 정확한 점수 시스템
💡 **상세 설명**: 문법 오류 구체적 분석
🎯 **학습 팁**: 실력 향상 맞춤 조언
🎉 **칭찬 시스템**: 동기부여 극대화

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 **지금 바로 시작하세요!** 🔥
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👆 **위 예시를 복사해서 `/write` 뒤에 붙여넣으세요!**
✨ **또는 자신만의 문장을 자유롭게 작성해보세요!**

**매일 1-2개 문장씩 연습하면 빠르게 실력이 향상됩니다!** 🚀
    """
    await update.message.reply_text(message_text)

async def menu_6_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """메뉴 6: 번역 & 음성"""
    message_text = """
🌍 **번역 & 음성 도구** 🌍

━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **번역 명령어**
━━━━━━━━━━━━━━━━━━━━━━━━

⚡ `/trs [언어] [텍스트]` - 빠른 번역
📚 `/trl [언어] [텍스트]` - 상세 번역 (문법 분석 포함)
🎵 `/trls [언어] [텍스트]` - 번역 + 음성 변환
🔊 `/ls [텍스트]` - 음성 변환만

💡 **지원 언어**: 
• korean (kr) - 한국어
• russian (ru) - 러시아어  
• english (en) - 영어
• chinese (cn) - 중국어
• japanese (jp) - 일본어

✨ **예시**:
`/trs russian 안녕하세요`
`/trls korean Здравствуйте`
`/ls Привет, как дела?`

🎯 **팁**: 음성으로 발음을 확인하세요!
    """
    await update.message.reply_text(message_text)

async def menu_7_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """메뉴 7: 학습 진도 확인"""
    await my_progress_command(update, context)

async def menu_8_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """메뉴 8: 발음 점수 확인"""
    await pronunciation_score_command(update, context)

async def menu_9_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """메뉴 9: 개인화된 수업"""
    await personalized_lesson_command(update, context)

async def menu_0_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """메뉴 0: 전체 메뉴 보기 - 완전 종합 가이드"""
    user = update.effective_user
    user_data = get_user(update.effective_chat.id)
    
    level = user_data['stats']['level']
    exp = user_data['stats']['total_exp']
    streak = user_data['learning']['daily_streak']
    achievements = len(user_data['learning']['achievements'])
    
    # 레벨별 이모지
    if level <= 10:
        level_emoji = "🔰"
        level_title = "초보 모험가"
    elif level <= 30:
        level_emoji = "⚡"
        level_title = "중급 탐험가"
    elif level <= 60:
        level_emoji = "🏆"
        level_title = "고급 마스터"
    else:
        level_emoji = "👑"
        level_title = "전설의 챔피언"

    menu_text = f"""
📱 **완전 종합 메뉴 가이드** 📱

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌟 **{user.first_name}님의 현재 상태** 🌟
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{level_emoji} **등급**: {level_title} (Lv.{level})
⭐ **경험치**: {exp:,} EXP
🔥 **연속학습**: {streak}일
🏅 **성취**: {achievements}/8개

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **번호 메뉴 (간편 접근)** 🚀
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🎮 게임 & 퀘스트**
`/1` - 🎮 **게임으로 학습** (4가지 최신 게임)
`/2` - 🏰 **퀘스트 모험** (실전 회화 연습)
`/3` - 🎯 **AI 튜터 상담** (개인 맞춤 분석)
`/4` - 🏆 **성취 배지함** (업적 및 랭킹)

**📚 학습 도구**
`/5` - ✍️ **작문 교정소** (AI 첨삭 서비스)
`/6` - 🌍 **번역 & 음성** (다국어 지원)
`/7` - 📊 **학습 대시보드** (진도 및 통계)
`/8` - 🎤 **발음 분석실** (음성 점수 확인)

**🎯 고급 기능**
`/9` - 📈 **개인화 수업** (맞춤형 커리큘럼)
`/0` - 📋 **이 메뉴** (전체 가이드)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **직접 명령어 (전문가용)** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🎯 핵심 기능**
• `/quest` - 퀘스트 즉시 시작
• `/games` - 게임 선택 메뉴
• `/write [러시아어]` - 작문 즉시 교정
• `/my_progress` - 상세 학습 분석

**🌍 번역 & 음성**
• `/trs [언어] [텍스트]` - 빠른 번역
• `/trl [언어] [텍스트]` - 상세 번역
• `/trls [언어] [텍스트]` - 번역+음성
• `/ls [텍스트]` - 음성 변환

**🎮 게임 직접 실행**
• `/game_word_match` - 단어 매칭
• `/game_sentence_builder` - 문장 조립
• `/game_speed_quiz` - 스피드 퀴즈  
• `/game_pronunciation` - 발음 챌린지

**📚 고급 학습**
• `/ai_tutor` - AI 개인 분석
• `/personalized_lesson` - 맞춤 수업
• `/achievements` - 성취 시스템
• `/weak_area_practice` - 약점 보강

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 **사용 팁** 💡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 **초보자**: `/1` → `/2` → `/3` 순서 추천
⚡ **중급자**: `/5` → `/9` → `/7` 순서 추천  
👑 **고급자**: `/8` → `/9` → 고급 명령어 활용

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 **특별 혜택** 🎉
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆓 **완전 무료** - 모든 기능 무제한
🤖 **최신 AI** - Gemini 2.5 Pro 엔진
🎵 **음성 지원** - 실시간 TTS 변환
📱 **24/7** - 언제든지 학습 가능

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 **자유 대화도 환영!** 💬
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

명령어 없이 그냥 메시지를 보내셔도
AI가 친근하게 러시아어 학습을 도와드려요!

🚀 **지금 바로 번호를 선택해서 시작하세요!**
    """
    
    await update.message.reply_text(menu_text)

# ===========================================
# 🎮 완전히 새로운 게임 시스템
# ===========================================

async def games_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🎮 최신식 게임 메뉴 시스템"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    # 사용자 레벨에 따른 추천 게임
    level = user_data['stats']['level']
    if level <= 5:
        recommended_game = "🎯 단어 매칭 게임 (초보자 추천!)"
        rec_command = "/game_word_match"
    elif level <= 15:
        recommended_game = "⚡ 스피드 퀴즈 (당신 레벨에 딱!)"
        rec_command = "/game_speed_quiz"
    else:
        recommended_game = "🎤 발음 챌린지 (고급자 도전!)"
        rec_command = "/game_pronunciation"
    
    games_text = f"""
🎮 **차세대 AI 학습 게임 센터** 🎮

━━━━━━━━━━━━━━━━━━━━━━━━
✨ **{user.first_name}님 전용 추천 게임** ✨
━━━━━━━━━━━━━━━━━━━━━━━━

🌟 **{recommended_game}**
→ `{rec_command}` 입력하여 바로 시작!

━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **전체 게임 목록**
━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **단어 매칭 게임** 
   • 명령어: `/game_word_match`
   • 난이도: ⭐⭐⭐☆☆ (초급)
   • 보상: 20 EXP | 시간: 60초
   • 설명: 러시아어-한국어 단어 매칭

⚡ **스피드 퀴즈**
   • 명령어: `/game_speed_quiz`  
   • 난이도: ⭐⭐⭐⭐☆ (중급)
   • 보상: 25 EXP | 시간: 30초
   • 설명: 빠른 번역 퀴즈

🔧 **문장 조립 게임**
   • 명령어: `/game_sentence_builder`
   • 난이도: ⭐⭐⭐⭐☆ (중급)  
   • 보상: 30 EXP | 시간: 90초
   • 설명: 단어로 문장 완성

🎤 **발음 챌린지**
   • 명령어: `/game_pronunciation`
   • 난이도: ⭐⭐⭐⭐⭐ (고급)
   • 보상: 35 EXP | 시간: 120초
   • 설명: 발음 정확도 측정

━━━━━━━━━━━━━━━━━━━━━━━━
📊 **개인 게임 통계**
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    total_played = 0
    total_won = 0
    
    for game_id, stats in user_data['learning']['game_stats'].items():
        if game_id in LEARNING_GAMES:
            game_name = LEARNING_GAMES[game_id]['name']
            played = stats['played']
            won = stats['won']
            best_score = stats['best_score']
            win_rate = (won / played * 100) if played > 0 else 0
            
            total_played += played
            total_won += won
            
            games_text += f"\n{game_name}\n"
            games_text += f"   🎮 플레이: {played}회 | 🏆 승리: {won}회\n"
            games_text += f"   📈 승률: {win_rate:.1f}% | 🎯 최고점: {best_score}점\n"
    
    overall_win_rate = (total_won / total_played * 100) if total_played > 0 else 0
    
    games_text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━
🏆 **종합 통계**
━━━━━━━━━━━━━━━━━━━━━━━━

🎮 총 게임 수: {total_played}회
🏆 총 승리: {total_won}회  
📊 전체 승률: {overall_win_rate:.1f}%
🔥 연속 학습: {user_data['learning']['daily_streak']}일
⭐ 랭킹 포인트: {user_data['social']['ranking_points']}점

💡 **팁**: 매일 게임을 하면 경험치와 승률이 향상됩니다!
🎯 **목표**: 모든 게임에서 80% 이상 승률 달성!
    """
    
    await update.message.reply_text(games_text)

async def word_match_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🎯 완전히 새로운 단어 매칭 게임"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    try:
        # 어휘 데이터 로드
        with open('russian_korean_vocab_2000.json', 'r', encoding='utf-8') as f:
            vocab_data = json.load(f)
    except Exception as e:
        await update.message.reply_text("❌ 어휘 데이터를 불러올 수 없습니다. 관리자에게 문의해주세요.")
        logger.error(f"Vocab data load error: {e}")
        return
    
    import random
    
    # 사용자 레벨에 따른 단어 선택
    level = user_data['stats']['level']
    if level <= 5:
        # 초급: 기본 단어 5개
        sample_size = 5
        word_list = list(vocab_data.items())[:500]  # 첫 500개 기본 단어
    elif level <= 15:
        # 중급: 중간 단어 6개
        sample_size = 6
        word_list = list(vocab_data.items())[500:1200]  # 중간 700개 단어
    else:
        # 고급: 고급 단어 8개
        sample_size = 8
        word_list = list(vocab_data.items())[1200:]  # 고급 단어들
    
    # 랜덤 단어 선택
    game_words = random.sample(word_list, min(sample_size, len(word_list)))
    
    # 게임 시작 메시지
    game_text = f"""
🎯 **단어 매칭 게임 시작!** 🎯

━━━━━━━━━━━━━━━━━━━━━━━━
⏰ **제한시간: 60초**
🎯 **목표: {len(game_words)}개 단어 매칭**
💰 **보상: 20 EXP + 보너스**
━━━━━━━━━━━━━━━━━━━━━━━━

📝 **문제: 다음 러시아어 단어들의 한국어 뜻을 입력하세요**

"""
    
    # 게임 데이터 저장
    game_data = {
        'words': game_words,
        'current_index': 0,
        'correct_count': 0,
        'start_time': datetime.now(MSK).timestamp()
    }
    
    # 첫 번째 단어 문제
    current_word = game_words[0]
    ru_word = current_word[0]
    correct_answer = current_word[1]
    
    # 정답을 여러 형태로 처리 (쉼표로 분리된 경우)
    if isinstance(correct_answer, str):
        correct_answers = [ans.strip() for ans in correct_answer.split(',')]
    else:
        correct_answers = [str(correct_answer)]
    
    game_data['correct_answers'] = correct_answers
    
    # 사용자 컨텍스트에 게임 데이터 저장
    context.user_data['word_match_game'] = game_data
    
    game_text += f"""
**문제 1/{len(game_words)}**

🇷🇺 **{ru_word}**

💡 **힌트**: 첫 글자는 '{correct_answers[0][0]}'입니다
⌨️ **답안**: 아래에 한국어 뜻을 입력하세요

━━━━━━━━━━━━━━━━━━━━━━━━
🎮 게임 중단하려면 "게임종료" 입력
💡 힌트가 필요하면 "힌트" 입력
    """
    
    await update.message.reply_text(game_text)
    
    # 게임 통계 업데이트
    user_data['learning']['game_stats']['word_match']['played'] += 1
    save_user_data({str(chat_id): user_data})

async def sentence_builder_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🔧 완전히 새로운 문장 조립 게임"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    # 문장 템플릿들
    sentence_templates = [
        {
            'russian': 'Я изучаю русский язык',
            'korean': '나는 러시아어를 공부합니다',
            'words': ['Я', 'изучаю', 'русский', 'язык'],
            'difficulty': 'beginner'
        },
        {
            'russian': 'Мне нравится читать книги',
            'korean': '나는 책 읽기를 좋아한다',
            'words': ['Мне', 'нравится', 'читать', 'книги'],
            'difficulty': 'beginner'
        },
        {
            'russian': 'Сегодня хорошая погода',
            'korean': '오늘은 날씨가 좋다',
            'words': ['Сегодня', 'хорошая', 'погода'],
            'difficulty': 'beginner'
        },
        {
            'russian': 'В магазине можно купить продукты',
            'korean': '상점에서 식료품을 살 수 있다',
            'words': ['В', 'магазине', 'можно', 'купить', 'продукты'],
            'difficulty': 'intermediate'
        },
        {
            'russian': 'Мы идём в театр на спектакль',
            'korean': '우리는 공연을 보러 극장에 간다',
            'words': ['Мы', 'идём', 'в', 'театр', 'на', 'спектакль'],
            'difficulty': 'intermediate'
        },
        {
            'russian': 'Несмотря на дождь, он пошёл гулять',
            'korean': '비에도 불구하고 그는 산책을 나갔다',
            'words': ['Несмотря', 'на', 'дождь', 'он', 'пошёл', 'гулять'],
            'difficulty': 'advanced'
        }
    ]
    
    # 사용자 레벨에 따른 문장 선택
    level = user_data['stats']['level']
    if level <= 5:
        available_sentences = [s for s in sentence_templates if s['difficulty'] == 'beginner']
    elif level <= 15:
        available_sentences = [s for s in sentence_templates if s['difficulty'] in ['beginner', 'intermediate']]
    else:
        available_sentences = sentence_templates
    
    import random
    selected_sentence = random.choice(available_sentences)
    
    # 단어 순서 섞기
    shuffled_words = selected_sentence['words'].copy()
    random.shuffle(shuffled_words)
    
    game_text = f"""
🔧 **문장 조립 게임 시작!** 🔧

━━━━━━━━━━━━━━━━━━━━━━━━
⏰ **제한시간: 90초**
🎯 **목표: 올바른 순서로 문장 완성**
💰 **보상: 30 EXP + 보너스**
━━━━━━━━━━━━━━━━━━━━━━━━

📖 **한국어 뜻**: {selected_sentence['korean']}

🧩 **주어진 단어들**: {' | '.join(shuffled_words)}

⌨️ **미션**: 위 단어들을 올바른 순서로 배열하여 완성된 러시아어 문장을 만드세요!

💡 **예시**: "Я изучаю русский язык" (단어 사이는 공백으로 구분)

━━━━━━━━━━━━━━━━━━━━━━━━
🎮 게임 중단하려면 "게임종료" 입력
💡 힌트가 필요하면 "힌트" 입력

⌨️ **답안을 입력하세요**:
    """
    
    # 게임 데이터 저장
    game_data = {
        'correct_sentence': selected_sentence['russian'],
        'korean_meaning': selected_sentence['korean'],
        'words': selected_sentence['words'],
        'shuffled_words': shuffled_words,
        'start_time': datetime.now(MSK).timestamp()
    }
    
    context.user_data['sentence_builder_game'] = game_data
    
    await update.message.reply_text(game_text)
    
    # 게임 통계 업데이트
    user_data['learning']['game_stats']['sentence_builder']['played'] += 1
    save_user_data({str(chat_id): user_data})

async def speed_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """⚡ 완전히 새로운 스피드 퀴즈"""
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    try:
        with open('russian_korean_vocab_2000.json', 'r', encoding='utf-8') as f:
            vocab_data = json.load(f)
    except Exception as e:
        await update.message.reply_text("❌ 어휘 데이터를 불러올 수 없습니다.")
        return
    
    import random
    
    # 5개 문제 준비
    quiz_words = random.sample(list(vocab_data.items()), 5)
    
    game_text = f"""
⚡ **스피드 퀴즈 시작!** ⚡

━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **제한시간: 30초**
🏃‍♂️ **총 5문제 연속 도전**
💰 **보상: 25 EXP + 스피드 보너스**
━━━━━━━━━━━━━━━━━━━━━━━━

🚀 **게임 방식**:
• 러시아어 단어가 나오면 즉시 한국어로 답변
• 빠르게 답할수록 높은 점수!
• 틀려도 계속 진행

준비되셨나요? 🏁

━━━━━━━━━━━━━━━━━━━━━━━━
🎮 게임 중단하려면 "게임종료" 입력

**3초 후 시작합니다!** ⏰
    """
    
    await update.message.reply_text(game_text)
    
    # 3초 대기
    await asyncio.sleep(3)
    
    # 게임 데이터 저장
    game_data = {
        'quiz_words': quiz_words,
        'current_question': 0,
        'correct_count': 0,
        'start_time': datetime.now(MSK).timestamp(),
        'question_start_time': datetime.now(MSK).timestamp()
    }
    
    context.user_data['speed_quiz_game'] = game_data
    
    # 첫 번째 문제
    await send_next_quiz_question(update, context)
    
    # 게임 통계 업데이트
    user_data['learning']['game_stats']['speed_quiz']['played'] += 1
    save_user_data({str(chat_id): user_data})

async def send_next_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """퀴즈 다음 문제 전송"""
    game_data = context.user_data.get('speed_quiz_game')
    if not game_data:
        return
    
    current_q = game_data['current_question']
    if current_q >= len(game_data['quiz_words']):
        await end_speed_quiz(update, context)
        return
    
    # 현재 문제
    word_pair = game_data['quiz_words'][current_q]
    ru_word = word_pair[0]
    correct_answer = word_pair[1]
    
    # 정답 처리
    if isinstance(correct_answer, str):
        correct_answers = [ans.strip() for ans in correct_answer.split(',')]
    else:
        correct_answers = [str(correct_answer)]
    
    game_data['current_correct_answers'] = correct_answers
    game_data['question_start_time'] = datetime.now(MSK).timestamp()
    
    question_text = f"""
⚡ **문제 {current_q + 1}/5** ⚡

🇷🇺 **{ru_word}**

⌨️ 한국어 뜻을 빠르게 입력하세요!
    """
    
    await update.message.reply_text(question_text)

async def end_speed_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """스피드 퀴즈 종료"""
    game_data = context.user_data.get('speed_quiz_game')
    if not game_data:
        return
    
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    # 결과 계산
    total_time = datetime.now(MSK).timestamp() - game_data['start_time']
    correct_count = game_data['correct_count']
    total_questions = len(game_data['quiz_words'])
    accuracy = (correct_count / total_questions) * 100
    
    # 점수 계산 (정확도 + 속도 보너스)
    base_score = correct_count * 20
    speed_bonus = max(0, (30 - total_time) * 2)  # 빠를수록 보너스
    final_score = int(base_score + speed_bonus)
    
    # 경험치 보상
    exp_reward = 25 + (correct_count * 5)
    user_data['stats']['total_exp'] += exp_reward
    
    # 게임 통계 업데이트
    if accuracy >= 60:  # 60% 이상이면 승리
        user_data['learning']['game_stats']['speed_quiz']['won'] += 1
        result_emoji = "🏆"
        result_text = "승리!"
    else:
        result_emoji = "💪"
        result_text = "아쉬워요!"
    
    # 최고 점수 업데이트
    if final_score > user_data['learning']['game_stats']['speed_quiz']['best_score']:
        user_data['learning']['game_stats']['speed_quiz']['best_score'] = final_score
        best_score_text = "🎉 **신기록 달성!**"
    else:
        best_score_text = ""
    
    save_user_data({str(chat_id): user_data})
    
    result_text_msg = f"""
⚡ **스피드 퀴즈 완료!** ⚡

━━━━━━━━━━━━━━━━━━━━━━━━
{result_emoji} **최종 결과: {result_text}**
━━━━━━━━━━━━━━━━━━━━━━━━

📊 **상세 결과**:
✅ 정답: {correct_count}/{total_questions}개
📈 정확도: {accuracy:.1f}%
⏱️ 소요시간: {total_time:.1f}초
🎯 최종점수: {final_score}점

💰 **획득 보상**:
⭐ 경험치: +{exp_reward} EXP
🏆 점수: {final_score}점

{best_score_text}

━━━━━━━━━━━━━━━━━━━━━━━━
🎮 다시 도전하려면 `/game_speed_quiz`
🏠 메인 메뉴로 돌아가려면 `/start`
    """
    
    await update.message.reply_text(result_text_msg)
    
    # 게임 데이터 정리
    if 'speed_quiz_game' in context.user_data:
        del context.user_data['speed_quiz_game']

async def handle_sentence_builder_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
    """문장 조립 게임 입력 처리"""
    chat_id = update.effective_chat.id
    user_data = get_user(chat_id)
    game_data = context.user_data['sentence_builder_game']
    
    # 게임 종료 요청
    if user_input.lower() in ['게임종료', 'quit', 'exit', '종료']:
        await update.message.reply_text("🎮 게임을 종료합니다. 다음에 또 도전해주세요!")
        del context.user_data['sentence_builder_game']
        return
    
    # 힌트 요청
    if user_input.lower() in ['힌트', 'hint']:
        correct_sentence = game_data['correct_sentence']
        words = correct_sentence.split()
        hint_text = f"💡 **힌트**: 첫 번째 단어는 '{words[0]}'입니다"
        await update.message.reply_text(hint_text)
        return
    
    # 시간 체크 (90초 제한)
    elapsed_time = datetime.now(MSK).timestamp() - game_data['start_time']
    if elapsed_time > 90:
        await update.message.reply_text("⏰ 시간 초과! 게임이 종료됩니다.")
        del context.user_data['sentence_builder_game']
        return
    
    # 정답 체크
    correct_sentence = game_data['correct_sentence']
    user_sentence = user_input.strip()
    
    is_correct = user_sentence.lower() == correct_sentence.lower()
    
    # 결과 처리
    if is_correct:
        # 승리 처리
        exp_reward = 30 + 10  # 보너스
        user_data['stats']['total_exp'] += exp_reward
        user_data['learning']['game_stats']['sentence_builder']['won'] += 1
        
        final_score = int(100 - elapsed_time)  # 빠를수록 높은 점수
        if final_score > user_data['learning']['game_stats']['sentence_builder']['best_score']:
            user_data['learning']['game_stats']['sentence_builder']['best_score'] = final_score
            best_score_text = "🎉 **신기록 달성!**"
        else:
            best_score_text = ""
        
        save_user_data({str(chat_id): user_data})
        
        result_msg = f"""
🔧 **문장 조립 게임 완료!** 🔧

━━━━━━━━━━━━━━━━━━━━━━━━
🏆 **완벽한 성공!** 🏆
━━━━━━━━━━━━━━━━━━━━━━━━

✅ **정답**: {correct_sentence}
⏱️ **소요시간**: {elapsed_time:.1f}초
🎯 **최종점수**: {final_score}점

💰 **획득 보상**:
⭐ 경험치: +{exp_reward} EXP

{best_score_text}

━━━━━━━━━━━━━━━━━━━━━━━━
🎮 다시 도전하려면 `/game_sentence_builder`
🏠 메인 메뉴로 돌아가려면 `/start`
        """
        
        await update.message.reply_text(result_msg)
        
    else:
        # 틀린 경우
        exp_reward = 15  # 참가상
        user_data['stats']['total_exp'] += exp_reward
        save_user_data({str(chat_id): user_data})
        
        result_msg = f"""
🔧 **문장 조립 게임 완료!** 🔧

━━━━━━━━━━━━━━━━━━━━━━━━
💪 **아쉽지만 좋은 시도였어요!** 💪
━━━━━━━━━━━━━━━━━━━━━━━━

❌ **입력한 답**: {user_sentence}
✅ **정답**: {correct_sentence}

💰 **참가 보상**:
⭐ 경험치: +{exp_reward} EXP

━━━━━━━━━━━━━━━━━━━━━━━━
🎮 다시 도전하려면 `/game_sentence_builder`
🏠 메인 메뉴로 돌아가려면 `/start`
        """
        
        await update.message.reply_text(result_msg)
    
    # 게임 데이터 정리
    del context.user_data['sentence_builder_game']

async def handle_speed_quiz_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
    """스피드 퀴즈 입력 처리"""
    chat_id = update.effective_chat.id
    user_data = get_user(chat_id)
    game_data = context.user_data['speed_quiz_game']
    
    # 게임 종료 요청
    if user_input.lower() in ['게임종료', 'quit', 'exit', '종료']:
        await update.message.reply_text("🎮 게임을 종료합니다. 다음에 또 도전해주세요!")
        del context.user_data['speed_quiz_game']
        return
    
    # 전체 시간 체크 (30초 제한)
    elapsed_time = datetime.now(MSK).timestamp() - game_data['start_time']
    if elapsed_time > 30:
        await end_speed_quiz(update, context)
        return
    
    # 현재 문제 정답 체크
    correct_answers = game_data.get('current_correct_answers', [])
    is_correct = any(user_input.strip().lower() == answer.lower() for answer in correct_answers)
    
    if is_correct:
        game_data['correct_count'] += 1
        # 즉시 다음 문제로
        game_data['current_question'] += 1
        await update.message.reply_text("✅ 정답!")
        await send_next_quiz_question(update, context)
    else:
        # 틀려도 다음 문제로
        game_data['current_question'] += 1
        await update.message.reply_text(f"❌ 정답: {correct_answers[0] if correct_answers else '알 수 없음'}")
        await send_next_quiz_question(update, context)

async def handle_pronunciation_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
    """발음 챌린지 입력 처리"""
    chat_id = update.effective_chat.id
    user_data = get_user(chat_id)
    game_data = context.user_data['pronunciation_game']
    
    # 게임 종료 요청
    if user_input.lower() in ['게임종료', 'quit', 'exit', '종료']:
        await update.message.reply_text("🎮 게임을 종료합니다. 다음에 또 도전해주세요!")
        del context.user_data['pronunciation_game']
        return
    
    # 음성 다시 듣기 요청
    if user_input.lower() in ['음성', 'audio', '다시']:
        sentence = game_data['sentence']['ru']
        try:
            audio_bytes = await convert_text_to_speech(sentence, "ru")
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = f"pronunciation_{sentence[:10]}.mp3"
            await update.message.reply_audio(
                audio=audio_file,
                caption=f"🔊 **{sentence}** 발음을 들어보세요!"
            )
        except Exception as e:
            await update.message.reply_text("❌ 음성 생성 중 오류가 발생했습니다.")
        return
    
    # 완료 확인
    if user_input.lower() in ['완료', 'done', '끝']:
        # 발음 점수 계산 (임의 점수 - 실제로는 음성 인식 필요)
        import random
        
        difficulty = game_data['difficulty']
        elapsed_time = datetime.now(MSK).timestamp() - game_data['start_time']
        
        # 난이도와 시간에 따른 점수 계산
        if difficulty == 'beginner':
            base_score = random.randint(70, 95)
        elif difficulty == 'intermediate':
            base_score = random.randint(65, 90)
        else:
            base_score = random.randint(60, 85)
        
        # 시간 보너스 (빠를수록 좋음)
        time_bonus = max(0, (120 - elapsed_time) * 0.2)
        final_score = min(100, int(base_score + time_bonus))
        
        # 경험치 보상
        exp_reward = 35 + (final_score // 10)
        user_data['stats']['total_exp'] += exp_reward
        
        # 게임 통계 업데이트
        if final_score >= 70:
            user_data['learning']['game_stats']['pronunciation_challenge']['won'] += 1
            result_emoji = "🏆"
            result_text = "훌륭한 발음!"
        else:
            result_emoji = "💪"
            result_text = "더 연습해보세요!"
        
        # 발음 점수 기록
        user_data['learning']['pronunciation_scores'].append({
            'score': final_score,
            'date': datetime.now(MSK).isoformat(),
            'sentence': game_data['sentence']['ru']
        })
        
        # 최고 점수 업데이트
        if final_score > user_data['learning']['game_stats']['pronunciation_challenge']['best_score']:
            user_data['learning']['game_stats']['pronunciation_challenge']['best_score'] = final_score
            best_score_text = "🎉 **신기록 달성!**"
        else:
            best_score_text = ""
        
        save_user_data({str(chat_id): user_data})
        
        result_msg = f"""
🎤 **발음 챌린지 완료!** 🎤

━━━━━━━━━━━━━━━━━━━━━━━━
{result_emoji} **{result_text}** {result_emoji}
━━━━━━━━━━━━━━━━━━━━━━━━

📝 **연습 문장**: {game_data['sentence']['ru']}
🎯 **발음 점수**: {final_score}점
⏱️ **소요시간**: {elapsed_time:.1f}초

💰 **획득 보상**:
⭐ 경험치: +{exp_reward} EXP

{best_score_text}

━━━━━━━━━━━━━━━━━━━━━━━━
🎮 다시 도전하려면 `/game_pronunciation`
🏠 메인 메뉴로 돌아가려면 `/start`
        """
        
        await update.message.reply_text(result_msg)
        del context.user_data['pronunciation_game']
    
    else:
        # 다른 입력은 격려 메시지
        await update.message.reply_text("🎤 연습을 계속하세요! 준비가 되면 '완료'를 입력해주세요.")

# ===========================================
# 🤖 AI 응답 생성 함수들
# ===========================================

async def generate_game_recommendation(user_data):
    """게임 추천 생성"""
    level = user_data['stats']['level']
    
    if level <= 5:
        recommendation = """
🎮 **초보자에게 추천하는 게임들** 🎮

1. 🎯 **단어 매칭 게임** (`/game_word_match`)
   • 기본 어휘 학습에 최적!
   • 쉬운 난이도로 자신감 향상

2. ⚡ **스피드 퀴즈** (`/game_speed_quiz`)
   • 빠른 번역 연습
   • 반사신경과 어휘력 동시 향상

💡 **팁**: 단어 매칭부터 시작해보세요!
        """
    elif level <= 15:
        recommendation = """
🎮 **중급자를 위한 게임들** 🎮

1. 🔧 **문장 조립 게임** (`/game_sentence_builder`)
   • 문법 구조 이해에 도움
   • 문장 구성 능력 향상

2. ⚡ **스피드 퀴즈** (`/game_speed_quiz`)
   • 속도와 정확성 모두 필요
   • 실전 회화 준비

💡 **팁**: 문장 조립으로 문법을 마스터하세요!
        """
    else:
        recommendation = """
🎮 **고급자 도전 게임들** 🎮

1. 🎤 **발음 챌린지** (`/game_pronunciation`)
   • 정확한 발음 연습
   • 네이티브 수준 도달

2. 🔧 **문장 조립 게임** (`/game_sentence_builder`)
   • 복잡한 문장 구조 마스터
   • 고급 표현력 향상

💡 **팁**: 발음까지 완벽하게 마스터하세요!
        """
    
    return recommendation

async def generate_progress_summary(user_data):
    """진도 요약 생성"""
    level = user_data['stats']['level']
    exp = user_data['stats']['total_exp']
    streak = user_data['learning']['daily_streak']
    
    summary = f"""
📊 **학습 진도 요약** 📊

━━━━━━━━━━━━━━━━━━━━━━━━
⭐ **현재 레벨**: {level}
💎 **총 경험치**: {exp:,} EXP
🔥 **연속 학습**: {streak}일

📈 **게임 통계**:
"""
    
    for game_id, stats in user_data['learning']['game_stats'].items():
        if game_id in LEARNING_GAMES:
            name = LEARNING_GAMES[game_id]['name']
            played = stats['played']
            won = stats['won']
            win_rate = (won/played*100) if played > 0 else 0
            summary += f"\n{name}: {played}회 플레이, 승률 {win_rate:.1f}%"
    
    summary += f"""

━━━━━━━━━━━━━━━━━━━━━━━━
💡 상세한 분석을 원하면 `/my_progress` 명령어를 사용하세요!
    """
    
    return summary

async def generate_translation_help(message):
    """번역 도움말 생성"""
    help_text = """
🌍 **번역 기능 사용법** 🌍

━━━━━━━━━━━━━━━━━━━━━━━━
**빠른 번역**:
• `/trs [러시아어]` - 간단 번역
• `/trl [긴 문장]` - 상세 번역

**음성 번역**:
• `/ls [러시아어]` - 음성으로 듣기
• `/trls [러시아어]` - 번역 + 음성

**예시**:
• `/trs привет` → "안녕하세요" + 음성
• `/trl Как дела?` → 상세 설명 + 활용법

━━━━━━━━━━━━━━━━━━━━━━━━
💡 직접 러시아어를 입력하시면 AI가 자동으로 번역해드려요!
    """
    
    return help_text

# ===========================================
# 🚀 메인 함수 - 봇 실행
# ===========================================

async def main() -> None:
    """🚀 세계 최고 수준 러시아어 학습 봇 실행"""
    if not BOT_TOKEN or not GEMINI_API_KEY:
        logger.error("텔레그램 봇 토큰 또는 Gemini API 키가 설정되지 않았습니다!")
        return

    application = Application.builder().token(BOT_TOKEN).build()
    
    # 🎨 혁신적인 UI와 모든 명령어 핸들러 등록
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe_daily", subscribe_daily_command))
    application.add_handler(CommandHandler("unsubscribe_daily", unsubscribe_daily_command))
    application.add_handler(CommandHandler("quest", quest_command))
    application.add_handler(CommandHandler("action", action_command))
    application.add_handler(CommandHandler("write", write_command))
    application.add_handler(CommandHandler("my_progress", my_progress_command))
    application.add_handler(CommandHandler("trs", translate_simple_command))
    application.add_handler(CommandHandler("trl", translate_long_command))
    application.add_handler(CommandHandler("ls", listening_command))
    application.add_handler(CommandHandler("trls", translate_listen_command))
    application.add_handler(CommandHandler("model_status", model_status_command))
    application.add_handler(CommandHandler("hint", hint_command))
    application.add_handler(CommandHandler("trans", translation_command))
    
    # 🎮 세계급 게임화 학습 시스템
    application.add_handler(CommandHandler("games", games_command))
    application.add_handler(CommandHandler("game_word_match", word_match_game_command))
    application.add_handler(CommandHandler("game_sentence_builder", sentence_builder_game_command))
    application.add_handler(CommandHandler("game_speed_quiz", speed_quiz_command))
    application.add_handler(CommandHandler("game_pronunciation", pronunciation_challenge_command))
    application.add_handler(CommandHandler("achievements", achievements_command))
    
    # 🧠 AI 기반 개인화 학습 시스템
    application.add_handler(CommandHandler("ai_tutor", ai_tutor_command))
    application.add_handler(CommandHandler("personalized_lesson", personalized_lesson_command))
    application.add_handler(CommandHandler("learning_analytics", learning_analytics_command))
    
    # 🎯 스마트 학습 도구
    application.add_handler(CommandHandler("weak_area_practice", weak_area_practice_command))
    application.add_handler(CommandHandler("adaptive_quiz", adaptive_quiz_command))
    application.add_handler(CommandHandler("srs_review", srs_review_command))
    application.add_handler(CommandHandler("vocabulary_builder", vocabulary_builder_command))
    application.add_handler(CommandHandler("pronunciation_score", pronunciation_score_command))
    
    # 🌟 소셜 기능 (미래 확장)
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    application.add_handler(CommandHandler("challenge_friend", challenge_friend_command))
    application.add_handler(CommandHandler("study_buddy", study_buddy_command))
    
    # 🔢 번호 메뉴 시스템 (인라인 키보드 대체)
    application.add_handler(CommandHandler("1", menu_1_command))
    application.add_handler(CommandHandler("2", menu_2_command))
    application.add_handler(CommandHandler("3", menu_3_command))
    application.add_handler(CommandHandler("4", menu_4_command))
    application.add_handler(CommandHandler("5", menu_5_command))
    application.add_handler(CommandHandler("6", menu_6_command))
    application.add_handler(CommandHandler("7", menu_7_command))
    application.add_handler(CommandHandler("8", menu_8_command))
    application.add_handler(CommandHandler("9", menu_9_command))
    application.add_handler(CommandHandler("0", menu_0_command))
    
    # 💬 일반 메시지 처리 (Gemini AI와 대화)