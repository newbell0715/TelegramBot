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
    
    # === 기본 명령어 핸들러들 ===
    application.add_handler(CommandHandler("start", SimpleBot.start_command))
    application.add_handler(CommandHandler("help", SimpleBot.help_command))
    
    # === 학습 관련 핸들러들 ===
    application.add_handler(CommandHandler("quest", SimpleBot.quest_command))
    application.add_handler(CommandHandler("action", SimpleBot.action_command))
    application.add_handler(CommandHandler("write", SimpleBot.write_command))
    application.add_handler(CommandHandler("my_progress", SimpleBot.my_progress_command))
    
    # === 🌟 혁신적인 게임화된 학습 시스템 ===
    application.add_handler(CommandHandler("games", SimpleBot.games_command))
    application.add_handler(CommandHandler("game_word_match", SimpleBot.word_match_game_command))
    application.add_handler(CommandHandler("game_sentence_builder", SimpleBot.sentence_builder_game_command))
    application.add_handler(CommandHandler("game_speed_quiz", SimpleBot.speed_quiz_command))
    application.add_handler(CommandHandler("game_pronunciation", SimpleBot.pronunciation_challenge_command))
    
    # === 🏆 성취 시스템 ===
    application.add_handler(CommandHandler("achievements", SimpleBot.achievements_command))
    
    # === 🧠 개인화된 AI 튜터 시스템 ===
    application.add_handler(CommandHandler("ai_tutor", SimpleBot.ai_tutor_command))
    application.add_handler(CommandHandler("personalized_lesson", SimpleBot.personalized_lesson_command))
    application.add_handler(CommandHandler("learning_analytics", SimpleBot.learning_analytics_command))
    application.add_handler(CommandHandler("weak_area_practice", SimpleBot.weak_area_practice_command))
    application.add_handler(CommandHandler("adaptive_quiz", SimpleBot.adaptive_quiz_command))
    
    # === 🎯 스마트 학습 시스템 ===
    application.add_handler(CommandHandler("srs_review", SimpleBot.srs_review_command))
    application.add_handler(CommandHandler("vocabulary_builder", SimpleBot.vocabulary_builder_command))
    application.add_handler(CommandHandler("pronunciation_score", SimpleBot.pronunciation_score_command))
    
    # === 👥 소셜 학습 기능 ===
    application.add_handler(CommandHandler("leaderboard", SimpleBot.leaderboard_command))
    application.add_handler(CommandHandler("challenge_friend", SimpleBot.challenge_friend_command))
    application.add_handler(CommandHandler("study_buddy", SimpleBot.study_buddy_command))
    
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
    
    logger.info("🤖 🌟 **지구 최고의 러시아어 학습 봇 '루샤(Rusya)' 업그레이드 완료!** 🌟")
    logger.info("🚀 모든 혁신적인 기능이 무제한으로 제공됩니다!")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🎮 **새로운 게임화된 학습 시스템:**")
    logger.info("   • /games - 게임 메뉴")
    logger.info("   • /game_word_match - 단어 매칭 게임")
    logger.info("   • /game_sentence_builder - 문장 조립 게임")
    logger.info("   • /game_speed_quiz - 스피드 퀴즈")
    logger.info("   • /game_pronunciation - 발음 챌린지")
    logger.info("🏆 **성취 시스템:**")
    logger.info("   • /achievements - 성취 확인")
    logger.info("🧠 **개인화된 AI 튜터:**")
    logger.info("   • /ai_tutor - AI 튜터 상담")
    logger.info("   • /personalized_lesson - 맞춤형 수업")
    logger.info("   • /learning_analytics - 학습 분석")
    logger.info("🎯 **스마트 학습 도구:**")
    logger.info("   • /srs_review - 간격 반복 학습")
    logger.info("   • /vocabulary_builder - 어휘 확장")
    logger.info("   • /pronunciation_score - 발음 평가")
    logger.info("👥 **소셜 학습:**")
    logger.info("   • /leaderboard - 리더보드")
    logger.info("   • /challenge_friend - 친구 도전")
    logger.info("   • /study_buddy - 스터디 버디")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("✅ 지구 최고 수준의 언어학습 봇으로 업그레이드 완료!")
    
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