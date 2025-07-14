import os
import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
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

# --- 콜백 쿼리 핸들러 ---
async def callback_query_handler(update, context):
    """인라인 키보드 콜백 쿼리 처리"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    
    # 퀴즈 관련 콜백
    if data.startswith('quiz_'):
        from handlers.quiz import start_quiz, show_question, handle_quiz_answer, show_quiz_history, show_leaderboard
        
        if data == 'quiz_menu':
            # 퀴즈 메뉴 다시 표시
            from config.settings import QUIZ_CATEGORIES
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = []
            for category_id, category_data in QUIZ_CATEGORIES.items():
                keyboard.append([InlineKeyboardButton(
                    f"{category_data['emoji']} {category_data['name']}", 
                    callback_data=f"quiz_{category_id}"
                )])
            
            keyboard.append([InlineKeyboardButton("📊 내 퀴즈 기록", callback_data="quiz_history")])
            keyboard.append([InlineKeyboardButton("🏅 리더보드", callback_data="leaderboard")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🧠 **퀴즈 카테고리를 선택해주세요:**",
                reply_markup=reply_markup
            )
            
        elif data in ['quiz_vocabulary', 'quiz_grammar', 'quiz_pronunciation']:
            category = data.replace('quiz_', '')
            await start_quiz(update, context, category)
            
        elif data.startswith('quiz_answer_'):
            answer_index = int(data.split('_')[-1])
            await handle_quiz_answer(update, context, answer_index)
            
        elif data == 'quiz_next':
            await show_question(update, context)
            
        elif data == 'quiz_quit':
            await query.edit_message_text("❌ **퀴즈를 종료했습니다.**\n\n언제든 `/quiz`로 다시 시작하세요!")
            
        elif data == 'quiz_history':
            await show_quiz_history(update, context)
            
        elif data == 'leaderboard':
            await show_leaderboard(update, context)
    
    # 기본 기능 콜백
    elif data == 'start_quest':
        # SimpleBot.py의 quest_command 가져오기
        import SimpleBot
        
        # 가짜 업데이트 객체 생성
        class FakeUpdate:
            def __init__(self, chat_id, user):
                self.effective_chat = type('obj', (object,), {'id': chat_id})()
                self.effective_user = user
                self.message = type('obj', (object,), {
                    'reply_text': query.edit_message_text,
                    'chat_id': chat_id
                })()
        
        fake_update = FakeUpdate(chat_id, query.from_user)
        await SimpleBot.quest_command(fake_update, context)
        
    elif data == 'help_write':
        help_text = """
✍️ **AI 작문 교정 완전 가이드**

📝 **기본 사용법:**
`/write [러시아어 문장]`

📚 **상세 예시:**
• `/write Я хочу изучать русский язык`
  → "러시아어를 배우고 싶어요" 교정

• `/write Вчера я пошёл в магазин`
  → "어제 가게에 갔어요" 문법 검사

• `/write Мне нравится читать книги`
  → "책 읽는 것을 좋아해요" 표현 개선

🎯 **AI가 제공하는 서비스:**
✅ **문법 오류 검출 및 수정**
✅ **자연스러운 표현 제안**
✅ **상세한 설명과 학습 포인트**
✅ **동기부여 피드백과 칭찬**
✅ **추가 학습 팁 제공**

💡 **학습 효과를 높이는 팁:**
🔹 틀려도 괜찮으니 자유롭게 작성하세요
🔹 일상 대화문을 만들어 실용성 높이기
🔹 교정 결과를 `/ls`로 음성 확인하기
🔹 비슷한 문장으로 반복 연습하기

⭐ **경험치:** 작문 교정 1회당 +10 EXP 획득!
        """
        await query.edit_message_text(help_text)
        
    elif data == 'help_translate':
        help_text = """
🌍 **스마트 번역 시스템 완전 가이드**

⚡ **간단 번역:** `/trs [언어] [텍스트]`
📝 **사용 예시:**
• `/trs russian 안녕하세요` → Здравствуйте
• `/trs korean Привет` → 안녕하세요
• `/trs en 감사합니다` → Thank you

📚 **상세 번역:** `/trl [언어] [텍스트]`
📝 **사용 예시:**
• `/trl russian 좋은 아침이에요`
  → 번역 + 문법 분석 + 단어 설명

🎵 **번역+음성:** `/trls [언어] [텍스트]`
📝 **사용 예시:**
• `/trls russian 감사합니다`
  → 번역 결과를 음성으로 바로 들을 수 있음

