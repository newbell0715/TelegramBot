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
    try:
        logger.info("🚨 콜백 쿼리 핸들러 호출됨!")
        
        query = update.callback_query
        logger.info(f"📱 query 객체: {query}")
        
        await query.answer()
        logger.info("✅ query.answer() 완료")
        
        data = query.data
        chat_id = query.message.chat_id
        user = query.from_user
        
        # 디버깅용 로그
        logger.info(f"🔘 콜백 수신: {data} (사용자: {user.first_name}, 채팅: {chat_id})")
        logger.info(f"📊 Raw update: {update}")
        
        # 테스트용 즉시 응답
        await query.message.reply_text(f"🧪 **테스트 응답**\n\n수신된 콜백: `{data}`\n시간: {query.message.date}")
        logger.info("🧪 테스트 응답 전송 완료")
        
        # SimpleBot 콜백 처리
        if data == "start_quest":
            # 퀘스트 시작
            logger.info("🏆 퀘스트 시작 버튼 클릭됨")
            import SimpleBot
            
            # 제대로 된 FakeUpdate 클래스
            class FakeUpdate:
                def __init__(self):
                    self.effective_chat = type('Chat', (), {'id': chat_id})()
                    self.effective_user = user
                    self.message = query.message
            
            fake_update = FakeUpdate()
            await SimpleBot.quest_command(fake_update, context)
        
        elif data == "help_write":
            logger.info("✍️ 작문 교정 도움말 버튼 클릭됨")
            await query.message.reply_text(
                "**✍️ AI 작문 교정 사용법**\n\n"
                "📝 **명령어:** `/write [교정받고 싶은 러시아어 문장]`\n\n"
                "📚 **예시:**\n"
                "• `/write Я хочу изучать русский язык`\n"
                "• `/write Вчера я пошёл в магазин`\n"
                "• `/write Мне нравится читать книги`\n\n"
                "🎯 **제공 기능:**\n"
                "✅ 문법 오류 수정\n"
                "✅ 자연스러운 표현 제안\n"
                "✅ 상세한 설명과 이유\n"
                "✅ 칭찬과 동기부여\n\n"
                "💡 **팁:** 틀려도 괜찮으니 자유롭게 문장을 만들어보세요!"
            )
        
        elif data == "help_translate":
            logger.info("🌍 번역 도움말 버튼 클릭됨")
            await query.message.reply_text(
                "**🌍 번역 시스템 사용법**\n\n"
                "**⚡ 간단 번역**\n"
                "• `/trs [언어] [텍스트]` - 빠르고 정확한 번역\n"
                "• 예시: `/trs russian 안녕하세요`\n\n"
                "**📚 상세 번역**\n"
                "• `/trl [언어] [텍스트]` - 문법 분석 + 단어 설명\n"
                "• 예시: `/trl russian 좋은 아침이에요`\n\n"
                "**🎵 번역+음성**\n"
                "• `/trls [언어] [텍스트]` - 번역과 음성을 한번에\n"
                "• 예시: `/trls russian 안녕하세요`\n\n"
                "🌍 **지원언어:** korean(kr), russian(ru), english(en)"
            )
        
        elif data == "help_tts":
            logger.info("🎵 음성 변환 도움말 버튼 클릭됨")
            await query.message.reply_text(
                "**🎵 음성 변환 사용법**\n\n"
                "🔊 **명령어:** `/ls [텍스트]`\n\n"
                "📚 **예시:**\n"
                "• `/ls 안녕하세요` (한국어)\n"
                "• `/ls Привет, как дела?` (러시아어)\n"
                "• `/ls 좋은 아침이에요` (한국어)\n\n"
                "🎯 **특징:**\n"
                "✅ 한국어/러시아어 자동 인식\n"
                "✅ 고품질 Google TTS 엔진\n"
                "✅ 완전 무료 서비스\n\n"
                "💡 **발음 연습 팁:** 음성을 들으며 따라 읽어보세요!"
            )
        
        elif data == "my_progress":
            # 진도 확인
            logger.info("📊 나의 학습 진도 버튼 클릭됨")
            import SimpleBot
            class FakeUpdate:
                def __init__(self):
                    self.effective_chat = type('Chat', (), {'id': chat_id})()
                    self.effective_user = user
                    self.message = query.message
            
            fake_update = FakeUpdate()
            await SimpleBot.my_progress_command(fake_update, context)
        
        elif data == "full_help":
            # 전체 도움말
            logger.info("📚 전체 도움말 버튼 클릭됨")
            import SimpleBot
            class FakeUpdate:
                def __init__(self):
                    self.effective_chat = type('Chat', (), {'id': chat_id})()
                    self.effective_user = user
                    self.message = query.message
            
            fake_update = FakeUpdate()
            await SimpleBot.help_command(fake_update, context)
        
        elif data == "subscribe_daily":
            # 일일 학습 구독
            logger.info("📅 일일 학습 구독 버튼 클릭됨")
            import SimpleBot
            class FakeUpdate:
                def __init__(self):
                    self.effective_chat = type('Chat', (), {'id': chat_id})()
                    self.effective_user = user
                    self.message = query.message
            
            fake_update = FakeUpdate()
            await SimpleBot.subscribe_daily_command(fake_update, context)
        
        # 퀘스트 관련 콜백
        elif data == "quest_hint":
            logger.info("💡 퀘스트 힌트 버튼 클릭됨")
            await query.message.reply_text(
                "💡 **퀘스트 힌트**\n\n"
                "• 상황에 맞는 러시아어 인사말을 사용해보세요\n"
                "• 'Здравствуйте' (공손한 인사)\n"
                "• 'Привет' (친근한 인사)\n"
                "• 주문할 때는 'пожалуйста'를 붙이면 더 정중해요\n\n"
                "🔄 `/action [러시아어 문장]`으로 다시 시도해보세요!"
            )
        
        elif data == "quest_translation":
            logger.info("📖 퀘스트 번역 버튼 클릭됨")
            await query.message.reply_text(
                "📖 **주요 표현 번역**\n\n"
                "• **Здравствуйте** - 안녕하세요 (정중)\n"
                "• **Привет** - 안녕 (친근)\n"
                "• **кофе** - 커피\n"
                "• **пожалуйста** - 부탁합니다/주세요\n"
                "• **спасибо** - 감사합니다\n"
                "• **карта/картой** - 카드/카드로\n\n"
                "💡 이 표현들을 조합해서 문장을 만들어보세요!"
            )
        
        elif data == "restart_quest":
            logger.info("🔄 퀘스트 재시작 버튼 클릭됨")
            await query.message.reply_text(
                "🔄 **퀘스트 다시 시작**\n\n"
                "퀘스트를 처음부터 다시 시작하려면 `/quest` 명령어를 입력하세요!\n"
                "새로운 마음가짐으로 러시아어 회화에 도전해보세요! 💪"
            )
        
        else:
            logger.warning(f"⚠️ 알 수 없는 콜백 데이터: {data}")
            await query.message.reply_text("❌ 알 수 없는 명령입니다.")
            
    except Exception as e:
        logger.error(f"❌ 콜백 처리 중 오류: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        try:
            await query.message.reply_text("😅 처리 중 오류가 발생했습니다. 다시 시도해주세요!")
        except:
            pass

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
    
    # === 콜백 쿼리 핸들러 (최우선 등록) ===
    logger.info("🔘 콜백 쿼리 핸들러 등록 중...")
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    logger.info("✅ 콜백 쿼리 핸들러 등록 완료!")
    
    # === 퀴즈 관련 핸들러들 ===
    from handlers.quiz import quiz_command
    application.add_handler(CommandHandler("quiz", quiz_command))
    
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
    logger.info("🔘 콜백 쿼리 핸들러 등록 완료!")
    
    # 봇 실행 (충돌 방지 설정)
    logger.info("🚀 봇 폴링 시작 - 충돌 방지 모드")
    application.run_polling(
        drop_pending_updates=True,  # 시작 시 모든 pending updates 삭제
        close_loop=False,           # 루프 자동 종료 비활성화
        stop_signals=None           # 신호 처리 비활성화 (Railway 환경용)
    )

if __name__ == '__main__':
    main() 