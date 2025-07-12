import os
import logging
import asyncio
from datetime import datetime
from telegram.ext import Application, CommandHandler

# --- 로깅 설정 ---
from config.settings import BOT_TOKEN, GEMINI_API_KEY, MSK

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

# --- 핸들러 import ---
from handlers.basic import start_command, help_command
from handlers.translation import (
    translate_simple_command, 
    translate_long_command, 
    listening_command, 
    translate_listen_command
)
from handlers.quest import quest_command, action_command
from handlers.learning import (
    write_command, 
    my_progress_command, 
    subscribe_daily_command, 
    unsubscribe_daily_command
)

# --- 서비스 import ---
from services.scheduler_service import create_scheduler

async def main() -> None:
    """메인 실행 함수"""
    if not BOT_TOKEN or not GEMINI_API_KEY:
        logger.error("텔레그램 봇 토큰 또는 Gemini API 키가 설정되지 않았습니다!")
        return

    # 애플리케이션 생성
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 기본 명령어 핸들러 등록
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # 번역 & TTS 핸들러 등록
    application.add_handler(CommandHandler("trs", translate_simple_command))
    application.add_handler(CommandHandler("trl", translate_long_command))
    application.add_handler(CommandHandler("ls", listening_command))
    application.add_handler(CommandHandler("trls", translate_listen_command))
    
    # 퀘스트 핸들러 등록
    application.add_handler(CommandHandler("quest", quest_command))
    application.add_handler(CommandHandler("action", action_command))
    
    # 학습 핸들러 등록
    application.add_handler(CommandHandler("write", write_command))
    application.add_handler(CommandHandler("my_progress", my_progress_command))
    application.add_handler(CommandHandler("subscribe_daily", subscribe_daily_command))
    application.add_handler(CommandHandler("unsubscribe_daily", unsubscribe_daily_command))
    
    # 스케줄러 생성 및 시작
    scheduler = create_scheduler(application.bot)
    
    logger.info("🤖 튜터 봇 '루샤'가 활동을 시작합니다...")
    
    try:
        # 스케줄러와 봇을 동시에 실행
        scheduler.start()
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # 봇이 중지될 때까지 계속 실행
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