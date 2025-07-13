from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from services.gemini_service import call_gemini
from utils.data_utils import get_user, load_user_data, save_user_data

async def write_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """AI 작문 교정 명령어"""
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
    """학습 진행률 확인"""
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

async def subscribe_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """매일 학습 콘텐츠 구독"""
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
    """매일 학습 콘텐츠 구독 취소"""
    chat_id = update.effective_chat.id
    users = load_user_data()
    user = get_user(chat_id)

    if user['subscribed_daily']:
        users[str(chat_id)]['subscribed_daily'] = False
        save_user_data(users)
        await update.message.reply_text("✅ 구독 취소 완료! 아쉽지만, 언제든 다시 돌아와주세요.")
    else:
        await update.message.reply_text("현재 구독 중이 아닙니다.") 