import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# 봇 토큰
BOT_TOKEN = "8064422632:AAFkFqQDA_35OCa5-BFxeHPA9_hil4cY8Rg"

# 로깅 설정
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 테스트용 콜백 핸들러
async def test_callback_handler(update: Update, context):
    """테스트용 콜백 핸들러"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"🔘 테스트 콜백 수신: {query.data}")
    
    if query.data == "test_button":
        await query.message.reply_text("✅ 버튼이 정상 작동합니다!")
        logger.info("✅ 테스트 버튼 응답 완료")
    else:
        await query.message.reply_text(f"📊 수신된 콜백: {query.data}")

# 테스트 명령어
async def test_command(update: Update, context):
    """테스트 명령어"""
    keyboard = [
        [InlineKeyboardButton("🧪 테스트 버튼", callback_data="test_button")],
        [InlineKeyboardButton("🔥 또 다른 테스트", callback_data="test_button_2")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🧪 **콜백 쿼리 테스트**\n\n"
        "버튼을 클릭해서 반응을 확인하세요!",
        reply_markup=reply_markup
    )
    logger.info("🧪 테스트 명령어 실행됨")

def main():
    """테스트 봇 실행"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 핸들러 등록
    application.add_handler(CommandHandler("test", test_command))
    application.add_handler(CallbackQueryHandler(test_callback_handler))
    
    logger.info("🧪 테스트 봇 시작!")
    logger.info("💡 /test 명령어로 테스트하세요!")
    
    # 봇 실행
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main() 