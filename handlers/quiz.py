from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random
import json
from utils.data_utils import UserManager, QuizManager
from services.gemini_service import call_gemini_api
from config.settings import QUIZ_CATEGORIES
import logging

logger = logging.getLogger(__name__)

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """퀴즈 메인 명령어 - 카테고리 선택 또는 사용법 안내"""
    args = context.args
    chat_id = update.effective_chat.id
    
    if not args:
        # 퀴즈 카테고리 선택 메뉴
        keyboard = []
        for category_id, category_data in QUIZ_CATEGORIES.items():
            keyboard.append([InlineKeyboardButton(
                f"{category_data['emoji']} {category_data['name']}", 
                callback_data=f"quiz_{category_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("📊 내 퀴즈 기록", callback_data="quiz_history")])
        keyboard.append([InlineKeyboardButton("🏅 리더보드", callback_data="leaderboard")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🧠 **러시아어 퀴즈에 오신 것을 환영합니다!** 🧠\n\n"
            "📚 **퀴즈 종류:**\n"
            "• 📚 **단어 퀴즈** - 러시아어 단어의 뜻 맞추기\n"
            "• 📝 **문법 퀴즈** - 문법 규칙과 활용 테스트\n"
            "• 🗣️ **발음 퀴즈** - 올바른 발음 선택하기\n\n"
            "🎯 **퀴즈 특징:**\n"
            "✅ 무제한 도전 가능\n"
            "✅ 실시간 점수 계산\n"
            "✅ 상세한 해설 제공\n"
            "✅ 경험치 및 레벨 시스템\n"
            "✅ 리더보드 경쟁\n\n"
            "🏆 **보상 시스템:**\n"
            "• 정답 1개 = +2 EXP\n"
            "• 퀴즈 완료 = 추가 보너스\n\n"
            "원하는 퀴즈 카테고리를 선택해주세요:",
            reply_markup=reply_markup
        )
        return
    
    # 직접 카테고리 지정한 경우
    category = args[0].lower()
    if category in QUIZ_CATEGORIES:
        await start_quiz(update, context, category)
    else:
        await update.message.reply_text(
            "❌ **잘못된 카테고리입니다.**\n\n"
            "📚 **사용 가능한 카테고리:**\n"
            "• `vocabulary` - 단어 퀴즈\n"
            "• `grammar` - 문법 퀴즈\n"
            "• `pronunciation` - 발음 퀴즈\n\n"
            "**사용법:** `/quiz [카테고리]`\n"
            "**예시:** `/quiz vocabulary`\n\n"
            "또는 `/quiz`만 입력하면 선택 메뉴가 나타납니다."
        )

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, questions_count: int = 5) -> None:
    """퀴즈 시작"""
    chat_id = update.effective_chat.id
    user = UserManager.get_user(chat_id)
    
    # 퀴즈 데이터 생성
    if category == 'vocabulary':
        quiz_data = await generate_vocabulary_quiz(questions_count)
    elif category == 'grammar':
        quiz_data = await generate_grammar_quiz(questions_count)
    elif category == 'pronunciation':
        quiz_data = await generate_pronunciation_quiz(questions_count)
    else:
        await update.message.reply_text("❌ 지원하지 않는 퀴즈 카테고리입니다.")
        return
    
    if not quiz_data:
        await update.message.reply_text(
            "😅 **퀴즈 생성 중 오류가 발생했습니다.**\n\n"
            "잠시 후 다시 시도해주세요."
        )
        return
    
    # 퀴즈 세션 저장
    context.user_data['current_quiz'] = {
        'category': category,
        'questions': quiz_data,
        'current_question': 0,
        'score': 0,
        'total_questions': len(quiz_data)
    }
    
    await show_question(update, context)

async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """현재 문제 표시"""
    quiz_data = context.user_data.get('current_quiz')
    if not quiz_data:
        await update.message.reply_text("❌ 진행 중인 퀴즈가 없습니다. `/quiz`로 새로 시작하세요.")
        return
    
    current_q = quiz_data['current_question']
    question_data = quiz_data['questions'][current_q]
    category_info = QUIZ_CATEGORIES[quiz_data['category']]
    
    # 선택지 버튼 생성
    keyboard = []
    for i, choice in enumerate(question_data['choices']):
        keyboard.append([InlineKeyboardButton(
            f"{chr(65+i)}. {choice}", 
            callback_data=f"quiz_answer_{i}"
        )])
    
    keyboard.append([InlineKeyboardButton("❌ 퀴즈 종료", callback_data="quiz_quit")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    progress_bar = "▓" * (current_q + 1) + "░" * (quiz_data['total_questions'] - current_q - 1)
    
    message_text = f"""
{category_info['emoji']} **{category_info['name']} - 문제 {current_q + 1}/{quiz_data['total_questions']}**

📊 **진행률:** {progress_bar} ({current_q + 1}/{quiz_data['total_questions']})
🏆 **현재 점수:** {quiz_data['score']}/{current_q} (정답률: {round((quiz_data['score']/max(current_q, 1))*100, 1) if current_q > 0 else 0}%)

━━━━━━━━━━━━━━━━━━━━━━━━

**❓ 문제:**
{question_data['question']}

**📝 선택지를 골라주세요:**
    """
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup
        )

async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, answer_index: int) -> None:
    """퀴즈 답안 처리"""
    quiz_data = context.user_data.get('current_quiz')
    if not quiz_data:
        await update.callback_query.answer("❌ 퀴즈 세션이 만료되었습니다.")
        return
    
    current_q = quiz_data['current_question']
    question_data = quiz_data['questions'][current_q]
    user_answer = question_data['choices'][answer_index]
    correct_answer = question_data['correct_answer']
    is_correct = user_answer == correct_answer
    
    # 점수 업데이트
    if is_correct:
        quiz_data['score'] += 1
    
    # 결과 메시지
    result_emoji = "✅" if is_correct else "❌"
    result_text = "정답!" if is_correct else "틀렸습니다."
    
    result_message = f"""
{result_emoji} **{result_text}**

**🎯 당신의 답:** {user_answer}
**✅ 정답:** {correct_answer}

**📖 해설:**
{question_data.get('explanation', '해설이 없습니다.')}

**🏆 현재 점수:** {quiz_data['score']}/{current_q + 1}
    """
    
    # 다음 문제로 진행
    quiz_data['current_question'] += 1
    
    if quiz_data['current_question'] >= quiz_data['total_questions']:
        # 퀴즈 완료
        await show_quiz_results(update, context, result_message)
    else:
        # 다음 문제 버튼
        keyboard = [[InlineKeyboardButton("➡️ 다음 문제", callback_data="quiz_next")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            result_message + "\n\n준비되면 다음 문제로 넘어가세요!",
            reply_markup=reply_markup
        )

async def show_quiz_results(update: Update, context: ContextTypes.DEFAULT_TYPE, last_answer_result: str = "") -> None:
    """퀴즈 결과 표시"""
    quiz_data = context.user_data.get('current_quiz')
    if not quiz_data:
        return
    
    chat_id = update.effective_chat.id
    score = quiz_data['score']
    total = quiz_data['total_questions']
    percentage = round((score / total) * 100, 1)
    category = quiz_data['category']
    
    # 성과 평가
    if percentage >= 90:
        grade = "🥇 완벽!"
        message = "놀라운 실력이네요!"
    elif percentage >= 80:
        grade = "🥈 우수"
        message = "정말 잘하셨어요!"
    elif percentage >= 70:
        grade = "🥉 양호"
        message = "좋은 성과입니다!"
    elif percentage >= 60:
        grade = "📚 보통"
        message = "조금 더 연습하면 완벽!"
    else:
        grade = "💪 더 노력"
        message = "포기하지 마세요!"
    
    # 경험치 계산
    exp_gained = score * 2  # 정답 1개당 2 EXP
    bonus_exp = 5 if percentage >= 80 else 0  # 80% 이상 시 보너스
    total_exp = exp_gained + bonus_exp
    
    # 사용자 데이터 업데이트
    UserManager.update_user_stats(chat_id, 'quiz_attempts', 1)
    exp_result = UserManager.add_exp(chat_id, total_exp)
    QuizManager.record_quiz_result(chat_id, category, score, total)
    
    # 레벨업 메시지
    levelup_text = ""
    if exp_result['leveled_up']:
        levelup_text = f"\n\n🎉 **레벨업!** {exp_result['old_level']} → {exp_result['new_level']}"
    
    category_info = QUIZ_CATEGORIES[category]
    
    results_message = f"""
{last_answer_result}

━━━━━━━━━━━━━━━━━━━━━━━━
🎊 **퀴즈 완료!** 🎊
━━━━━━━━━━━━━━━━━━━━━━━━

{category_info['emoji']} **카테고리:** {category_info['name']}

🏆 **최종 점수:** {score}/{total} ({percentage}%)
🌟 **평가:** {grade}
💬 **코멘트:** {message}

⭐ **획득 경험치:** +{total_exp} EXP
   • 정답 보상: +{exp_gained} EXP
   • 성과 보너스: +{bonus_exp} EXP{levelup_text}

━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    # 다시 도전 버튼
    keyboard = [
        [InlineKeyboardButton(f"🔄 {category_info['name']} 다시 도전", callback_data=f"quiz_{category}")],
        [InlineKeyboardButton("🧠 다른 퀴즈 도전", callback_data="quiz_menu")],
        [InlineKeyboardButton("📊 내 기록 보기", callback_data="quiz_history")],
        [InlineKeyboardButton("🏅 리더보드", callback_data="leaderboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 퀴즈 세션 정리
    if 'current_quiz' in context.user_data:
        del context.user_data['current_quiz']
    
    await update.callback_query.edit_message_text(
        results_message,
        reply_markup=reply_markup
    )

async def show_quiz_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """퀴즈 기록 표시"""
    chat_id = update.effective_chat.id
    user = UserManager.get_user(chat_id)
    
    quiz_history = user.get('quiz_history', [])
    if not quiz_history:
        await update.callback_query.edit_message_text(
            "📊 **퀴즈 기록이 없습니다.**\n\n"
            "첫 번째 퀴즈에 도전해보세요!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🧠 퀴즈 시작", callback_data="quiz_menu")
            ]])
        )
        return
    
    # 최근 10개 기록만 표시
    recent_history = quiz_history[-10:]
    
    history_text = "📊 **나의 퀴즈 기록** (최근 10개)\n\n"
    
    for i, record in enumerate(reversed(recent_history), 1):
        category_name = QUIZ_CATEGORIES.get(record['category'], {}).get('name', record['category'])
        date = record['date'][:10]  # YYYY-MM-DD 형식
        
        grade_emoji = "🥇" if record['percentage'] >= 90 else "🥈" if record['percentage'] >= 80 else "🥉" if record['percentage'] >= 70 else "📚"
        
        history_text += f"{i}. **{category_name}** - {date}\n"
        history_text += f"   {grade_emoji} {record['score']}/{record['total']} ({record['percentage']}%)\n\n"
    
    # 통계 요약
    total_attempts = len(quiz_history)
    if total_attempts > 0:
        avg_score = sum(r['percentage'] for r in quiz_history) / total_attempts
        best_score = max(quiz_history, key=lambda x: x['percentage'])
        
        history_text += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        history_text += f"📈 **전체 통계**\n"
        history_text += f"• 총 시도: {total_attempts}회\n"
        history_text += f"• 평균 점수: {avg_score:.1f}%\n"
        history_text += f"• 최고 기록: {best_score['percentage']}% ({QUIZ_CATEGORIES.get(best_score['category'], {}).get('name', best_score['category'])})\n"
    
    keyboard = [
        [InlineKeyboardButton("🧠 새 퀴즈 도전", callback_data="quiz_menu")],
        [InlineKeyboardButton("🏅 리더보드", callback_data="leaderboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        history_text,
        reply_markup=reply_markup
    )

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """리더보드 표시"""
    # 전체 순위
    overall_board = QuizManager.get_leaderboard('overall', 10)
    quiz_board = QuizManager.get_leaderboard('quiz', 10)
    
    if not overall_board:
        await update.callback_query.edit_message_text(
            "🏅 **리더보드가 비어있습니다.**\n\n"
            "첫 번째 도전자가 되어보세요!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🧠 퀴즈 시작", callback_data="quiz_menu")
            ]])
        )
        return
    
    leaderboard_text = "🏅 **리더보드** 🏅\n\n"
    
    # 전체 경험치 순위
    leaderboard_text += "👑 **전체 랭킹** (경험치 기준)\n"
    for i, entry in enumerate(overall_board[:5], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
        leaderboard_text += f"{emoji} {i}위: Lv.{entry['level']} ({entry['score']} EXP)\n"
    
    leaderboard_text += "\n🧠 **퀴즈 순위** (퀴즈 점수 기준)\n"
    for i, entry in enumerate(quiz_board[:5], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
        leaderboard_text += f"{emoji} {i}위: {entry['score']}점 (Lv.{entry['level']})\n"
    
    # 현재 사용자 순위
    chat_id = update.effective_chat.id
    user_rank = None
    for i, entry in enumerate(overall_board, 1):
        if entry['user_id'] == str(chat_id):
            user_rank = i
            break
    
    if user_rank:
        leaderboard_text += f"\n🎯 **당신의 순위:** {user_rank}위"
    
    keyboard = [
        [InlineKeyboardButton("🧠 퀴즈 도전", callback_data="quiz_menu")],
        [InlineKeyboardButton("📊 내 기록", callback_data="quiz_history")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        leaderboard_text,
        reply_markup=reply_markup
    )

# 퀴즈 생성 함수들
async def generate_vocabulary_quiz(count: int = 5) -> list:
    """어휘 퀴즈 생성"""
    questions = []
    words = QuizManager.get_vocabulary_sample(count * 4)  # 선택지를 위해 더 많이 가져오기
    
    if len(words) < count * 4:
        return None
    
    for i in range(count):
        correct_word = words[i]
        wrong_words = words[count + i*3:count + (i+1)*3]
        
        # 선택지 생성 및 셞기
        choices = [correct_word['korean']] + [w['korean'] for w in wrong_words]
        random.shuffle(choices)
        
        questions.append({
            'question': f"다음 러시아어 단어의 뜻은?\n\n**{correct_word['russian']}**\n[{correct_word.get('pronunciation', '')}]",
            'choices': choices,
            'correct_answer': correct_word['korean'],
            'explanation': f"**{correct_word['russian']}** [{correct_word.get('pronunciation', '')}] = {correct_word['korean']}"
        })
    
    return questions

async def generate_grammar_quiz(count: int = 5) -> list:
    """문법 퀴즈 생성 (AI 활용)"""
    prompt = f"""
    러시아어 문법 퀴즈 {count}개를 만들어주세요. 각 문제는 다음 형식으로 만들어주세요:

    문제 1:
    질문: [문법 문제]
    선택지: A) [선택지1] B) [선택지2] C) [선택지3] D) [선택지4]
    정답: [정답]
    해설: [상세한 해설]

    주제는 격변화, 동사 활용, 시제, 전치사 등 기본 문법을 다뤄주세요.
    """
    
    try:
        response = await call_gemini_api(prompt)
        # AI 응답을 파싱하여 퀴즈 형식으로 변환
        questions = parse_grammar_quiz_response(response)
        return questions[:count]
    except Exception as e:
        logger.error(f"문법 퀴즈 생성 오류: {e}")
        return None

async def generate_pronunciation_quiz(count: int = 5) -> list:
    """발음 퀴즈 생성"""
    words = QuizManager.get_vocabulary_sample(count * 4)
    if len(words) < count:
        return None
    
    questions = []
    for i in range(count):
        correct_word = words[i]
        
        # 발음이 비슷한 다른 단어들로 오답 생성 (간단한 방식)
        wrong_pronunciations = [
            correct_word.get('pronunciation', '').replace('а', 'о'),
            correct_word.get('pronunciation', '').replace('е', 'и'),
            correct_word.get('pronunciation', '').replace('ы', 'и')
        ]
        
        choices = [correct_word.get('pronunciation', '')] + wrong_pronunciations[:3]
        random.shuffle(choices)
        
        questions.append({
            'question': f"다음 러시아어 단어의 올바른 발음은?\n\n**{correct_word['russian']}** ({correct_word['korean']})",
            'choices': choices,
            'correct_answer': correct_word.get('pronunciation', ''),
            'explanation': f"**{correct_word['russian']}**의 올바른 발음은 **{correct_word.get('pronunciation', '')}**입니다."
        })
    
    return questions

def parse_grammar_quiz_response(response: str) -> list:
    """AI 응답을 퀴즈 형식으로 파싱"""
    questions = []
    
    try:
        # 간단한 파싱 로직 (실제로는 더 정교한 파싱이 필요)
        parts = response.split('문제 ')
        
        for part in parts[1:]:  # 첫 번째는 빈 문자열이므로 제외
            lines = part.strip().split('\n')
            
            question = ""
            choices = []
            correct_answer = ""
            explanation = ""
            
            for line in lines:
                if line.startswith('질문:'):
                    question = line[3:].strip()
                elif line.startswith('선택지:'):
                    # A) B) C) D) 형식 파싱
                    choice_text = line[4:].strip()
                    parts = choice_text.split(') ')
                    for i in range(1, len(parts)):
                        if i < len(parts):
                            choices.append(parts[i].split(' ')[0])
                elif line.startswith('정답:'):
                    correct_answer = line[3:].strip()
                elif line.startswith('해설:'):
                    explanation = line[3:].strip()
            
            if question and choices and correct_answer:
                questions.append({
                    'question': question,
                    'choices': choices,
                    'correct_answer': correct_answer,
                    'explanation': explanation
                })
    
    except Exception as e:
        logger.error(f"퀴즈 파싱 오류: {e}")
    
    return questions 