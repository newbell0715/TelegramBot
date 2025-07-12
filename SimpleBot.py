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
GEMINI_API_KEY = "AIzaSyCmH1flv0HSRp8xYa1Y8oL7xnpyyQVuIw8" # 본인의 Gemini API 키
BOT_TOKEN = "8064422632:AAFkFqQDA_35OCa5-BFxeHPA9_hil4cY8Rg" # 본인의 텔레그램 봇 토큰

# --- Gemini AI 설정 ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

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
            'plan': 'Pro',  # 새 사용자는 Pro 플랜으로 시작
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
    # 사용자가 활동할 때마다 마지막 활동일 업데이트
    users[user_id]['stats']['last_active_date'] = datetime.now(MSK).isoformat()
    save_user_data(users)
    return users[user_id]

# --- AI 기능 헬퍼 ---
async def call_gemini(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API 오류: {e}")
        return "죄송합니다. AI 모델과 통신 중 오류가 발생했습니다. 😅"

# --- 핵심 기능: 명령어 핸들러 ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = user.id
    get_user(chat_id) # 사용자 데이터 생성 또는 로드
    
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
        await update.message.reply_text("✅ 구독 완료! 내일부터 매일 아침 6시(모스크바 기준)에 학습 콘텐츠를 보내드릴게요. 기대해주세요!")
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
        quest_id = 'q1' # 첫 퀘스트
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

    # 키워드 기반으로 성공 여부 판단 (간단한 방식)
    if any(keyword in user_text.lower() for keyword in stage_data['keywords']):
        # 성공
        next_stage = stage + 1
        if next_stage > len(quest['stages']):
            # 퀘스트 완료
            user['quest_state'] = {'current_quest': None, 'stage': 0}
            user['stats']['quests_completed'] += 1
            save_user_data(users)
            await update.message.reply_text(f"🎉 **퀘스트 완료: {quest['title']}** 🎉\n\n축하합니다! 실전 러시아어 경험치가 1 상승했습니다. `/quest`로 다음 퀘스트에 도전하세요!")
        else:
            # 다음 단계로
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
        # 실패
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

    # 통계 업데이트
    users = load_user_data()
    users[str(chat_id)]['stats']['sentences_corrected'] += 1
    save_user_data(users)

async def my_progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_data = get_user(chat_id)
    stats = user_data['stats']

    start_date = datetime.fromisoformat(stats['start_date'])
    today = datetime.now(MSK)
    
    # 주간 데이터 계산
    last_week = today - timedelta(days=7)
    # 실제 구현에서는 주간 활동을 별도로 기록해야 하지만, 여기서는 전체 통계를 보여줌
    
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

async def send_daily_learning(bot: Bot):
    users = load_user_data()
    
    prompt = """
    러시아어 초급자를 위한 '오늘의 학습' 콘텐츠를 생성해줘. 아래 형식에 맞춰서:

    **단어 (3개):**
    1. [러시아어 단어] [한글 발음] - [뜻]
    2. [러시아어 단어] [한글 발음] - [뜻]
    3. [러시아어 단어] [한글 발음] - [뜻]

    **회화 (2개):**
    1. [러시아어 문장] - [뜻]
       [한글 발음]
    2. [러시아어 문장] - [뜻]
       [한글 발음]
    """
    
    learning_content = await call_gemini(prompt)
    
    for user_id, user_data in users.items():
        if user_data.get('subscribed_daily', False):
            try:
                message = f"**☀️ 오늘의 러시아어 학습 (모스크바 기준 {datetime.now(MSK).strftime('%m월 %d일')})**\n\n{learning_content}"
                await bot.send_message(chat_id=user_id, text=message)
                
                # 통계 업데이트
                user_data['stats']['daily_words_received'] += 1
                logger.info(f"Sent daily learning to {user_id}")
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
    
    save_user_data(users)


async def post_init(application: Application) -> None:
    """애플리케이션 초기화 후 스케줄러를 시작합니다."""
    scheduler = AsyncIOScheduler(timezone=MSK)
    scheduler.add_job(send_daily_learning, 'cron', hour=6, minute=0, args=[application.bot])
    scheduler.start()
    # 애플리케이션 컨텍스트에 스케줄러 저장 (선택 사항)
    application.bot_data["scheduler"] = scheduler
    logger.info("APScheduler가 성공적으로 시작되었습니다.")


# --- 봇 실행 ---
async def main() -> None:
    """봇을 설정하고 비동기적으로 실행합니다."""
    if not BOT_TOKEN or not GEMINI_API_KEY:
        logger.error("텔레그램 봇 토큰 또는 Gemini API 키가 설정되지 않았습니다!")
        return

    # 애플리케이션 생성
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # 명령어 핸들러 등록
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe_daily", subscribe_daily_command))
    application.add_handler(CommandHandler("unsubscribe_daily", unsubscribe_daily_command))
    application.add_handler(CommandHandler("quest", quest_command))
    application.add_handler(CommandHandler("action", action_command))
    application.add_handler(CommandHandler("write", write_command))
    application.add_handler(CommandHandler("my_progress", my_progress_command))
    
    # 일반 메시지 처리 (향후 기능 확장용)
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 튜터 봇 '루샤'가 활동을 시작합니다...")
    
    try:
        # 스케줄러와 봇을 동시에 실행
        scheduler = application.bot_data["scheduler"] # post_init에서 저장한 스케줄러
        scheduler.start()
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # 봇이 중지될 때까지 계속 실행
        while True:
            await asyncio.sleep(3600) # 1시간마다 체크 (또는 다른 시간)

    except (KeyboardInterrupt, SystemExit):
        logger.info("봇과 스케줄러를 종료합니다.")
        scheduler.shutdown() # 스케줄러 종료
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main()) 