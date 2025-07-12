from telegram import Update
from telegram.ext import ContextTypes
from utils.data_utils import get_user

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """봇 시작 메시지"""
    user = update.effective_user
    chat_id = user.id
    get_user(chat_id)
    
    await update.message.reply_text(
        f"🎉 안녕하세요, {user.first_name}님!\n"
        "저는 당신만의 러시아어 학습 트레이너, '루샤(Rusya)'입니다.\n\n"
        "단순 번역기를 넘어, 실제 상황처럼 대화하고, 작문을 교정하며, 꾸준히 학습할 수 있도록 제가 함께할게요!\n\n"
        "**주요 기능:**\n"
        "🇷🇺 `/quest` - 스토리 기반 퀘스트로 실전 회화 배우기\n"
        "✍️ `/write [문장]` - AI가 직접 러시아어 작문을 교정\n"
        "📈 `/my_progress` - 나의 주간 학습 성과 확인하기\n"
        "🔔 `/subscribe_daily` - 매일 아침 학습 콘텐츠 받아보기\n"
        "⚡ `/trs [언어] [텍스트]` - 간단한 번역\n"
        "📚 `/trl [언어] [텍스트]` - 상세한 번역 (문법 분석 포함)\n"
        "🎵 `/ls [텍스트]` - 음성 변환\n"
        "🌍 `/trls [언어] [텍스트]` - 번역 + 음성\n\n"
        "자, 이제 저와 함께 러시아어 정복을 시작해볼까요?\n"
        "먼저 `/quest`를 입력해서 첫 번째 임무를 시작해보세요!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """도움말 메시지"""
    help_text = """
    🤖 **'루샤' 봇 사용법 안내** 🤖

    **🇷🇺 핵심 학습 기능**
    - `/quest` - 스토리 기반 퀘스트를 시작하거나 현재 상태를 봅니다.
    - `/action [문장]` - 퀘스트 진행을 위해 행동(대답)을 입력합니다.
    - `/write [러시아어 문장]` - AI가 문법과 표현을 교정해줍니다.
    - `/my_progress` - 주간 학습 통계를 확인하고 피드백을 받습니다.

    **🌍 번역 & TTS 기능**
    - `/trs [언어] [텍스트]` - 간단 번역 (최고의 번역만)
    - `/trl [언어] [텍스트]` - 상세 번역 (문법, 단어 분석)
    - `/ls [텍스트]` - 한국어/러시아어 음성 듣기 🎵
    - `/trls [언어] [텍스트]` - 간단 번역 + 음성 🎯

    **🔔 구독 및 알림**
    - `/subscribe_daily` - 매일 아침 학습 콘텐츠 구독을 시작합니다.
    - `/unsubscribe_daily` - 매일 학습 콘텐츠 구독을 중지합니다.

    **⚙️ 기타 명령어**
    - `/start` - 봇 시작 및 초기화
    - `/help` - 이 도움말을 다시 봅니다.
    
    **💡 팁:**
    퀘스트가 막히면 `/quest`를 다시 입력해 현재 상황 설명을 다시 확인해보세요!

    **🌍 지원 언어:**
    - english (en), russian (ru), korean (kr)

    **🎵 TTS 지원 언어:**
    - 한국어 🇰🇷, 러시아어 🇷🇺

    **🚀 24/7 서비스 중!**
    """
    await update.message.reply_text(help_text) 