import os
import logging
import json
import io
from datetime import datetime, timedelta
import pytz
from gtts import gTTS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
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
            'plan': 'Pro',
            'subscribed_daily': False,
            'quest_state': {'current_quest': None, 'stage': 0},
            'stats': {
                'start_date': datetime.now(MSK).isoformat(),
                'last_active_date': datetime.now(MSK).isoformat(),
                'quests_completed': 0,
                'sentences_corrected': 0,
                'daily_words_received': 0
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
    get_user(chat_id)
    
    await update.message.reply_text(
        f"🎉 안녕하세요, {user.first_name}님!\n"
        "저는 당신만의 러시아어 학습 트레이너, '루샤(Rusya)'입니다.\n\n"
        "단순 번역기를 넘어, 실제 상황처럼 대화하고, 작문을 교정하며, 꾸준히 학습할 수 있도록 제가 함께할게요!\n\n"
        "**주요 기능:**\n"
        "🇷🇺 `/quest` - 스토리 기반 퀘스트로 실전 회화 배우기\n"
        "✍️ `/write [문장]` - AI가 직접 러시아어 작문을 교정\n"
        "📈 `/my_progress` - 나의 주간 학습 성과 확인하기\n"
        "🔔 `/subscribe_daily` - 매일 아침 학습 콘텐츠 받아보기\n\n"
        "자, 이제 저와 함께 러시아어 정복을 시작해볼까요?\n"
        "먼저 `/quest`를 입력해서 첫 번째 임무를 시작해보세요!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
    🤖 **'루샤' 봇 사용법 안내** 🤖

    **🇷🇺 핵심 학습 기능**
    - `/quest` - 스토리 기반 퀘스트를 시작하거나 현재 상태를 봅니다.
    - `/action [문장]` - 퀘스트 진행을 위해 행동(대답)을 입력합니다.
    - `/write [러시아어 문장]` - AI가 문법과 표현을 교정해줍니다.
    - `/my_progress` - 주간 학습 통계를 확인하고 피드백을 받습니다.

    **🔔 구독 및 알림**
    - `/subscribe_daily` - 매일 아침 학습 콘텐츠 구독을 시작합니다.
    - `/unsubscribe_daily` - 매일 학습 콘텐츠 구독을 중지합니다.

    **⚙️ 기타 명령어**
    - `/start` - 봇 시작 및 초기화
    - `/help` - 이 도움말을 다시 봅니다.
    
    **💡 팁:**
    퀘스트가 막히면 `/quest`를 다시 입력해 현재 상황 설명을 다시 확인해보세요!
    """
    await update.message.reply_text(help_text)

async def subscribe_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    users = load_user_data()
    user = get_user(chat_id)
    
    if user['plan'] == 'Free':
        await update.message.reply_text("✨ '매일 학습' 기능은 Pro 플랜 전용입니다. `/my_plan`으로 플랜을 업그레이드해주세요!")
        return

    if not user['subscribed_daily']:
        users[str(chat_id)]['subscribed_daily'] = True
        save_user_data(users)
        await update.message.reply_text("✅ 구독 완료! 내일부터 매일 아침 7시(모스크바 기준)에 학습 콘텐츠를 보내드릴게요. 기대해주세요!")
    else:
        await update.message.reply_text("이미 구독 중이십니다! 매일 아침을 기다려주세요. 😊")

async def unsubscribe_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    users = load_user_data()
    user = get_user(chat_id)

    if user['subscribed_daily']:
        users[str(chat_id)]['subscribed_daily'] = False
        save_user_data(users)
        await update.message.reply_text("✅ 구독 취소 완료! 아쉽지만, 언제든 다시 돌아와주세요.")
    else:
        await update.message.reply_text("현재 구독 중이 아닙니다.")

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
            f"{stage_data['description']}\n\n"
            f"**상황:**\n`{stage_data['bot_message']}`\n\n"
            f"➡️ **당신의 행동:**\n{stage_data['action_prompt']}\n"
            f"명령어 `/action [할 말]`을 사용해 대답해주세요."
        )
    else:
        quest_id = quest_state['current_quest']
        stage = quest_state['stage']
        quest = QUEST_DATA[quest_id]
        
        if stage > len(quest['stages']):
            await update.message.reply_text("이미 모든 퀘스트를 완료하셨습니다! 다음 업데이트를 기대해주세요.")
            return

        stage_data = quest['stages'][stage]
        await update.message.reply_text(
            f"**📜 퀘스트 진행 중: {quest['title']} (단계: {stage})**\n\n"
            f"{stage_data['description']}\n\n"
            f"**상황:**\n`{stage_data['bot_message']}`\n\n"
            f"➡️ **당신의 행동:**\n{stage_data['action_prompt']}\n"
            f"명령어 `/action [할 말]`을 사용해 대답해주세요."
        )

async def action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = " ".join(context.args)
    
    if not user_text:
        await update.message.reply_text("실행할 행동을 입력해주세요. 예: `/action 안녕하세요`")
        return

    users = load_user_data()
    user = users[str(chat_id)]
    quest_state = user['quest_state']

    if quest_state['current_quest'] is None:
        await update.message.reply_text("진행 중인 퀘스트가 없습니다. `/quest`로 새 퀘스트를 시작하세요.")
        return

    quest_id = quest_state['current_quest']
    stage = quest_state['stage']
    quest = QUEST_DATA[quest_id]
    stage_data = quest['stages'][stage]

    if any(keyword in user_text.lower() for keyword in stage_data['keywords']):
        next_stage = stage + 1
        if next_stage > len(quest['stages']):
            user['quest_state'] = {'current_quest': None, 'stage': 0}
            user['stats']['quests_completed'] += 1
            save_user_data(users)
            await update.message.reply_text(f"🎉 **퀘스트 완료: {quest['title']}** 🎉\n\n축하합니다! 실전 러시아어 경험치가 1 상승했습니다. `/quest`로 다음 퀘스트에 도전하세요!")
        else:
            user['quest_state']['stage'] = next_stage
            save_user_data(users)
            
            next_stage_data = quest['stages'][next_stage]
            await update.message.reply_text(
                f"**✅ 단계 성공!**\n\n"
                f"**📜 다음 단계: {quest['title']} (단계: {next_stage})**\n\n"
                f"{next_stage_data['description']}\n\n"
                f"**상황:**\n`{next_stage_data['bot_message']}`\n\n"
                f"➡️ **당신의 행동:**\n{next_stage_data['action_prompt']}"
            )
    else:
        await update.message.reply_text(f"음... 조금 다른 표현이 필요할 것 같아요. 다시 시도해볼까요?\n\n**힌트:** {stage_data['action_prompt']}")

async def write_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = " ".join(context.args)

    if not user_text:
        await update.message.reply_text("사용법: `/write [교정받고 싶은 러시아어 문장]`")
        return

    user = get_user(chat_id)
    if user['plan'] == 'Free' and user['stats']['sentences_corrected'] >= 5:
        await update.message.reply_text("오늘의 무료 작문 교정 횟수를 모두 사용하셨습니다. Pro 플랜으로 업그레이드하시면 무제한으로 사용 가능합니다!")
        return

    processing_message = await update.message.reply_text("✍️ AI가 문장을 교정하고 있습니다. 잠시만 기다려주세요...")

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
    """
    
    corrected_text = await call_gemini(prompt)
    
    await processing_message.delete()
    await update.message.reply_text(corrected_text)

    users = load_user_data()
    users[str(chat_id)]['stats']['sentences_corrected'] += 1
    save_user_data(users)

async def my_progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_data = get_user(chat_id)
    stats = user_data['stats']

    start_date = datetime.fromisoformat(stats['start_date'])
    
    progress_report = f"""
    📊 **{update.effective_user.first_name}님의 성장 일기** 📊

    - **학습 시작일:** {start_date.strftime('%Y년 %m월 %d일')}
    - **현재 플랜:** {user_data['plan']}

    ---
    **이번 주 학습 활동 요약 (전체 기간):**
    
    - ✅ **완료한 퀘스트:** {stats['quests_completed']}개
    - ✍️ **AI 작문 교정:** {stats['sentences_corrected']}회
    - 📚 **일일 학습 자료 수신:** {stats['daily_words_received']}회

    ---

    **💡 루샤의 피드백:**
    정말 꾸준히 잘하고 계세요! 특히 작문 연습을 많이 하신 점이 인상 깊네요. 
    자신있게 문장을 만들어보는 습관이 언어 실력 향상의 지름길입니다.
    다음 주에는 새로운 퀘스트에 도전해보는 건 어떨까요? 파이팅!
    """
    await update.message.reply_text(progress_report)

async def translate_simple_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """간단한 번역 명령어 (/trs)"""
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "사용법: /trs [언어] [텍스트]\n\n"
                "💡 예시:\n"
                "- /trs english 안녕하세요 (또는 /trs en)\n"
                "- /trs russian 좋은 아침이에요 (또는 /trs ru)\n"
                "- /trs korean 감사합니다 (또는 /trs kr)\n\n"
                "⚡ 간단 번역: 최고의 번역만 간략하게 제공\n\n"
                "🌍 지원 언어:\n"
                "- english (en), russian (ru), korean (kr)"
            )
            return
        
        target_language = args[0]
        text_to_translate = " ".join(args[1:])
        
        # "처리 중..." 메시지 표시
        processing_message = await update.message.reply_text("⚡ 간단 번역 중...")
        
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
        full_response = f"⚡ 간단 번역 ({korean_language}):\n{clean_translation}"
        await update.message.reply_text(full_response)
                
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
    
    scheduler = AsyncIOScheduler(timezone=MSK)
    scheduler.add_job(send_daily_learning, 'cron', hour=7, minute=0, args=[application.bot])
    
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