🌍 **지원하는 언어:**
• **한국어:** `korean`, `kr`
• **러시아어:** `russian`, `ru`  
• **영어:** `english`, `en`

💡 **사용 팁:**
🔹 간단한 확인은 `/trs` 사용
🔹 문법 학습이 목적이면 `/trl` 사용
🔹 발음 연습이 필요하면 `/trls` 사용
🔹 복잡한 문장은 단어별로 나누어 번역

⭐ **경험치:** 번역 1회당 +5 EXP 획득!
        """
        await query.edit_message_text(help_text)
        
    elif data == 'help_tts':
        help_text = """
🎵 **음성 변환 (TTS) 완전 가이드**

🔊 **기본 사용법:**
`/ls [텍스트]`

📚 **다양한 예시:**
• `/ls 안녕하세요` (한국어 음성)
• `/ls Привет, как дела?` (러시아어 음성)
• `/ls Доброе утро!` (러시아어 음성)
• `/ls 좋은 하루 되세요` (한국어 음성)

🎯 **고급 기능:**
✅ **언어 자동 감지** - 한국어/러시아어 자동 인식
✅ **고품질 Google TTS** - 자연스러운 발음
✅ **최적화된 속도** - 학습에 적합한 속도
✅ **즉시 재생** - 텔레그램에서 바로 재생

🚀 **학습 활용법:**
🔹 **발음 연습:** 번역 결과를 음성으로 들어보기
🔹 **청취 훈련:** 러시아어 문장을 반복 청취
🔹 **억양 학습:** 자연스러운 억양 체득
🔹 **확신 검증:** 내가 읽는 발음과 비교

💡 **효과적인 사용 순서:**
1️⃣ `/trs`로 번역하기
2️⃣ `/ls`로 발음 듣기  
3️⃣ 따라 말하며 연습하기
4️⃣ `/write`로 문장 만들어보기

⭐ **경험치:** 음성 변환 1회당 +3 EXP 획득!
        """
        await query.edit_message_text(help_text)
        
    elif data == 'my_progress':
        import SimpleBot
        
        class FakeUpdate:
            def __init__(self, chat_id, user):
                self.effective_chat = type('obj', (object,), {'id': chat_id})()
                self.effective_user = user
                self.message = type('obj', (object,), {
                    'reply_text': query.edit_message_text,
                })()
        
        fake_update = FakeUpdate(chat_id, query.from_user)
        await SimpleBot.my_progress_command(fake_update, context)
        
    elif data == 'subscribe_daily':
        import SimpleBot
        
        class FakeUpdate:
            def __init__(self, chat_id):
                self.effective_chat = type('obj', (object,), {'id': chat_id})()
                self.message = type('obj', (object,), {
                    'reply_text': query.edit_message_text,
                })()
        
        fake_update = FakeUpdate(chat_id)
        await SimpleBot.subscribe_daily_command(fake_update, context)
        
    elif data == 'full_help':
        import SimpleBot
        
        class FakeUpdate:
            def __init__(self):
                self.message = type('obj', (object,), {
                    'reply_text': query.edit_message_text,
                })()
        
        fake_update = FakeUpdate()
        await SimpleBot.help_command(fake_update, context)

def main():
    """메인 실행 함수"""
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
    
    # === 퀴즈 관련 핸들러들 ===
    from handlers.quiz import quiz_command
    application.add_handler(CommandHandler("quiz", quiz_command))
    
    # === 콜백 쿼리 핸들러 ===
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # === AI 대화 핸들러 (명령어가 아닌 일반 메시지) ===
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, SimpleBot.handle_message))
    
    logger.info("🤖 러시아어 학습 봇 '루샤(Rusya)'가 시작되었습니다!")
    logger.info("🚀 모든 기능이 무제한으로 제공됩니다!")
    logger.info("📚 업그레이드된 명령어들:")
    logger.info("   • /start - 향상된 시작 화면 (인라인 키보드)")
    logger.info("   • /help - 카테고리별 상세 도움말")
    logger.info("   • /write - AI 작문 교정 (상세 피드백)")
    logger.info("   • /trs, /trl - 간단/상세 번역")
    logger.info("   • /ls, /trls - 음성 변환")
    logger.info("   • /quiz - 무제한 퀴즈 시스템")
    logger.info("   • /quest - 업그레이드된 퀘스트")
    logger.info("   • /my_progress - 상세 학습 통계")
    
    # 봇 실행
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main() 