import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from cachetools import TTLCache
import asyncio
import logging
from config.settings import USER_DATA_FILE, MSK, CACHE_TTL, MAX_CACHE_SIZE

logger = logging.getLogger(__name__)

# 메모리 캐시
user_cache = TTLCache(maxsize=MAX_CACHE_SIZE, ttl=CACHE_TTL)

class UserManager:
    @staticmethod
    def load_user_data() -> Dict:
        """사용자 데이터 로드"""
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"사용자 데이터 로드 오류: {e}")
            return {}

    @staticmethod
    def save_user_data(data: Dict) -> None:
        """사용자 데이터 저장"""
        try:
            with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            # 캐시도 업데이트
            for user_id, user_data in data.items():
                user_cache[user_id] = user_data
        except Exception as e:
            logger.error(f"사용자 데이터 저장 오류: {e}")

    @staticmethod
    def get_user(chat_id: int) -> Dict:
        """사용자 정보 가져오기 (캐시 활용)"""
        user_id = str(chat_id)
        
        # 캐시에서 먼저 확인
        if user_id in user_cache:
            user_data = user_cache[user_id]
            user_data['stats']['last_active_date'] = datetime.now(MSK).isoformat()
            return user_data
        
        users = UserManager.load_user_data()
        
        if user_id not in users:
            users[user_id] = {
                'subscribed_daily': False,
                'quest_state': {'current_quest': None, 'stage': 0},
                'stats': {
                    'start_date': datetime.now(MSK).isoformat(),
                    'last_active_date': datetime.now(MSK).isoformat(),
                    'quests_completed': 0,
                    'sentences_corrected': 0,
                    'translations_made': 0,
                    'tts_generated': 0,
                    'daily_words_received': 0,
                    'quiz_attempts': 0,
                    'quiz_score': 0,
                    'total_exp': 0,
                    'level': 1,
                    'streak_days': 0,
                    'last_quiz_date': None,
                    'achievements': []
                },
                'quiz_history': [],
                'preferences': {
                    'language': 'korean',
                    'difficulty': 'easy',
                    'notifications': True
                }
            }
            UserManager.save_user_data(users)
        
        # 마지막 활동 시간 업데이트
        users[user_id]['stats']['last_active_date'] = datetime.now(MSK).isoformat()
        user_cache[user_id] = users[user_id]
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
                
                # 경험치 추가 시 레벨 계산
                if stat_type == 'total_exp':
                    exp = users[user_id]['stats']['total_exp']
                    level = min(exp // 100 + 1, 100)  # 100레벨 최대
                    users[user_id]['stats']['level'] = level
                
                UserManager.save_user_data(users)

    @staticmethod
    def add_exp(chat_id: int, exp_amount: int) -> Dict:
        """경험치 추가 및 레벨업 확인"""
        users = UserManager.load_user_data()
        user_id = str(chat_id)
        
        if user_id not in users:
            UserManager.get_user(chat_id)
            users = UserManager.load_user_data()
        
        old_level = users[user_id]['stats']['level']
        users[user_id]['stats']['total_exp'] += exp_amount
        
        new_exp = users[user_id]['stats']['total_exp']
        new_level = min(new_exp // 100 + 1, 100)
        users[user_id]['stats']['level'] = new_level
        
        UserManager.save_user_data(users)
        
        return {
            'leveled_up': new_level > old_level,
            'old_level': old_level,
            'new_level': new_level,
            'total_exp': new_exp
        }

    @staticmethod
    def calculate_streak(chat_id: int) -> int:
        """연속 학습 일수 계산"""
        users = UserManager.load_user_data()
        user_id = str(chat_id)
        
        if user_id not in users:
            return 0
        
        last_active = users[user_id]['stats'].get('last_active_date')
        if not last_active:
            return 0
        
        last_date = datetime.fromisoformat(last_active).date()
        today = datetime.now(MSK).date()
        
        if last_date == today:
            return users[user_id]['stats'].get('streak_days', 0)
        elif last_date == today - timedelta(days=1):
            # 어제 활동했으면 연속
            users[user_id]['stats']['streak_days'] = users[user_id]['stats'].get('streak_days', 0) + 1
            UserManager.save_user_data(users)
            return users[user_id]['stats']['streak_days']
        else:
            # 연속 끊김
            users[user_id]['stats']['streak_days'] = 1
            UserManager.save_user_data(users)
            return 1

class ProgressTracker:
    @staticmethod
    def calculate_progress_bar(current: int, total: int, length: int = 10) -> str:
        """진행률 바 생성"""
        if total == 0:
            return "░" * length
        
        filled = int((current / total) * length)
        bar = "▓" * filled + "░" * (length - filled)
        return f"{bar} {current}/{total}"

    @staticmethod
    def get_user_progress(chat_id: int) -> Dict:
        """사용자 진행 상황 조회"""
        user = UserManager.get_user(chat_id)
        stats = user['stats']
        
        # 레벨 진행률
        exp = stats.get('total_exp', 0)
        level = stats.get('level', 1)
        exp_for_current_level = (level - 1) * 100
        exp_for_next_level = level * 100
        exp_progress = exp - exp_for_current_level
        
        return {
            'level': level,
            'exp': exp,
            'exp_progress': exp_progress,
            'exp_needed': 100 - exp_progress if level < 100 else 0,
            'streak': ProgressTracker.calculate_streak_badge(UserManager.calculate_streak(chat_id)),
            'total_activities': (
                stats.get('sentences_corrected', 0) + 
                stats.get('translations_made', 0) + 
                stats.get('quests_completed', 0) + 
                stats.get('quiz_attempts', 0)
            ),
            'achievements': stats.get('achievements', [])
        }

    @staticmethod
    def calculate_streak_badge(streak_days: int) -> str:
        """연속 일수에 따른 뱃지 반환"""
        if streak_days >= 30:
            return f"🔥 {streak_days}일 연속 (전설의 학습자!)"
        elif streak_days >= 14:
            return f"🔥 {streak_days}일 연속 (꾸준한 학습자)"
        elif streak_days >= 7:
            return f"⭐ {streak_days}일 연속 (일주일 달성!)"
        elif streak_days >= 3:
            return f"✨ {streak_days}일 연속 (좋은 습관!)"
        else:
            return f"🌱 {streak_days}일"

class QuizManager:
    @staticmethod
    def get_vocabulary_sample(count: int = 10) -> List[Dict]:
        """어휘 퀴즈용 단어 샘플 가져오기"""
        try:
            with open('russian_korean_vocab_2000.json', 'r', encoding='utf-8') as f:
                vocab_db = json.load(f)
            
            if 'vocabulary' in vocab_db:
                return random.sample(vocab_db['vocabulary'], min(count, len(vocab_db['vocabulary'])))
            return []
        except Exception as e:
            logger.error(f"어휘 데이터 로드 오류: {e}")
            return []

    @staticmethod
    def generate_quiz_question(category: str) -> Dict:
        """퀴즈 문제 생성"""
        if category == 'vocabulary':
            words = QuizManager.get_vocabulary_sample(4)  # 정답 1개 + 오답 3개
            if len(words) < 4:
                return None
            
            correct_word = words[0]
            wrong_words = words[1:4]
            
            # 선택지 섞기
            choices = [correct_word['korean']] + [w['korean'] for w in wrong_words]
            random.shuffle(choices)
            
            return {
                'question': f"다음 러시아어 단어의 뜻은?\n\n**{correct_word['russian']}**\n[{correct_word.get('pronunciation', '')}]",
                'choices': choices,
                'correct_answer': correct_word['korean'],
                'explanation': f"**{correct_word['russian']}** [{correct_word.get('pronunciation', '')}] = {correct_word['korean']}"
            }
        
        # 다른 카테고리들도 추가 가능
        return None

    @staticmethod
    def record_quiz_result(chat_id: int, category: str, score: int, total_questions: int) -> None:
        """퀴즈 결과 기록"""
        users = UserManager.load_user_data()
        user_id = str(chat_id)
        
        if user_id not in users:
            UserManager.get_user(chat_id)
            users = UserManager.load_user_data()
        
        # 퀴즈 기록 추가
        quiz_record = {
            'date': datetime.now(MSK).isoformat(),
            'category': category,
            'score': score,
            'total': total_questions,
            'percentage': round((score / total_questions) * 100, 1)
        }
        
        if 'quiz_history' not in users[user_id]:
            users[user_id]['quiz_history'] = []
        
        users[user_id]['quiz_history'].append(quiz_record)
        
        # 통계 업데이트
        users[user_id]['stats']['quiz_attempts'] += 1
        users[user_id]['stats']['quiz_score'] += score
        users[user_id]['stats']['last_quiz_date'] = datetime.now(MSK).isoformat()
        
        # 경험치 추가
        exp_gained = score * 2  # 맞은 문제당 2 EXP
        users[user_id]['stats']['total_exp'] += exp_gained
        
        UserManager.save_user_data(users)

    @staticmethod
    def get_leaderboard(category: str = 'overall', limit: int = 10) -> List[Dict]:
        """리더보드 조회"""
        users = UserManager.load_user_data()
        leaderboard = []
        
        for user_id, user_data in users.items():
            stats = user_data.get('stats', {})
            
            if category == 'overall':
                score = stats.get('total_exp', 0)
            elif category == 'quiz':
                score = stats.get('quiz_score', 0)
            elif category == 'streak':
                score = UserManager.calculate_streak(int(user_id))
            else:
                continue
            
            leaderboard.append({
                'user_id': user_id,
                'score': score,
                'level': stats.get('level', 1),
                'activities': (
                    stats.get('sentences_corrected', 0) + 
                    stats.get('translations_made', 0) + 
                    stats.get('quests_completed', 0)
                )
            })
        
        # 점수순 정렬
        leaderboard.sort(key=lambda x: x['score'], reverse=True)
        return leaderboard[:limit]

    @staticmethod
    def format_user_stats(chat_id: int) -> str:
        """사용자 통계 포맷팅"""
        user = UserManager.get_user(chat_id)
        stats = user['stats']
        
        # 경험치와 레벨 계산
        exp = stats.get('total_exp', 0)
        level = stats.get('level', 1)
        exp_progress = exp % 100
        
        progress_bar = ProgressTracker.calculate_progress_bar(exp_progress, 100)
        
        return f"""
📊 **학습 통계**

🔰 **레벨**: {level} ({exp_progress}/100 EXP)
{progress_bar}

📈 **활동 기록**:
• ✍️ 작문 교정: {stats.get('sentences_corrected', 0)}회
• 🌍 번역: {stats.get('translations_made', 0)}회  
• 🎵 음성 변환: {stats.get('tts_generated', 0)}회
• 🏆 완료한 퀘스트: {stats.get('quests_completed', 0)}개
• 🧠 퀴즈 시도: {stats.get('quiz_attempts', 0)}회

🔥 **연속 학습**: {ProgressTracker.calculate_streak_badge(UserManager.calculate_streak(chat_id))}

⭐ **총 경험치**: {exp} EXP
        """.strip() 