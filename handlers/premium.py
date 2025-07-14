import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes, CallbackQueryHandler

from config.settings import PLANS, PRICES, EMOJIS, ADMIN_USER_IDS
from utils.data_utils import UserManager

logger = logging.getLogger(__name__)

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """프리미엄 플랜 소개"""
    user = UserManager.get_user(update.effective_chat.id)
    current_plan = user['plan']
    
    # 플랜별 정보 생성
    plan_info = ""
    for plan_name, plan_data in PLANS.items():
        emoji = "✅" if plan_name == current_plan else "⭐"
        features = "\n".join([f"  • {feature}" for feature in plan_data['features']])
        
        plan_info += f"""
{emoji} **{plan_name} 플랜**
{features}

"""
    
    # 가격 정보
    price_info = f"""
💰 **요금 안내**
• Pro 월간: {PRICES['pro_monthly']:,}원/월
• Pro 연간: {PRICES['pro_yearly']:,}원/년 (월 {PRICES['pro_yearly']//12:,}원)
• Premium 월간: {PRICES['premium_monthly']:,}원/월  
• Premium 연간: {PRICES['premium_yearly']:,}원/년 (월 {PRICES['premium_yearly']//12:,}원)
"""
    
    # 키보드 생성
    keyboard = []
    if current_plan == 'Free':
        keyboard.extend([
            [InlineKeyboardButton("🌟 Pro 월간 구독", callback_data="upgrade_pro_monthly")],
            [InlineKeyboardButton("💎 Premium 월간 구독", callback_data="upgrade_premium_monthly")],
            [InlineKeyboardButton("📊 플랜 비교", callback_data="compare_plans")]
        ])
    else:
        keyboard.extend([
            [InlineKeyboardButton("📊 현재 플랜 상세", callback_data="plan_details")],
            [InlineKeyboardButton("🔄 플랜 변경", callback_data="change_plan")]
        ])
    
    keyboard.append([InlineKeyboardButton("❓ 자주 묻는 질문", callback_data="premium_faq")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = f"""
{EMOJIS['crown']} **프리미엄 플랜 안내**

현재 플랜: **{current_plan}**

{plan_info}

{price_info}

{EMOJIS['fire']} **지금 업그레이드하면:**
• 첫 7일 무료 체험
• 언제든 취소 가능
• 즉시 모든 기능 이용
"""
    
    await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

async def upgrade_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """업그레이드 콜백 처리"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.from_user.id
    
    if data.startswith("upgrade_"):
        plan_type = data.replace("upgrade_", "")
        await start_payment_process(query, plan_type)
    
    elif data == "compare_plans":
        await show_plan_comparison(query)
    
    elif data == "premium_faq":
        await show_premium_faq(query)
    
    elif data == "plan_details":
        await show_plan_details(query, chat_id)

async def start_payment_process(query, plan_type: str) -> None:
    """결제 프로세스 시작"""
    prices = {
        "pro_monthly": LabeledPrice("Pro 월간", PRICES['pro_monthly'] * 100),  # 텔레그램은 코펙 단위
        "premium_monthly": LabeledPrice("Premium 월간", PRICES['premium_monthly'] * 100),
        "pro_yearly": LabeledPrice("Pro 연간", PRICES['pro_yearly'] * 100),
        "premium_yearly": LabeledPrice("Premium 연간", PRICES['premium_yearly'] * 100)
    }
    
    if plan_type not in prices:
        await query.edit_message_text("❌ 잘못된 플랜 선택입니다.")
        return
    
    # 결제 설명
    plan_names = {
        "pro_monthly": "Pro 월간 구독",
        "premium_monthly": "Premium 월간 구독", 
        "pro_yearly": "Pro 연간 구독",
        "premium_yearly": "Premium 연간 구독"
    }
    
    description = f"""
{plan_names[plan_type]} 업그레이드

✅ 7일 무료 체험
✅ 언제든 취소 가능
✅ 즉시 모든 프리미엄 기능 이용
"""
    
    # 실제 결제는 Payment Provider Token이 필요
    # 현재는 결제 안내만 표시
    keyboard = [
        [InlineKeyboardButton("💳 카카오페이로 결제", url="https://pay.kakao.com")],
        [InlineKeyboardButton("💳 토스페이로 결제", url="https://toss.me")],
        [InlineKeyboardButton("🔙 뒤로가기", callback_data="back_to_premium")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💳 **결제 안내**\n\n{description}\n\n"
        "아래 링크를 통해 결제를 진행해주세요.\n"
        "결제 완료 후 /activate 명령어로 계정을 활성화하세요.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_plan_comparison(query) -> None:
    """플랜 비교 표시"""
    comparison = """
📊 **플랜 상세 비교**

🆓 **Free 플랜**
• 일일 교정: 5회
• 일일 번역: 10회
• 일일 TTS: 5회
• 퀴즈: 3회/일
• 기본 퀘스트

🌟 **Pro 플랜**
• 무제한 교정
• 무제한 번역
• 무제한 TTS
• 무제한 퀴즈
• 고급 퀘스트
• 개인화 학습
• 상세 통계

💎 **Premium 플랜**  
• Pro 모든 기능
• AI 실시간 채팅
• 음성 인식
• 개인 튜터 모드
• 1:1 지원
• 우선 처리
"""
    
    keyboard = [[InlineKeyboardButton("🔙 뒤로가기", callback_data="back_to_premium")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(comparison, reply_markup=reply_markup, parse_mode='Markdown')

async def show_premium_faq(query) -> None:
    """프리미엄 FAQ"""
    faq = """
❓ **자주 묻는 질문**

**Q: 무료 체험이 있나요?**
A: 네! 모든 유료 플랜은 7일 무료 체험이 제공됩니다.

**Q: 언제든 취소할 수 있나요?** 
A: 네, 언제든 /cancel 명령어로 구독을 취소할 수 있습니다.

**Q: 결제는 어떻게 하나요?**
A: 카카오페이, 토스페이를 지원합니다.

**Q: 환불이 가능한가요?**
A: 7일 체험 기간 내 취소 시 100% 환불됩니다.

**Q: Pro와 Premium의 차이는?**
A: Premium은 Pro 기능 + AI 실시간 채팅 + 1:1 지원이 추가됩니다.

**Q: 학생 할인이 있나요?**
A: 학생증 인증 시 30% 할인 혜택을 드립니다. /student로 신청하세요.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 뒤로가기", callback_data="back_to_premium")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(faq, reply_markup=reply_markup, parse_mode='Markdown')

async def show_plan_details(query, chat_id: int) -> None:
    """현재 플랜 상세 정보"""
    user = UserManager.get_user(chat_id)
    plan = user['plan']
    
    usage = user.get('usage', {})
    plan_limits = PLANS[plan]
    
    # 사용량 정보
    usage_info = ""
    for usage_type in ['corrections', 'translations', 'tts_calls', 'quiz_attempts']:
        current = usage.get(usage_type, 0)
        limit = plan_limits.get(f'daily_{usage_type}', 0)
        
        if limit == -1:
            usage_info += f"• {usage_type}: {current} (무제한)\n"
        else:
            usage_info += f"• {usage_type}: {current}/{limit}\n"
    
    details = f"""
📋 **현재 플랜 상세**

플랜: **{plan}**
가입일: {user['stats'].get('start_date', 'N/A')[:10]}

📊 **오늘 사용량**
{usage_info}

🎯 **사용 가능한 기능**
{chr(10).join([f"• {feature}" for feature in plan_limits['features']])}
"""
    
    keyboard = []
    if plan == 'Free':
        keyboard.append([InlineKeyboardButton("⬆️ 업그레이드", callback_data="upgrade_pro_monthly")])
    
    keyboard.append([InlineKeyboardButton("🔙 뒤로가기", callback_data="back_to_premium")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(details, reply_markup=reply_markup, parse_mode='Markdown')

async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """후원 기능"""
    donate_text = f"""
{EMOJIS['gem']} **후원하기**

안녕하세요! '루샤' 봇을 사용해주셔서 감사합니다.

더 나은 서비스를 위해 여러분의 후원이 큰 힘이 됩니다!

💝 **후원 혜택**
• 따뜻한 마음 + 좋은 일 한 기분
• 더 나은 AI 모델 사용 가능
• 새로운 기능 개발 지원
• 후원자 전용 배지 획득

☕ **커피 한 잔 값 후원**
작은 후원도 큰 의미가 됩니다!
"""
    
    keyboard = [
        [InlineKeyboardButton("☕ 3,000원 후원", url="https://toss.me/rusya/3000")],
        [InlineKeyboardButton("🍔 5,000원 후원", url="https://toss.me/rusya/5000")],
        [InlineKeyboardButton("🍕 10,000원 후원", url="https://toss.me/rusya/10000")],
        [InlineKeyboardButton("💝 자유 금액 후원", url="https://toss.me/rusya")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        donate_text, 
        reply_markup=reply_markup, 
        parse_mode='Markdown'
    )

async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """관리자용 통계 (관리자만 사용 가능)"""
    if update.effective_user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    
    users = UserManager.load_user_data()
    
    # 기본 통계
    total_users = len(users)
    active_today = sum(1 for user in users.values() 
                      if user['stats']['last_active_date'][:10] == datetime.now().strftime('%Y-%m-%d'))
    
    plan_counts = {'Free': 0, 'Pro': 0, 'Premium': 0}
    for user in users.values():
        plan = user.get('plan', 'Free')
        plan_counts[plan] += 1
    
    stats_text = f"""
📊 **관리자 통계**

👥 **사용자**
• 총 사용자: {total_users}명
• 오늘 활성: {active_today}명

💎 **플랜 분포**
• Free: {plan_counts['Free']}명
• Pro: {plan_counts['Pro']}명  
• Premium: {plan_counts['Premium']}명

📈 **활동**
• 총 퀘스트 완료: {sum(user['stats'].get('quests_completed', 0) for user in users.values())}
• 총 문장 교정: {sum(user['stats'].get('sentences_corrected', 0) for user in users.values())}
"""
    
    await update.message.reply_text(stats_text, parse_mode='Markdown') 