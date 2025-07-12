import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from config.settings import MSK
from services.gemini_service import call_gemini
from utils.data_utils import load_user_data, save_user_data

logger = logging.getLogger(__name__)

async def send_daily_learning(bot: Bot):
    """매일 학습 콘텐츠를 구독자들에게 전송"""
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
                
                user_data['stats']['daily_words_received'] += 1
                logger.info(f"Sent daily learning to {user_id}")
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
    
    save_user_data(users)

def create_scheduler(bot: Bot) -> AsyncIOScheduler:
    """스케줄러를 생성하고 설정"""
    scheduler = AsyncIOScheduler(timezone=MSK)
    scheduler.add_job(send_daily_learning, 'cron', hour=6, minute=0, args=[bot])
    return scheduler 