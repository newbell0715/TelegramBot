import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from functools import lru_cache
from cachetools import TTLCache

from config.settings import USER_DATA_FILE, MSK, CACHE_TTL, MAX_CACHE_SIZE, PLANS

# 캐시 인스턴스
cache = TTLCache(maxsize=MAX_CACHE_SIZE, ttl=CACHE_TTL)

class UserManager:
    """사용자 데이터 관리 클래스"""
    
    @staticmethod
    def load_user_data() -> Dict[str, Any]:
        """사용자 데이터 로드 (캐시된)"""
        if 'user_data' in cache:
            return cache['user_data']
            
        if os.path.exists(USER_DATA_FILE):
            try:
                with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cache['user_data'] = data
                    return data
            except Exception:
                pass
        
        data = {}
        cache['user_data'] = data
        return data

    @staticmethod
    def save_user_data(data: Dict[str, Any]) -> None:
        """사용자 데이터 저장"""
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        cache['user_data'] = data

    @staticmethod
    def get_user(chat_id: int) -> Dict[str, Any]:
        """사용자 정보 가져오기 (없으면 생성)"""
        users = UserManager.load_user_data()
        user_id = str(chat_id)
        
        if user_id not in users:
            now = datetime.now(MSK).isoformat()
            users[user_id] = {
                'plan': 'Free',
                'subscribed_daily': False,
                'quest_state': {'current_quest': None, 'stage': 0},
                'stats': {
                    'start_date': now,
                    'last_active_date': now,
                    'quests_completed': 0,
                    'sentences_corrected': 0,
                    'daily_words_received': 0,
                    'total_exp': 0,
                    'level': 1,
                    'quiz_scores': [],
                    'streak_days': 0,
                    'badges': [],
                    'favorite_language': 'russian'
                },
                'usage': {
                    'today': datetime.now(MSK).date().isoformat(),
                    'corrections': 0,
                    'translations': 0,
                    'tts_calls': 0,
                    'quiz_attempts': 0
                },
                'preferences': {
                    'notification_time': '07:00',
                    'difficulty': 'medium',
                    'language_learning_goals': ['conversation', 'grammar']
                }
            }
            UserManager.save_user_data(users)
        
        # 마지막 활동 시간 업데이트
        users[user_id]['stats']['last_active_date'] = datetime.now(MSK).isoformat()
        
        # 일일 사용량 리셋 체크
        today = datetime.now(MSK).date().isoformat()
        if users[user_id]['usage']['today'] != today:
            users[user_id]['usage'] = {
                'today': today,
                'corrections': 0,
                'translations': 0,
                'tts_calls': 0,
                'quiz_attempts': 0
            }
        
        UserManager.save_user_data(users)
        return users[user_id]

    @staticmethod
    def update_user_stats(chat_id: int, stat_type: str, increment: int = 1) -> None:
        """사용자 통계 업데이트"""
        users = UserManager.load_user_data()
        user_id = str(chat_id)
        
        if user_id in users:
            if stat_type in users[user_id]['stats']:
                users[user_id]['stats'][stat_type] += increment
            
            # 경험치 및 레벨 계산
            if stat_type == 'quests_completed':
                users[user_id]['stats']['total_exp'] += 50
            elif stat_type == 'sentences_corrected':
                users[user_id]['stats']['total_exp'] += 10
            
            # 레벨업 체크
            exp = users[user_id]['stats']['total_exp']
            new_level = min(100, max(1, exp // 100 + 1))
            users[user_id]['stats']['level'] = new_level
            
            UserManager.save_user_data(users)

    @staticmethod
    def check_usage_limit(chat_id: int, usage_type: str) -> tuple[bool, int, int]:
        """사용량 제한 확인"""
        user = UserManager.get_user(chat_id)
        plan = user['plan']
        plan_limits = PLANS.get(plan, PLANS['Free'])
        
        current_usage = user['usage'].get(usage_type, 0)
        limit = plan_limits.get(f'daily_{usage_type}', 0)
        
        if limit == -1:  # 무제한
            return True, current_usage, -1
        
        can_use = current_usage < limit
        return can_use, current_usage, limit

    @staticmethod
    def increment_usage(chat_id: int, usage_type: str) -> None:
        """사용량 증가"""
        users = UserManager.load_user_data()
        user_id = str(chat_id)
        
        if user_id in users:
            if usage_type not in users[user_id]['usage']:
                users[user_id]['usage'][usage_type] = 0
            users[user_id]['usage'][usage_type] += 1
            UserManager.save_user_data(users)

class ProgressTracker:
    """학습 진도 추적 클래스"""
    
    @staticmethod
    def calculate_progress_bar(current: int, total: int, length: int = 10) -> str:
        """진행 상태 바 생성"""
        if total == 0:
            return '□' * length
        
        filled = int((current / total) * length)
        return '■' * filled + '□' * (length - filled)
    
    @staticmethod
    def get_streak_info(chat_id: int) -> Dict[str, Any]:
        """연속 학습일 정보"""
        user = UserManager.get_user(chat_id)
        last_active = datetime.fromisoformat(user['stats']['last_active_date'])
        today = datetime.now(MSK)
        
        # 연속일 계산 로직
        days_diff = (today.date() - last_active.date()).days
        if days_diff <= 1:
            streak = user['stats'].get('streak_days', 0)
            if days_diff == 1:
                streak += 1
        else:
            streak = 0
        
        return {
            'current_streak': streak,
            'longest_streak': max(streak, user['stats'].get('longest_streak', 0)),
            'badge': get_streak_badge(streak)
        }

def get_streak_badge(days: int) -> str:
    """연속일에 따른 배지 반환"""
    if days >= 100:
        return "🔥💎 화염의 다이아몬드"
    elif days >= 50:
        return "🔥👑 화염의 왕관"
    elif days >= 30:
        return "🔥🏆 화염의 트로피"
    elif days >= 14:
        return "🔥⭐ 화염의 별"
    elif days >= 7:
        return "🔥 일주일 화염"
    elif days >= 3:
        return "✨ 시작의 불꽃"
    else:
        return "💫 첫 걸음"

@lru_cache(maxsize=100)
def load_vocabulary_data() -> List[Dict[str, Any]]:
    """어휘 데이터 로드 (캐시된)"""
    try:
        with open('russian_korean_vocab_2000.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('vocabulary', [])
    except FileNotFoundError:
        return []

@lru_cache(maxsize=50)
def load_conversation_data() -> List[Dict[str, Any]]:
    """회화 데이터 로드 (캐시된)"""
    try:
        with open('russian_learning_database.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('conversations', [])
    except FileNotFoundError:
        return []

class QuizManager:
    """퀴즈 관리 클래스"""
    
    @staticmethod
    def generate_vocabulary_quiz() -> Dict[str, Any]:
        """단어 퀴즈 생성"""
        vocabulary = load_vocabulary_data()
        if not vocabulary:
            return None
        
        import random
        word = random.choice(vocabulary)
        
        # 오답 선택지 생성
        wrong_answers = random.sample([v['korean'] for v in vocabulary if v != word], 3)
        
        options = [word['korean']] + wrong_answers
        random.shuffle(options)
        
        return {
            'question': f"'{word['russian']}'의 뜻은?",
            'options': options,
            'correct_answer': word['korean'],
            'pronunciation': word.get('pronunciation', ''),
            'category': 'vocabulary'
        }
    
    @staticmethod
    def check_answer(user_answer: str, correct_answer: str) -> bool:
        """정답 확인"""
        return user_answer.strip().lower() == correct_answer.strip().lower()

def format_user_stats(user_data: Dict[str, Any]) -> str:
    """사용자 통계를 보기 좋게 포맷팅"""
    stats = user_data['stats']
    level = stats.get('level', 1)
    exp = stats.get('total_exp', 0)
    next_level_exp = level * 100
    exp_progress = exp % 100
    
    progress_bar = ProgressTracker.calculate_progress_bar(exp_progress, 100)
    
    return f"""
📊 **개인 통계**
🔰 **레벨**: {level} ({exp_progress}/100 EXP)
{progress_bar}

📈 **학습 기록**
✅ 완료한 퀘스트: {stats.get('quests_completed', 0)}개
✍️ 교정받은 문장: {stats.get('sentences_corrected', 0)}개
📚 받은 학습자료: {stats.get('daily_words_received', 0)}회

🏆 **성취**
🔥 연속 학습일: {stats.get('streak_days', 0)}일
⭐ 총 경험치: {exp} EXP
🎯 평균 퀴즈 점수: {calculate_average_quiz_score(stats.get('quiz_scores', []))}점
"""

def calculate_average_quiz_score(scores: List[int]) -> float:
    """평균 퀴즈 점수 계산"""
    return sum(scores) / len(scores) if scores else 0.0 