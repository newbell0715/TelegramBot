import os
import logging
import requests
import io
from datetime import datetime
import pytz
from gtts import gTTS
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# 러시아 모스크바 시간대 설정
MSK = pytz.timezone('Europe/Moscow')

# 러시아 시간대를 사용하는 커스텀 로거 포맷터
class MSKFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, MSK)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S')

# 로깅 설정 (러시아 모스크바 시간대 적용)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 러시아 시간대 포맷터 적용
for handler in logging.root.handlers:
    handler.setFormatter(MSKFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger = logging.getLogger(__name__)

# Google Gemini AI 설정
genai.configure(api_key="AIzaSyCmH1flv0HSRp8xYa1Y8oL7xnpyyQVuIw8")  # Gemini Pro 계정 API 키

# Gemini 모델 초기화 - 이제 최신 Pro 모델 사용!
model = genai.GenerativeModel('gemini-2.5-pro')

# 텔레그램 봇 토큰
BOT_TOKEN = "8064422632:AAFkFqQDA_35OCa5-BFxeHPA9_hil4cY8Rg"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """봇 시작 메시지"""
    user_name = update.effective_user.first_name
    chat_id = update.effective_chat.id
    
    # 친구 등록을 위한 정보 로깅
    logger.info(f"새로운 사용자 시작: {user_name} (Chat ID: {chat_id})")
    
    await update.message.reply_text(
        f'안녕하세요 {user_name}님! 저는 Gemini AI 봇입니다! 🤖\n'
        f'무엇이든 물어보세요! 저는 24/7 돌아가고 있어요! ⚡\n'
        f'🎉 현재 버전: v1.1 (Railway 자동 배포 테스트)\n\n'
        f'🌍 번역 & TTS 기능:\n'
        f'- /trs [언어] [텍스트] - 간단 번역\n'
        f'- /trl [언어] [텍스트] - 상세 번역\n'
        f'- /ls [텍스트] - 한국어/러시아어 음성 변환\n'
        f'- /trls [언어] [텍스트] - 간단 번역+음성\n\n'
        f'💡 예시:\n'
        f'- /trs english 안녕하세요 (또는 /trs en)\n'
        f'- /trl english 안녕하세요 (또는 /trl en)\n'
        f'- /ls 안녕하세요 (한국어 음성)\n'
        f'- /trls russian 좋은 아침이에요 (또는 /trls ru)\n\n'
        f'🎵 TTS 지원: 한국어 🇰🇷, 러시아어 🇷🇺\n'
        f'🌍 지원 언어: english (en), russian (ru), korean (kr)\n\n'
        f'📋 Chat ID: `{chat_id}`\n'
        f'💡 /help 명령어로 더 자세한 사용법을 확인하세요!'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """도움말 메시지"""
    help_text = """
🤖 Gemini AI 봇 사용법

📝 기본 기능:
- 일반 채팅: 그냥 메시지 보내기
- /start - 봇 시작 & Chat ID 확인
- /help - 도움말

🌍 번역 & TTS 기능:
- /trs [언어] [텍스트] - 간단 번역 (최고의 번역만)
- /trl [언어] [텍스트] - 상세 번역 (문법, 단어 분석)
- /ls [텍스트] - 한국어/러시아어 음성 듣기 🎵
- /trls [언어] [텍스트] - 간단 번역 + 음성 🎯

💡 사용 예시:
- /trs english 안녕하세요 (또는 /trs en) - 간단한 번역
- /trl english 안녕하세요 (또는 /trl en) - 상세한 번역 + 분석
- /ls 안녕하세요 (한국어 음성)
- /ls Привет! (러시아어 음성)
- /trls russian 안녕하세요 (또는 /trls ru) - 간단 번역+음성

🔑 주요 차이점:
- /trs: 간단하고 빠른 번역
- /trl: 상세 번역 + 발음 + 문법 + 단어 분석
- /trls: 간단한 번역 + 음성 (TTS 최적화)
- /ls: 음성 변환만 (자동 언어 감지)

🌍 지원 언어:
- english (en), russian (ru), korean (kr)

🎵 TTS 지원 언어:
- 한국어 🇰🇷, 러시아어 🇷🇺

🚀 24/7 서비스 중!
    """
    await update.message.reply_text(help_text)

async def chat_with_gemini(text: str) -> str:
    """Gemini와 대화"""
    try:
        response = model.generate_content(text)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API 오류: {e}")
        return "죄송합니다. 잠시 후 다시 시도해주세요. 😅"

async def convert_text_to_speech(text: str, lang: str = "auto") -> bytes:
    """무료 Google TTS로 텍스트를 음성으로 변환 (한국어, 러시아어 지원)"""
    try:
        # 언어 자동 감지 또는 지정
        if lang == "auto":
            # 한글이 포함되어 있으면 한국어, 키릴 문자가 포함되어 있으면 러시아어
            if any('\u3131' <= char <= '\u3163' or '\uac00' <= char <= '\ud7a3' for char in text):
                detected_lang = "ko"
                lang_name = "한국어"
            elif any('\u0400' <= char <= '\u04ff' for char in text):
                detected_lang = "ru"
                lang_name = "러시아어"
            else:
                # 기본값을 한국어로 설정
                detected_lang = "ko"
                lang_name = "한국어 (기본값)"
        else:
            detected_lang = lang
            lang_name = "러시아어" if lang == "ru" else "한국어" if lang == "ko" else lang
            
        logger.info(f"TTS 시작 - 텍스트: '{text}', 감지된 언어: {lang_name} ({detected_lang})")
        
        # 텍스트가 너무 길면 자르기 (gTTS 제한: 200자 정도)
        if len(text) > 200:
            text = text[:200] + "..."
            logger.info(f"텍스트 자름 - 새 길이: {len(text)}")
        
        # gTTS 객체 생성
        logger.info("gTTS 객체 생성 중...")
        tts = gTTS(text=text, lang=detected_lang, slow=False)
        
        # 메모리에서 음성 파일 생성
        logger.info("음성 파일 생성 중...")
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        audio_data = audio_buffer.getvalue()
        logger.info(f"음성 파일 생성 완료 - 크기: {len(audio_data)} bytes, 언어: {lang_name}")
        
        return audio_data
    except Exception as e:
        logger.error(f"TTS 오류: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        return None

async def split_long_message(text: str, max_length: int = 4096) -> list:
    """긴 메시지를 여러 부분으로 나누기"""
    if len(text) <= max_length:
        return [text]
    
    # 메시지를 여러 부분으로 나누기
    parts = []
    current_part = ""
    
    # 줄 단위로 나누기
    lines = text.split('\n')
    
    for line in lines:
        # 현재 부분 + 새 줄이 최대 길이를 초과하는지 확인
        if len(current_part) + len(line) + 1 > max_length:
            if current_part:
                parts.append(current_part.strip())
                current_part = line
            else:
                # 한 줄이 너무 긴 경우 강제로 자르기
                while len(line) > max_length:
                    parts.append(line[:max_length])
                    line = line[max_length:]
                current_part = line
        else:
            if current_part:
                current_part += "\n" + line
            else:
                current_part = line
    
    # 마지막 부분 추가
    if current_part:
        parts.append(current_part.strip())
    
    return parts

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """일반 메시지 처리"""
    user_message = update.message.text
    user_name = update.effective_user.first_name
    
    # 사용자 메시지 로깅
    logger.info(f"사용자 {user_name}: {user_message}")
    
    # 일반 메시지 처리
    # "생각 중..." 메시지 표시
    thinking_message = await update.message.reply_text("🤔 생각 중...")
    
    # 날짜/시간 관련 요청 감지
    datetime_keywords = ['날짜', '시간', '날씨', '오늘', '현재', '지금', '시각']
    is_datetime_request = any(keyword in user_message for keyword in datetime_keywords)
    
    if is_datetime_request:
        # 현재 모스크바 시간 가져오기
        moscow_time = datetime.now(MSK)
        current_date = moscow_time.strftime("%Y년 %m월 %d일")
        current_time = moscow_time.strftime("%H시 %M분")
        current_weekday = moscow_time.strftime("%A")
        
        # 요일을 한국어로 변환
        weekday_mapping = {
            'Monday': '월요일',
            'Tuesday': '화요일', 
            'Wednesday': '수요일',
            'Thursday': '목요일',
            'Friday': '금요일',
            'Saturday': '토요일',
            'Sunday': '일요일'
        }
        korean_weekday = weekday_mapping.get(current_weekday, current_weekday)
        
        # 시간 정보를 포함한 프롬프트 생성
        enhanced_message = f"""
현재 정확한 날짜와 시간 정보:
- 날짜: {current_date} ({korean_weekday})
- 시간: {current_time} (모스크바 시간)

사용자 질문: {user_message}

위의 정확한 현재 시간 정보를 바탕으로 답변해주세요. 날씨 정보가 필요한 경우 실시간 날씨 정보는 제공할 수 없다고 안내해주세요.
"""
        response = await chat_with_gemini(enhanced_message)
    else:
        # 일반 메시지 처리
        response = await chat_with_gemini(user_message)
    
    # "생각 중..." 메시지 삭제
    await thinking_message.delete()
    
    # 긴 메시지를 여러 부분으로 나누어서 전송
    message_parts = await split_long_message(response)
    
    for i, part in enumerate(message_parts):
        if i == 0:
            await update.message.reply_text(part)
        else:
            # 연속 메시지임을 표시
            await update.message.reply_text(f"📄 (계속 {i+1}/{len(message_parts)})\n\n{part}")

async def translate_simple_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """간단한 번역 명령어 (/trs)"""
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "사용법: /trs [언어] [텍스트]\n\n"
                "💡 예시:\n"
                "- /trs english 안녕하세요 (또는 /trs en)\n"
                "- /trs russian 좋은 아침이에요 (또는 /trs ru)\n"
                "- /trs korean 감사합니다 (또는 /trs kr)\n\n"
                "⚡ 간단 번역: 최고의 번역만 간략하게 제공\n\n"
                "🌍 지원 언어:\n"
                "- english (en), russian (ru), korean (kr)"
            )
            return
        
        target_language = args[0]
        text_to_translate = " ".join(args[1:])
        
        # "처리 중..." 메시지 표시
        processing_message = await update.message.reply_text("⚡ 간단 번역 중...")
        
        # 언어 매핑 (영어 입력을 한국어로 변환)
        language_mapping = {
            'russian': '러시아어',
            'russia': '러시아어',
            'ru': '러시아어',
            'english': '영어',
            'en': '영어',
            'korean': '한국어',
            'korea': '한국어',
            'kr': '한국어'
        }
        
        # 영어 입력을 한국어로 변환
        korean_language = language_mapping.get(target_language.lower(), target_language)
        
        # 간단한 번역만 요청
        translate_prompt = f"다음 텍스트를 {korean_language}로 최고의 번역만 제공해주세요. 설명이나 추가 정보 없이 가장 자연스러운 번역문만 제공해주세요: {text_to_translate}"
        
        translated_text = await chat_with_gemini(translate_prompt)
        
        # 번역 결과에서 불필요한 부분 제거 (첫 번째 줄만 사용)
        clean_translation = translated_text.split('\n')[0].strip()
        if '**' in clean_translation:
            clean_translation = clean_translation.replace('**', '').strip()
        
        # "처리 중..." 메시지 삭제
        await processing_message.delete()
        
        # 번역 결과 전송
        full_response = f"⚡ 간단 번역 ({korean_language}):\n{clean_translation}"
        await update.message.reply_text(full_response)
                
    except Exception as e:
        logger.error(f"간단 번역 오류: {e}")
        await update.message.reply_text("간단 번역 중 오류가 발생했습니다. 😅")

async def translate_long_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """상세한 번역 명령어 (/trl)"""
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "사용법: /trl [언어] [텍스트]\n\n"
                "💡 예시:\n"
                "- /trl english 안녕하세요 (또는 /trl en)\n"
                "- /trl russian 좋은 아침이에요 (또는 /trl ru)\n"
                "- /trl korean 감사합니다 (또는 /trl kr)\n\n"
                "📚 상세 번역: 여러 번역본, 발음, 문법, 단어 분석까지\n\n"
                "🌍 지원 언어:\n"
                "- english (en), russian (ru), korean (kr)"
            )
            return
        
        target_language = args[0]
        text_to_translate = " ".join(args[1:])
        
        # "처리 중..." 메시지 표시
        processing_message = await update.message.reply_text("📚 상세 번역 중...")
        
        # 언어 매핑 (영어 입력을 한국어로 변환)
        language_mapping = {
            'russian': '러시아어',
            'russia': '러시아어',
            'ru': '러시아어',
            'english': '영어',
            'en': '영어',
            'korean': '한국어',
            'korea': '한국어',
            'kr': '한국어'
        }
        
        # 영어 입력을 한국어로 변환
        korean_language = language_mapping.get(target_language.lower(), target_language)
        
        # 상세한 문법 분석 번역 요청
        if target_language.lower() in ['russian', 'russia', 'ru']:
            translate_prompt = f"""
다음 텍스트를 러시아어로 번역해주세요: {text_to_translate}

다음 형식으로 답변해주세요:

1. 번역:
- 번역 1: (주요 번역)
- 번역 2: (다른 표현)

2. 문법적 설명:
- 문장 구조: (주어, 술어, 목적어 배치)
- 시제: (현재/과거/미래 시제)
- 동사 변화: (인칭변화, 완료/불완료 동사)
- 격변화: (주격, 대격, 여격, 전치격, 조격, 생격 등)
- 명사의 성별: (남성/여성/중성 명사)
- 단수/복수: (명사와 형용사의 단복수 형태)
- 어미변화: (형용사의 성별 일치)

3. 각각의 단어 의미:
- 주요 단어들의 기본형과 의미
- 동사의 원형과 현재 사용된 형태
- 명사의 성별과 격 정보

(모든 답변에서 별표 강조 표시 사용하지 마세요)
"""
        else:
            translate_prompt = f"""
다음 텍스트를 {korean_language}로 번역해주세요: {text_to_translate}

다음 형식으로 답변해주세요:

1. 번역:
- 번역 1: (주요 번역)
- 번역 2: (다른 표현)

2. 문법적 설명:
- 문장 구조: (주어, 술어, 목적어 배치)
- 시제: (현재/과거/미래 시제)
- 동사 변화: (인칭변화, 동사 활용)
- 단수/복수: (명사의 단복수 형태)
- 어순: (언어별 특징적 어순)

3. 각각의 단어 의미:
- 주요 단어들의 기본형과 의미
- 동사의 원형과 현재 사용된 형태

(모든 답변에서 별표 강조 표시 사용하지 마세요)
"""
        
        translated_text = await chat_with_gemini(translate_prompt)
        
        # "처리 중..." 메시지 삭제
        await processing_message.delete()
        
        # 번역 결과 전송 (긴 메시지 처리)
        full_response = f"📚 상세 번역 결과 ({korean_language}):\n\n{translated_text}"
        message_parts = await split_long_message(full_response)
        
        for i, part in enumerate(message_parts):
            if i == 0:
                await update.message.reply_text(part)
            else:
                await update.message.reply_text(f"📄 (계속 {i+1}/{len(message_parts)})\n\n{part}")
                
    except Exception as e:
        logger.error(f"상세 번역 오류: {e}")
        await update.message.reply_text("상세 번역 중 오류가 발생했습니다. 😅")

async def listening_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """한국어/러시아어 음성 변환 명령어"""
    try:
        if not context.args:
            await update.message.reply_text(
                "사용법: /ls [텍스트]\n\n"
                "💡 예시:\n"
                "- /ls 안녕하세요 (한국어)\n"
                "- /ls Привет, как дела? (러시아어)\n"
                "- /ls 좋은 아침이에요 (한국어)\n"
                "- /ls Доброе утро! (러시아어)\n\n"
                "🎵 완전 무료 Google TTS 사용!\n"
                "🌍 자동 언어 감지: 한국어/러시아어"
            )
            return
        
        input_text = " ".join(context.args)
        
        # "변환 중..." 메시지 표시
        processing_message = await update.message.reply_text("🎵 음성 변환 중...")
        
        # 자동 언어 감지로 음성 변환
        audio_data = await convert_text_to_speech(input_text, "auto")
        
        if audio_data:
            # "변환 중..." 메시지 삭제
            await processing_message.delete()
            
            # 언어 감지
            if any('\u3131' <= char <= '\u3163' or '\uac00' <= char <= '\ud7a3' for char in input_text):
                lang_flag = "🇰🇷"
                lang_name = "한국어"
            elif any('\u0400' <= char <= '\u04ff' for char in input_text):
                lang_flag = "🇷🇺"
                lang_name = "러시아어"
            else:
                lang_flag = "🇰🇷"
                lang_name = "한국어 (기본값)"
            
            # 음성 파일 전송
            await update.message.reply_audio(
                audio=audio_data,
                title=f"{lang_name} 음성: {input_text[:50]}...",
                caption=f"{lang_flag} {lang_name} 음성\n📝 텍스트: {input_text}\n🎤 엔진: Google TTS"
            )
        else:
            await processing_message.edit_text("음성 변환 실패. 다시 시도해주세요. 😅")
            
    except Exception as e:
        logger.error(f"TTS 오류: {e}")
        await update.message.reply_text("음성 변환 중 오류가 발생했습니다. 😅")

async def translate_listen_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """간단한 번역 + 음성 변환 명령어"""
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "사용법: /trls [언어] [텍스트]\n\n"
                "💡 예시:\n"
                "- /trls russian 안녕하세요 (또는 /trls ru)\n"
                "- /trls korean 좋은 아침이에요 (또는 /trls kr)\n"
                "- /trls english 감사합니다 (또는 /trls en)\n\n"
                "🎯 간단 번역 + 음성: TTS 최적화된 번역\n"
                "💡 음성 지원: 한국어, 러시아어\n\n"
                "🌍 지원 언어:\n"
                "- korean (kr), russian (ru), english (en)"
            )
            return
        
        target_language = args[0]
        text_to_translate = " ".join(args[1:])
        
        # "처리 중..." 메시지 표시
        processing_message = await update.message.reply_text("🔄 간단 번역 + 음성 변환 중...")
        
        # 언어 매핑 (영어 입력을 한국어로 변환)
        language_mapping = {
            'russian': '러시아어',
            'russia': '러시아어',
            'ru': '러시아어',
            'korean': '한국어',
            'korea': '한국어',
            'kr': '한국어',
            'english': '영어',
            'en': '영어'
        }
        
        # 영어 입력을 한국어로 변환
        korean_language = language_mapping.get(target_language.lower(), target_language)
        
        # 간단한 번역만 요청 (TTS 최적화)
        if target_language.lower() in ['russian', 'russia', 'ru']:
            translate_prompt = f"다음 텍스트를 러시아어로 간단하고 자연스럽게 번역해주세요. 설명이나 추가 정보 없이 번역문만 제공해주세요: {text_to_translate}"
        elif target_language.lower() in ['korean', 'korea', 'kr']:
            translate_prompt = f"다음 텍스트를 한국어로 간단하고 자연스럽게 번역해주세요. 설명이나 추가 정보 없이 번역문만 제공해주세요: {text_to_translate}"
        else:
            translate_prompt = f"다음 텍스트를 {korean_language}로 간단하고 자연스럽게 번역해주세요. 설명이나 추가 정보 없이 번역문만 제공해주세요: {text_to_translate}"
        
        translated_text = await chat_with_gemini(translate_prompt)
        
        # 번역 결과에서 불필요한 부분 제거 (첫 번째 줄만 사용)
        clean_translation = translated_text.split('\n')[0].strip()
        if '**' in clean_translation:
            clean_translation = clean_translation.replace('**', '').strip()
        
        # "처리 중..." 메시지 삭제
        await processing_message.delete()
        
        # 번역 결과 전송
        full_response = f"🌍 간단 번역 ({korean_language}):\n{clean_translation}"
        await update.message.reply_text(full_response)
        
        # 음성 변환 (한국어 또는 러시아어인 경우)
        if target_language.lower() in ['russian', 'russia', 'ru', 'korean', 'korea', 'kr']:
            if target_language.lower() in ['russian', 'russia', 'ru']:
                logger.info("러시아어로 인식됨 - 음성 변환 시작")
                tts_lang = "ru"
                lang_flag = "🇷🇺"
                lang_name = "러시아어"
            else:  # korean
                logger.info("한국어로 인식됨 - 음성 변환 시작")
                tts_lang = "ko"
                lang_flag = "🇰🇷"
                lang_name = "한국어"
            
            # 음성 변환 메시지 표시
            tts_message = await update.message.reply_text("🎵 음성 변환 중...")
            
            # 정리된 번역 텍스트를 음성으로 변환
            audio_data = await convert_text_to_speech(clean_translation, tts_lang)
            
            if audio_data:
                # 음성 변환 메시지 삭제
                await tts_message.delete()
                
                # 음성 파일 전송
                await update.message.reply_audio(
                    audio=audio_data,
                    title=f"{lang_name} 음성: {clean_translation[:50]}...",
                    caption=f"{lang_flag} {lang_name} 음성 (간단 번역+TTS)\n📝 텍스트: {clean_translation}\n🎤 엔진: Google TTS"
                )
            else:
                await tts_message.edit_text("음성 변환 실패. 번역만 완료되었습니다. 😅")
        else:
            await update.message.reply_text("💡 음성 변환은 한국어와 러시아어만 지원합니다!")
            
    except Exception as e:
        logger.error(f"번역+음성 오류: {e}")
        await update.message.reply_text("번역+음성 변환 중 오류가 발생했습니다. 😅")

def main() -> None:
    """봇 시작"""
    # API 키 체크
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN이 설정되지 않았습니다!")
        return
    
    # 애플리케이션 생성
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 명령어 등록
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("trs", translate_simple_command))
    application.add_handler(CommandHandler("trl", translate_long_command))
    application.add_handler(CommandHandler("ls", listening_command))
    application.add_handler(CommandHandler("trls", translate_listen_command))
    
    # 모든 텍스트 메시지 처리 (명령어가 아닌 경우)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 봇 시작
    logger.info("🤖 봇 시작!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 