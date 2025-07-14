import logging
import json
import random
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from config.settings import MSK
from utils.data_utils import load_user_data, save_user_data

logger = logging.getLogger(__name__)

def load_learning_database():
    """러시아어 학습 데이터베이스 로드"""
    try:
        with open('russian_learning_database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("russian_learning_database.json 파일을 찾을 수 없습니다!")
        return {"vocabulary": [], "conversations": []}

async def send_daily_learning(bot: Bot):
    """매일 학습 콘텐츠를 구독자들에게 전송"""
    users = load_user_data()
    database = load_learning_database()
    
    # 데이터베이스에서 랜덤 선택
    vocabulary = database.get("vocabulary", [])
    conversations = database.get("conversations", [])
    
    if len(vocabulary) < 30 or len(conversations) < 20:
        logger.warning("데이터베이스에 충분한 데이터가 없습니다!")
        return
    
    # 랜덤 선택 (중복 방지)
    selected_words = random.sample(vocabulary, min(30, len(vocabulary)))
    selected_conversations = random.sample(conversations, min(20, len(conversations)))
    
    # 메시지 형식 생성
    words_text = "**📚 오늘의 단어 (30개):**\n"
    for i, word in enumerate(selected_words, 1):
        words_text += f"{i}. **{word['russian']}** 🔊`{word['pronunciation']}` - {word['korean']}\n"
    
    conversations_text = "\n**💬 오늘의 회화 (20개):**\n"
    for i, conv in enumerate(selected_conversations, 1):
        conversations_text += f"{i}. **{conv['russian']}** - {conv['korean']}\n"
        conversations_text += f"   🔊 발음: `{conv['pronunciation']}`\n"
    
    learning_content = words_text + conversations_text
    
    for user_id, user_data in users.items():
        if user_data.get('subscribed_daily', False):
            try:
                message = f"**☀️ 오늘의 러시아어 학습 (모스크바 기준 {datetime.now(MSK).strftime('%m월 %d일')})**\n\n{learning_content}"
                
                # 메시지가 너무 길면 분할 전송
                if len(message) > 4000:
                    # 단어 부분만 먼저 전송
                    words_message = f"**☀️ 오늘의 러시아어 학습 (모스크바 기준 {datetime.now(MSK).strftime('%m월 %d일')})**\n\n{words_text}"
                    await bot.send_message(chat_id=user_id, text=words_message)
                    
                    # 회화 부분을 따로 전송
                    conversations_message = f"**💬 오늘의 회화 (계속)**\n{conversations_text}"
                    await bot.send_message(chat_id=user_id, text=conversations_message)
                else:
                    await bot.send_message(chat_id=user_id, text=message)
                
                user_data['stats']['daily_words_received'] += 1
                logger.info(f"Sent daily learning to {user_id}")
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
    
    save_user_data(users)

def create_scheduler(bot: Bot) -> AsyncIOScheduler:
    """스케줄러를 생성하고 설정"""
    scheduler = AsyncIOScheduler(timezone=MSK)
    scheduler.add_job(send_daily_learning, 'cron', hour=7, minute=0, args=[bot])
    scheduler.add_job(send_daily_learning, 'cron', hour=12, minute=0, args=[bot])
    return scheduler 