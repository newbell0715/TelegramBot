import os
import logging
import asyncio
from datetime import datetime
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

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
from handlers.premium import (
    premium_command,
    upgrade_handler,
    donate_command,
    admin_stats_command
)
from handlers.quiz import (
    quiz_command,
    quiz_callback_handler,
    leaderboard_command
)

# --- 서비스 import ---
from services.scheduler_service import create_scheduler
from services.gemini_service import chat_with_gemini
from utils.data_utils import UserManager

async def handle_message(update, context):
    """일반 메시지 처리 - AI 채팅"""
    user_message = update.message.text
    chat_id = update.effective_chat.id
    user = UserManager.get_user(chat_id)
    
    # Premium 사용자는 무제한, Free는 일일 10회 제한
    if user['plan'] == 'Free':
        can_use, current, limit = UserManager.check_usage_limit(chat_id, 'chat_messages')
        if not can_use:
            await update.message.reply_text(
                f"❌ 오늘의 AI 채팅 횟수를 모두 사용했습니다. ({current}/{limit})\n"
                "💎 Pro 플랜으로 업그레이드하면 무제한 채팅이 가능합니다! /premium"
            )
            return
        UserManager.increment_usage(chat_id, 'chat_messages')
    
    # "생각 중..." 메시지 표시
    processing_message = await update.message.reply_text("🤔 생각 중... 😊")
    
    try:
        # 대화 맥락 (Premium 기능)
        context_message = None
        if user['plan'] in ['Premium']:
            # 간단한 대화 맥락 유지 (최근 메시지)
            context_message = f"이전 대화를 고려하여 자연스럽게 대답해주세요."
        
        # AI 응답 생성
        response = await chat_with_gemini(user_message, context_message)
        
        # 응답 전송
        await processing_message.delete()
        
        # 긴 응답 처리
        if len(response) > 4096:
            # 메시지를 여러 부분으로 나누기
            parts = [response[i:i+4096] for i in range(0, len(response), 4096)]
            for i, part in enumerate(parts):
                if i == 0:
                    await update.message.reply_text(part)
                else:
                    await update.message.reply_text(f"📄 (계속 {i+1}/{len(parts)})\n\n{part}")
        else:
            await update.message.reply_text(response)
    
    except Exception as e:
        logger.error(f"AI 채팅 오류: {e}")
        await processing_message.delete()
        await update.message.reply_text("죄송합니다. AI와 대화 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. 😅")

async def feedback_command(update, context):
    """피드백 명령어"""
    if not context.args:
        await update.message.reply_text(
            "💭 **피드백 보내기**\n\n"
            "사용법: /feedback [여러분의 의견]\n\n"
            "예시:\n"
            "• /feedback 퀴즈 기능이 재미있어요!\n"
            "• /feedback 새로운 언어도 추가해주세요\n"
            "• /feedback 버그 발견: 번역이 이상해요\n\n"
            "여러분의 소중한 의견을 기다립니다! 🙏"
        )
        return
    
    feedback_text = " ".join(context.args)
    user = update.effective_user
    
    # 피드백 로깅 (실제 프로덕션에서는 데이터베이스나 파일에 저장)
    logger.info(f"FEEDBACK from {user.first_name} ({user.id}): {feedback_text}")
    
    # 사용자에게 감사 메시지
    await update.message.reply_text(
        "✅ **피드백이 전송되었습니다!**\n\n"
        "소중한 의견 감사드립니다. 더 나은 서비스를 만들기 위해 참고하겠습니다! 🙏\n\n"
        "💝 피드백 제공자에게는 특별 배지를 드립니다!"
    )
    
    # 사용자에게 피드백 배지 추가
    UserManager.update_user_stats(update.effective_chat.id, 'total_exp', 5)

