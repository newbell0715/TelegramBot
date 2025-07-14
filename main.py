import os
import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config.settings import BOT_TOKEN, MSK
from utils.data_utils import UserManager
import pytz

# --- 로깅 설정 (러시아 모스크바 시간대) ---
class MSKFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        from datetime import datetime
        dt = datetime.fromtimestamp(record.created, MSK)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
for handler in logging.root.handlers:
    handler.setFormatter(MSKFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# 콜백 핸들러 제거됨 - 이제 명령어만 사용

def main():
    """메인 실행 함수 - 강력한 충돌 방지"""
    
    logger.info("🚀 봇 시작 - 충돌 방지 모드")
    
    # pending updates 완전 클리어
    import requests
    clear_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1"
    try:
        response = requests.get(clear_url)
        logger.info(f"📋 pending updates 클리어: {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️ pending updates 클리어 실패: {e}")
    
    # 기존 webhook 삭제
    try:
        delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
        response = requests.get(delete_url)
        logger.info(f"🗑️ webhook 삭제: {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️ webhook 삭제 실패: {e}")
    
    import SimpleBot
    
    # 애플리케이션 생성
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 콜백 핸들러 제거됨 - 이제 명령어만 사용
    
    # === 기본 명령어 핸들러들 ===
    application.add_handler(CommandHandler("start", SimpleBot.start_command))
    application.add_handler(CommandHandler("help", SimpleBot.help_command))
    
    # === 학습 관련 핸들러들 ===
    application.add_handler(CommandHandler("quest", SimpleBot.quest_command))
    application.add_handler(CommandHandler("action", SimpleBot.action_command))
    application.add_handler(CommandHandler("write", SimpleBot.write_command))
    application.add_handler(CommandHandler("my_progress", SimpleBot.my_progress_command))
    
    # === 구독 관련 핸들러들 ===
    application.add_handler(CommandHandler("subscribe_daily", SimpleBot.subscribe_daily_command))
    application.add_handler(CommandHandler("unsubscribe_daily", SimpleBot.unsubscribe_daily_command))
    
    # === 번역 관련 핸들러들 ===
    application.add_handler(CommandHandler("trs", SimpleBot.translate_simple_command))
    application.add_handler(CommandHandler("trl", SimpleBot.translate_long_command))
    application.add_handler(CommandHandler("ls", SimpleBot.listening_command))
    application.add_handler(CommandHandler("trls", SimpleBot.translate_listen_command))
    
    # === 시스템 관련 핸들러들 ===
    application.add_handler(CommandHandler("model_status", SimpleBot.model_status_command))
    
    # === 퀘스트 도움 명령어들 ===
    application.add_handler(CommandHandler("hint", SimpleBot.hint_command))
    application.add_handler(CommandHandler("trans", SimpleBot.translation_command))
    
    # === AI 대화 핸들러 (명령어가 아닌 일반 메시지) ===
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, SimpleBot.handle_message))
    
    logger.info("🤖 러시아어 학습 봇 '루샤(Rusya)'가 시작되었습니다!")
    logger.info("🚀 모든 기능이 무제한으로 제공됩니다!")
    logger.info("📚 업그레이드된 명령어들:")
    logger.info("   • /start - 명령어 안내")
    logger.info("   • /help - 카테고리별 상세 도움말")
    logger.info("   • /write - AI 작문 교정 (상세 피드백)")
    logger.info("   • /trs, /trl - 간단/상세 번역")
    logger.info("   • /ls, /trls - 음성 변환")
    logger.info("   • /quest - 업그레이드된 퀘스트")
    logger.info("   • /hint, /trans - 퀘스트 도움말")
    logger.info("   • /my_progress - 상세 학습 통계")
    logger.info("✅ 명령어 방식으로 단순화 완료!")
    
    # 봇 실행 (최강 충돌 방지 설정)
    logger.info("🔥 충돌 방지 폴링 시작!")
    application.run_polling(
        drop_pending_updates=True,    # 시작 시 모든 pending updates 삭제
        close_loop=False,             # 루프 자동 종료 비활성화
        stop_signals=None,            # 신호 처리 완전 비활성화
        allowed_updates=None,         # 모든 업데이트 허용
        pool_timeout=30,              # 긴 타임아웃
        connect_timeout=30,           # 연결 타임아웃
        read_timeout=30               # 읽기 타임아웃
    )

if __name__ == '__main__':
    main() 