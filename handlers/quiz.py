import random
import logging
from typing import Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config.settings import QUIZ_CATEGORIES, EMOJIS
from utils.data_utils import UserManager, QuizManager, load_vocabulary_data
from services.gemini_service import gemini_service

logger = logging.getLogger(__name__)

class QuizSession:
    """퀴즈 세션 관리"""
    active_sessions = {}  # chat_id: quiz_data

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """퀴즈 메인 메뉴"""
    user = UserManager.get_user(update.effective_chat.id)
    
    # 사용량 체크
    can_use, current, limit = UserManager.check_usage_limit(update.effective_chat.id, 'quiz_attempts')
    if not can_use:
        await update.message.reply_text(
            f"❌ 오늘의 퀴즈 횟수를 모두 사용했습니다. ({current}/{limit})\n"
            "💎 Pro 플랜으로 업그레이드하면 무제한 이용 가능합니다! /premium"
        )
        return
    
    # 퀴즈 카테고리 선택 키보드
    keyboard = []
    for category_id, category_data in QUIZ_CATEGORIES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{category_data['emoji']} {category_data['name']}", 
                callback_data=f"quiz_{category_id}"
            )
        ])
    
    keyboard.extend([
        [InlineKeyboardButton("🎲 랜덤 퀴즈", callback_data="quiz_random")],
        [InlineKeyboardButton("🏆 내 점수 기록", callback_data="quiz_scores")],
        [InlineKeyboardButton("📊 퀴즈 랭킹", callback_data="quiz_leaderboard")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 사용자 통계
    stats = user['stats']
    quiz_scores = stats.get('quiz_scores', [])
    avg_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
    
    message_text = f"""
{EMOJIS['trophy']} **러시아어 퀴즈**

🎯 **당신의 기록**
• 평균 점수: {avg_score:.1f}점
• 도전 횟수: {len(quiz_scores)}회
• 오늘 남은 횟수: {limit - current if limit != -1 else '무제한'}

🧠 **퀴즈 카테고리를 선택하세요:**
"""
    
    await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

async def quiz_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """퀴즈 콜백 처리"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.from_user.id
    data = query.data
    
    if data.startswith("quiz_"):
        category = data.replace("quiz_", "")
        
        if category == "random":
            category = random.choice(list(QUIZ_CATEGORIES.keys()))
        elif category == "scores":
            await show_quiz_scores(query, chat_id)
            return
        elif category == "leaderboard":
            await show_quiz_leaderboard(query)
            return
        
        await start_quiz(query, chat_id, category)
    
    elif data.startswith("answer_"):
        await handle_quiz_answer(query, chat_id, data)

async def start_quiz(query, chat_id: int, category: str) -> None:
    """퀴즈 시작"""
    # 사용량 증가
    UserManager.increment_usage(chat_id, 'quiz_attempts')
    
    # 퀴즈 생성
    if category == "vocabulary":
        quiz = QuizManager.generate_vocabulary_quiz()
    else:
        # AI로 문법/발음 퀴즈 생성
        quiz = await generate_ai_quiz(category)
    
    if not quiz:
        await query.edit_message_text("❌ 퀴즈 생성에 실패했습니다. 다시 시도해주세요.")
        return
    
    # 세션 저장
    QuizSession.active_sessions[chat_id] = {
        'category': category,
        'quiz': quiz,
        'start_time': query.message.date
    }
    
    # 선택지 키보드 생성
    keyboard = []
    for i, option in enumerate(quiz['options']):
        keyboard.append([
            InlineKeyboardButton(
                f"{chr(65+i)}) {option}", 
                callback_data=f"answer_{i}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ 퀴즈 그만하기", callback_data="quiz_quit")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    category_info = QUIZ_CATEGORIES[category]
    
    quiz_text = f"""
{category_info['emoji']} **{category_info['name']}**

❓ **문제:**
{quiz['question']}

{EMOJIS['info']} 정답을 선택하세요:
"""
    
    await query.edit_message_text(quiz_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_quiz_answer(query, chat_id: int, answer_data: str) -> None:
    """퀴즈 답변 처리"""
    if chat_id not in QuizSession.active_sessions:
        await query.edit_message_text("❌ 활성화된 퀴즈가 없습니다.")
        return
    
    session = QuizSession.active_sessions[chat_id]
    quiz = session['quiz']
    
    # 답변 처리
    if answer_data == "quiz_quit":
        del QuizSession.active_sessions[chat_id]
        await query.edit_message_text("퀴즈를 종료했습니다. 다음에 또 도전해보세요! 👋")
        return
    
    answer_index = int(answer_data.replace("answer_", ""))
    user_answer = quiz['options'][answer_index]
    is_correct = QuizManager.check_answer(user_answer, quiz['correct_answer'])
    
    # 점수 계산
    score = 100 if is_correct else 0
    
    # 사용자 통계 업데이트
    users = UserManager.load_user_data()
    user_id = str(chat_id)
    if user_id in users:
        users[user_id]['stats']['quiz_scores'].append(score)
        UserManager.save_user_data(users)
    
    # 결과 메시지
    if is_correct:
        result_emoji = EMOJIS['success']
        result_text = "정답입니다!"
        experience_gain = 10
    else:
        result_emoji = EMOJIS['error']
        result_text = f"틀렸습니다. 정답: {quiz['correct_answer']}"
        experience_gain = 2
    
    # 경험치 추가
    UserManager.update_user_stats(chat_id, 'total_exp', experience_gain)
    
    # 추가 정보
    extra_info = ""
    if 'pronunciation' in quiz and quiz['pronunciation']:
        extra_info += f"🗣️ 발음: {quiz['pronunciation']}\n"
    if 'explanation' in quiz and quiz['explanation']:
        extra_info += f"💡 설명: {quiz['explanation']}\n"
    
    result_message = f"""
{result_emoji} **{result_text}**

{extra_info}

📊 **획득 점수:** {score}점
⭐ **경험치:** +{experience_gain} EXP

🎯 **다음 행동:**
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 다른 퀴즈 도전", callback_data=f"quiz_{session['category']}")],
        [InlineKeyboardButton("🏠 퀴즈 메뉴로", callback_data="quiz_menu")],
        [InlineKeyboardButton("📊 내 점수 보기", callback_data="quiz_scores")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(result_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    # 세션 종료
    del QuizSession.active_sessions[chat_id]

async def generate_ai_quiz(category: str) -> Dict[str, Any]:
    """AI로 퀴즈 생성"""
    try:
        difficulty = "medium"  # 나중에 사용자 설정으로 변경 가능
        
        if category == "grammar":
            prompt = f"""
러시아어 문법 퀴즈를 만들어주세요. 난이도: {difficulty}

다음 JSON 형식으로 답변해주세요:
{{
    "question": "문제 내용",
    "options": ["선택지1", "선택지2", "선택지3", "선택지4"],
    "correct_answer": "정답",
    "explanation": "정답 설명"
}}

예시 주제: 격변화, 동사활용, 형용사 활용 등
"""
        elif category == "pronunciation":
            prompt = f"""
러시아어 발음 퀴즈를 만들어주세요. 난이도: {difficulty}

다음 JSON 형식으로 답변해주세요:
{{
    "question": "다음 단어의 올바른 발음은?",
    "options": ["발음1", "발음2", "발음3", "발음4"],
    "correct_answer": "정답 발음",
    "explanation": "발음 설명"
}}

실제 러시아어 단어를 사용해주세요.
"""
        
        response = await gemini_service.generate_content(prompt)
        
        # JSON 파싱
        import json
        quiz_data = json.loads(response)
        quiz_data['category'] = category
        
        return quiz_data
        
    except Exception as e:
        logger.error(f"AI 퀴즈 생성 오류: {e}")
        return None

async def show_quiz_scores(query, chat_id: int) -> None:
    """퀴즈 점수 기록 표시"""
    user = UserManager.get_user(chat_id)
    quiz_scores = user['stats'].get('quiz_scores', [])
    
    if not quiz_scores:
        score_text = "아직 퀴즈 기록이 없습니다. 첫 퀴즈에 도전해보세요!"
    else:
        total_quizzes = len(quiz_scores)
        avg_score = sum(quiz_scores) / total_quizzes
        best_score = max(quiz_scores)
        perfect_count = quiz_scores.count(100)
        
        # 최근 5개 점수
        recent_scores = quiz_scores[-5:]
        recent_text = " → ".join([str(score) for score in recent_scores])
        
        score_text = f"""
📊 **퀴즈 성적표**

📈 **전체 통계**
• 총 도전 횟수: {total_quizzes}회
• 평균 점수: {avg_score:.1f}점
• 최고 점수: {best_score}점
• 만점 횟수: {perfect_count}회

📉 **최근 5회 점수**
{recent_text}

🏆 **성취도**
{get_quiz_achievement(avg_score, perfect_count)}
"""
    
    keyboard = [
        [InlineKeyboardButton("🎯 새 퀴즈 도전", callback_data="quiz_vocabulary")],
        [InlineKeyboardButton("🔙 퀴즈 메뉴로", callback_data="quiz_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(score_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_quiz_leaderboard(query) -> None:
    """퀴즈 랭킹 표시"""
    users = UserManager.load_user_data()
    
    # 사용자별 평균 점수 계산
    user_averages = []
    for user_id, user_data in users.items():
        quiz_scores = user_data['stats'].get('quiz_scores', [])
        if quiz_scores:
            avg_score = sum(quiz_scores) / len(quiz_scores)
            total_quizzes = len(quiz_scores)
            user_averages.append({
                'user_id': user_id,
                'avg_score': avg_score,
                'total_quizzes': total_quizzes,
                'level': user_data['stats'].get('level', 1)
            })
    
    # 평균 점수로 정렬
    user_averages.sort(key=lambda x: x['avg_score'], reverse=True)
    
    leaderboard_text = f"{EMOJIS['trophy']} **퀴즈 랭킹 TOP 10**\n\n"
    
    for i, user_info in enumerate(user_averages[:10]):
        rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}️⃣"
        
        leaderboard_text += f"{rank_emoji} **{user_info['avg_score']:.1f}점** "
        leaderboard_text += f"(Lv.{user_info['level']}, {user_info['total_quizzes']}회)\n"
    
    if not user_averages:
        leaderboard_text = "아직 랭킹 데이터가 없습니다. 첫 번째 도전자가 되어보세요!"
    
    keyboard = [
        [InlineKeyboardButton("🎯 퀴즈 도전하기", callback_data="quiz_vocabulary")],
        [InlineKeyboardButton("🔙 퀴즈 메뉴로", callback_data="quiz_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(leaderboard_text, reply_markup=reply_markup, parse_mode='Markdown')

def get_quiz_achievement(avg_score: float, perfect_count: int) -> str:
    """성취도 배지 반환"""
    if avg_score >= 90:
        return f"{EMOJIS['crown']} 퀴즈 마스터"
    elif avg_score >= 80:
        return f"{EMOJIS['trophy']} 퀴즈 전문가"
    elif avg_score >= 70:
        return f"{EMOJIS['medal']} 퀴즈 고수"
    elif avg_score >= 60:
        return f"{EMOJIS['star']} 퀴즈 도전자"
    else:
        return f"{EMOJIS['fire']} 퀴즈 새내기"

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """전체 리더보드 명령어"""
    users = UserManager.load_user_data()
    
    # 여러 카테고리별 랭킹
    rankings = {
        'level': [],
        'exp': [],
        'quests': [],
        'quiz_avg': []
    }
    
    for user_id, user_data in users.items():
        stats = user_data['stats']
        quiz_scores = stats.get('quiz_scores', [])
        
        rankings['level'].append({
            'value': stats.get('level', 1),
            'user_id': user_id
        })
        
        rankings['exp'].append({
            'value': stats.get('total_exp', 0),
            'user_id': user_id
        })
        
        rankings['quests'].append({
            'value': stats.get('quests_completed', 0),
            'user_id': user_id
        })
        
        if quiz_scores:
            rankings['quiz_avg'].append({
                'value': sum(quiz_scores) / len(quiz_scores),
                'user_id': user_id
            })
    
    # 정렬
    for category in rankings:
        rankings[category].sort(key=lambda x: x['value'], reverse=True)
    
    leaderboard_text = f"""
{EMOJIS['trophy']} **종합 리더보드**

🔰 **레벨 랭킹**
"""
    
    for i, user in enumerate(rankings['level'][:5]):
        rank_emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i]
        leaderboard_text += f"{rank_emoji} 레벨 {user['value']}\n"
    
    leaderboard_text += f"""

⭐ **경험치 랭킹**
"""
    
    for i, user in enumerate(rankings['exp'][:5]):
        rank_emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i]
        leaderboard_text += f"{rank_emoji} {user['value']:,} EXP\n"
    
    keyboard = [
        [InlineKeyboardButton("🎯 퀴즈 랭킹", callback_data="quiz_leaderboard")],
        [InlineKeyboardButton("📊 내 통계", callback_data="my_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(leaderboard_text, reply_markup=reply_markup, parse_mode='Markdown') 