async def model_status_command(update, context):
    """AI 모델 상태 확인"""
    from services.gemini_service import gemini_service
    
    status = gemini_service.get_status()
    
    status_text = f"""
🤖 **AI 모델 상태**

📍 **현재 모델**: {status['current_model']}
📊 **오늘 요청수**: {status['daily_requests']}회
🔄 **캐시 크기**: {status['cache_size']}개
{'✅ 최고 성능 모델 사용 중' if status['is_primary'] else '⚠️ 폴백 모델 사용 중'}

🔧 **상태**: {'정상' if status['failure_count'] == 0 else f'오류 {status["failure_count"]}회'}
📅 **마지막 리셋**: {status['last_reset']}
"""
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def stats_command(update, context):
    """향상된 통계 명령어"""
    from utils.data_utils import format_user_stats, ProgressTracker
    
    user = UserManager.get_user(update.effective_chat.id)
    stats_text = format_user_stats(user)
    
    # 진행률 시각화 추가
    level = user['stats'].get('level', 1)
    exp = user['stats'].get('total_exp', 0)
    exp_in_level = exp % 100
    
    progress_bar = ProgressTracker.calculate_progress_bar(exp_in_level, 100, 15)
    
    # 연속 학습일 정보
    streak_info = ProgressTracker.get_streak_info(update.effective_chat.id)
    
    enhanced_stats = f"""
{stats_text}

🔥 **연속 학습**
• 현재 연속일: {streak_info['current_streak']}일
• 최장 연속일: {streak_info['longest_streak']}일
• 연속 배지: {streak_info['badge']}

📊 **레벨 진행도**
레벨 {level}: {progress_bar} {exp_in_level}/100 EXP
"""
    
    # 키보드 추가
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [InlineKeyboardButton("📈 상세 분석", callback_data="detailed_stats")],
        [InlineKeyboardButton("🏆 랭킹 보기", callback_data="leaderboard")],
        [InlineKeyboardButton("💎 플랜 업그레이드", callback_data="upgrade_pro_monthly")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(enhanced_stats, reply_markup=reply_markup, parse_mode='Markdown')

async def main() -> None:
    """메인 실행 함수 - 대폭 개선된 버전"""
    if not BOT_TOKEN or not GEMINI_API_KEY:
        logger.error("텔레그램 봇 토큰 또는 Gemini API 키가 설정되지 않았습니다!")
        return

    # 애플리케이션 생성
    application = Application.builder().token(BOT_TOKEN).build()
    
    # === 기본 명령어 핸들러 ===
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # === 번역 & TTS 핸들러 ===
    application.add_handler(CommandHandler("trs", translate_simple_command))
    application.add_handler(CommandHandler("trl", translate_long_command))
    application.add_handler(CommandHandler("ls", listening_command))
    application.add_handler(CommandHandler("trls", translate_listen_command))
    
    # === 퀘스트 핸들러 ===
    application.add_handler(CommandHandler("quest", quest_command))
    application.add_handler(CommandHandler("action", action_command))
    
    # === 학습 핸들러 ===
    application.add_handler(CommandHandler("write", write_command))
    application.add_handler(CommandHandler("my_progress", my_progress_command))
    application.add_handler(CommandHandler("subscribe_daily", subscribe_daily_command))
    application.add_handler(CommandHandler("unsubscribe_daily", unsubscribe_daily_command))
    
    # === 프리미엄 & 수익화 핸들러 ===
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CommandHandler("donate", donate_command))
    application.add_handler(CommandHandler("admin_stats", admin_stats_command))
    
    # === 퀴즈 & 게임화 핸들러 ===
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    
    # === 새로운 고급 기능 핸들러 ===
    application.add_handler(CommandHandler("feedback", feedback_command))
    application.add_handler(CommandHandler("model_status", model_status_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # === 콜백 쿼리 핸들러 ===
    application.add_handler(CallbackQueryHandler(upgrade_handler, pattern=r"^(upgrade_|compare_|premium_|plan_|back_to_)"))
    application.add_handler(CallbackQueryHandler(quiz_callback_handler, pattern=r"^(quiz_|answer_)"))
    
    # === 일반 메시지 핸들러 (AI 채팅) ===
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # === 스케줄러 생성 및 시작 ===
    scheduler = create_scheduler(application.bot)
    
    logger.info("🚀 최고의 러시아어 학습 봇 '루샤'가 활동을 시작합니다!")
    logger.info("✨ 새로운 기능: 퀴즈, 프리미엄, AI 채팅, 리더보드, 향상된 UI")
    
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