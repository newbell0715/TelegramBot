import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config.settings import EMOJIS
from utils.data_utils import UserManager

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """시작 명령어 - 대폭 업그레이드된 버전"""
    user = update.effective_user
    chat_id = user.id
    user_data = UserManager.get_user(chat_id)
    
    # 신규/기존 사용자 구분
    is_new_user = user_data['stats']['quests_completed'] == 0
    
    # 개인화된 인사말
    if is_new_user:
        greeting = f"🎉 안녕하세요, {user.first_name}님!"
        welcome_text = "저는 당신만의 러시아어 학습 파트너, **'루샤(Rusya)'**입니다."
        encouragement = "함께 러시아어 정복을 시작해볼까요? 🚀"
    else:
        level = user_data['stats'].get('level', 1)
        streak = user_data['stats'].get('streak_days', 0)
        greeting = f"👋 다시 만나서 반가워요, {user.first_name}님!"
        welcome_text = f"레벨 {level} 학습자님, 오늘도 함께 성장해봅시다!"
        encouragement = f"🔥 연속 {streak}일째 학습 중! 대단해요!"
    
    # 메인 기능 소개
    main_features = f"""
**🌟 핵심 기능**
{EMOJIS['fire']} `/quest` - 실전 회화 퀘스트 (게임처럼!)
✍️ `/write` - AI 작문 교정 (점수 매김!)
🧠 `/quiz` - 재미있는 퀴즈 도전
📊 `/stats` - 나의 학습 진도 확인

**💬 똑똑한 AI 기능**
🤖 일반 채팅 - 명령어 없이 대화하세요!
🌍 `/trs` - 간단 번역 | `/trl` - 상세 번역
🎵 `/ls` - 음성 변환 | `/trls` - 번역+음성

**🎯 게임화 요소**
🏆 `/leaderboard` - 전체 랭킹
🔥 연속 학습일 추적
⭐ 경험치 & 레벨 시스템
🎖️ 성취 배지 컬렉션
"""
    
    # 플랜별 추가 정보
    plan_info = ""
    if user_data['plan'] == 'Free':
        plan_info = f"""
💎 **더 많은 기능이 필요하신가요?**
`/premium` - Pro/Premium 플랜 보기
• 무제한 사용 • 고급 기능 • 우선 지원
"""
    else:
        plan_info = f"✨ **{user_data['plan']} 사용자님께 감사드립니다!**"
    
    # 인라인 키보드
    keyboard = []
    if is_new_user:
        keyboard.extend([
            [InlineKeyboardButton("🎮 첫 퀘스트 시작", callback_data="start_first_quest")],
            [InlineKeyboardButton("📚 사용법 배우기", callback_data="tutorial")]
        ])
    else:
        keyboard.extend([
            [InlineKeyboardButton("🎯 퀴즈 도전", callback_data="quiz_vocabulary")],
            [InlineKeyboardButton("📊 내 통계", callback_data="my_stats")]
        ])
    
    keyboard.extend([
        [InlineKeyboardButton("💎 프리미엄", callback_data="upgrade_pro_monthly"), 
         InlineKeyboardButton("💝 후원하기", callback_data="donate")],
        [InlineKeyboardButton("❓ 도움말", callback_data="help_menu")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 최종 메시지 조합
    message_text = f"""
{greeting}

{welcome_text}

{main_features}

{plan_info}

{encouragement}

💡 **시작하려면 아래 버튼을 눌러보세요!**
"""
    
    await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """도움말 명령어 - 카테고리별 정리"""
    help_categories = {
        "🎮 학습 & 게임": [
            ("🎯 /quest", "스토리 기반 실전 회화 퀘스트"),
            ("⚔️ /action [문장]", "퀘스트에서 행동하기"),
            ("🧠 /quiz", "다양한 러시아어 퀴즈 도전"),
            ("✍️ /write [문장]", "AI가 러시아어 작문 교정"),
            ("📊 /stats", "상세한 학습 통계 & 진도")
        ],
        "🌍 번역 & 음성": [
            ("⚡ /trs [언어] [텍스트]", "간단 번역"),
            ("📚 /trl [언어] [텍스트]", "상세 번역 (문법 분석)"),
            ("🎵 /ls [텍스트]", "텍스트를 음성으로 변환"),
            ("🎯 /trls [언어] [텍스트]", "번역 + 음성 변환")
        ],
        "🏆 순위 & 소셜": [
            ("🏆 /leaderboard", "전체 사용자 랭킹"),
            ("📈 /my_progress", "나의 학습 성과 리포트"),
            ("💭 /feedback [의견]", "봇 개선 의견 보내기")
        ],
        "💎 프리미엄": [
            ("💎 /premium", "Pro/Premium 플랜 안내"),
            ("💝 /donate", "개발자 후원하기"),
            ("🔔 /subscribe_daily", "매일 학습 자료 받기")
        ],
        "🔧 시스템": [
            ("🤖 /model_status", "AI 모델 상태 확인"),
            ("📊 /admin_stats", "관리자 통계 (관리자만)"),
            ("❓ /help", "이 도움말 다시 보기")
        ]
    }
    
    help_text = f"""
{EMOJIS['info']} **'루샤' 봇 완전 가이드**

💬 **AI 채팅**: 명령어 없이 바로 대화하세요!
예: "안녕" / "러시아어로 안녕은 뭐야?" / "오늘 기분이 좋아"

"""
    
    for category, commands in help_categories.items():
        help_text += f"\n**{category}**\n"
        for command, description in commands:
            help_text += f"• {command} - {description}\n"
    
    help_text += f"""

{EMOJIS['fire']} **꿀팁**
• 모든 명령어는 한국어와 러시아어 모두 지원
• Pro 플랜은 모든 기능 무제한 사용
• 매일 학습하면 연속일 배지 획득
• 퀴즈 점수는 리더보드에 반영

🆘 **문제가 있나요?**
/feedback으로 언제든 문의하세요!
"""
    
    # 도움말 키보드
    keyboard = [
        [InlineKeyboardButton("🎮 퀘스트 시작", callback_data="quest_easy_cafe")],
        [InlineKeyboardButton("🧠 퀴즈 도전", callback_data="quiz_vocabulary")],
        [InlineKeyboardButton("💎 프리미엄 보기", callback_data="upgrade_pro_monthly")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

async def tutorial_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """튜토리얼 핸들러"""
    query = update.callback_query
    await query.answer()
    
    tutorial_text = f"""
🎓 **빠른 시작 가이드**

**1단계: 첫 퀘스트 도전** 🎮
`/quest` → 카페에서 주문하기 퀘스트 시작
`/action [러시아어 문장]`으로 대답하기

**2단계: AI와 대화하기** 💬
명령어 없이 "안녕"이라고 말해보세요!
AI가 자연스럽게 대답해드려요.

**3단계: 작문 교정 받기** ✍️
`/write Привет, как дела?`
AI가 문법을 확인하고 점수를 매겨줘요.

**4단계: 퀴즈 도전하기** 🧠
`/quiz` → 재미있는 러시아어 퀴즈
점수는 리더보드에 기록돼요!

**5단계: 번역하기** 🌍
`/trs russian 안녕하세요` (간단 번역)
`/trl russian 안녕하세요` (상세 번역)

{EMOJIS['star']} **이제 시작할 준비가 됐어요!**
"""
    
    keyboard = [
        [InlineKeyboardButton("🎮 첫 퀘스트 시작", callback_data="start_first_quest")],
        [InlineKeyboardButton("🏠 메인으로", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(tutorial_text, reply_markup=reply_markup, parse_mode='Markdown')

# 추가 콜백 핸들러들이 필요하지만, 이미 main.py에서 처리되고 있음 