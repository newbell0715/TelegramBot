import os
import logging
import json
import io
from datetime import datetime, timedelta
import pytz
from gtts import gTTS
from telegram import Update, Bot
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
            }
        }
        save_user_data(users)
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
    user = update.effective_user
    chat_id = user.id
    user_data = get_user(chat_id)
    
    await update.message.reply_text(
        f"🎉 안녕하세요, {user.first_name}님!\n"
        "저는 당신만의 러시아어 학습 트레이너, **'루샤(Rusya)'**입니다.\n\n"
        "단순 번역기를 넘어, 실제 상황처럼 대화하고, 작문을 교정하며, 꾸준히 학습할 수 있도록 제가 함께할게요!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**🚀 핵심 학습 기능**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎮 **퀘스트 학습** - 실전 상황에서 러시아어 회화 배우기\n"
        "   • `/quest` - 카페, 레스토랑 등 스토리 시뮬레이션 시작\n"
        "   • `/action [러시아어]` - 퀘스트에서 행동하기\n"
        "   • `/hint` - 퀘스트 힌트 받기\n"
        "   • `/trans` - 퀘스트 번역 도움\n\n"
        "✍️ **AI 작문 교정** - 문법과 표현을 정확하게 수정\n"
        "   • `/write [러시아어 문장]` - 상세 피드백과 교정\n\n"
        "🌍 **스마트 번역 시스템**\n"
        "   • `/trs [언어] [텍스트]` - 빠른 간단 번역\n"
        "   • `/trl [언어] [텍스트]` - 문법 분석 + 상세 설명\n"
        "   📝 지원언어: korean(kr), russian(ru), english(en)\n\n"
        "🎵 **음성 학습 도구**\n"
        "   • `/ls [텍스트]` - 고품질 음성 변환 (발음 연습)\n"
        "   • `/trls [언어] [텍스트]` - 번역 + 음성을 한번에\n\n"
        "📊 **학습 관리 & 통계**\n"
        "   • `/my_progress` - 레벨, 경험치, 상세 학습 통계\n"
        "   • 자동 레벨업 시스템 & 성취도 추적\n\n"
        "📅 **일일 학습 구독** (매일 오전 7시 발송)\n"
        "   • `/subscribe_daily` - 매일 새로운 단어 30개 + 회화 20개\n"
        "   • `/unsubscribe_daily` - 구독 해제\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**🔧 시스템 & 도움말**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "• `/help` - 전체 상세 사용법 안내\n"
        "• `/model_status` - AI 모델 상태 확인\n"
        "• **명령어 없이도 대화 가능** - 그냥 메시지 보내기만 해도 AI가 응답!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**💡 추천 학습 순서**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ `/quest` - 실전 회화로 시작\n"
        "2️⃣ `/write` - 작문으로 문법 익히기\n"
        "3️⃣ `/trl` - 상세 번역으로 이해 깊히기\n"
        "4️⃣ `/ls` - 음성으로 발음 연습\n"
        "5️⃣ `/subscribe_daily` - 꾸준한 학습 습관 만들기\n\n"
        "🎯 **목표**: 매일 조금씩, 꾸준히 러시아어 마스터하기!\n\n"
        f"현재 레벨: **{user_data['stats']['level']}** | "
        f"총 경험치: **{user_data['stats']['total_exp']}**\n\n"
        "지금 바로 `/quest`로 시작하거나 `/help`로 상세 안내를 확인해보세요! 🚀"
    )

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
    
    # 30개 단어 랜덤 선택
    vocabulary = random.sample(database['vocabulary'], min(30, len(database['vocabulary'])))
    
    # 회화 문장은 기존 데이터베이스에서 로드
    try:
        with open('russian_learning_database.json', 'r', encoding='utf-8') as f:
            old_database = json.load(f)
        conversations = random.sample(old_database['conversations'], min(20, len(old_database['conversations'])))
    except FileNotFoundError:
        # 기존 파일이 없으면 단어로 대체
        conversations = random.sample(database['vocabulary'], min(20, len(database['vocabulary'])))
    
    # 단어 메시지 생성
    words_message = "📚 **오늘의 러시아어 단어 (30개)**\n\n"
    for i, word in enumerate(vocabulary, 1):
        words_message += f"{i}. **{word['russian']}** [{word['pronunciation']}] - {word['korean']}\n"
    
    # 회화 메시지 생성
    conversations_message = "💬 **오늘의 러시아어 회화 (20개)**\n\n"
    for i, conv in enumerate(conversations, 1):
        conversations_message += f"{i}. **{conv['russian']}**\n"
        conversations_message += f"   [{conv['pronunciation']}]\n"
        conversations_message += f"   💡 {conv['korean']}\n\n"
    
    # 긴 메시지 나누기
    words_parts = await split_long_message(words_message)
    conversations_parts = await split_long_message(conversations_message)
    
    for user_id, user_data in users.items():
        if user_data.get('subscribed_daily', False):
            try:
                # 헤더 메시지
                header = f"☀️ **오늘의 러시아어 학습** (모스크바 기준 {datetime.now(MSK).strftime('%m월 %d일')})\n\n"
                await bot.send_message(chat_id=user_id, text=header)
                
                # 단어 메시지 전송
                for part in words_parts:
                    await bot.send_message(chat_id=user_id, text=part)
                    await asyncio.sleep(0.5)  # 메시지 간 간격
                
                # 회화 메시지 전송
                for part in conversations_parts:
                    await bot.send_message(chat_id=user_id, text=part)
                    await asyncio.sleep(0.5)
                
                user_data['stats']['daily_words_received'] += 1
                logger.info(f"Sent daily learning to {user_id}")
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
    
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

# --- 봇 실행 ---
async def main() -> None:
    if not BOT_TOKEN or not GEMINI_API_KEY:
        logger.error("텔레그램 봇 토큰 또는 Gemini API 키가 설정되지 않았습니다!")
        return

    application = Application.builder().token(BOT_TOKEN).build()
    
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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    scheduler = AsyncIOScheduler(timezone=MSK)
    scheduler.add_job(send_daily_learning, 'cron', hour=7, minute=0, args=[application.bot])
    scheduler.add_job(send_daily_learning, 'cron', hour=12, minute=0, args=[application.bot])
    
    logger.info("🤖 튜터 봇 '루샤'가 활동을 시작합니다...")
    
    try:
        scheduler.start()
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        while True:
            await asyncio.sleep(3600)

    except (KeyboardInterrupt, SystemExit):
        logger.info("봇과 스케줄러를 종료합니다.")
        scheduler.shutdown()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main()) 