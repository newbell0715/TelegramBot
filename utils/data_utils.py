import os
import json
from datetime import datetime
from config.settings import USER_DATA_FILE, MSK

def load_user_data():
    """사용자 데이터를 파일에서 로드"""
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    """사용자 데이터를 파일에 저장"""
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user(chat_id):
    """사용자 데이터를 가져오거나 새로 생성"""
    users = load_user_data()
    user_id = str(chat_id)
    if user_id not in users:
        users[user_id] = {
            'plan': 'Pro',
            'subscribed_daily': False,
            'quest_state': {'current_quest': None, 'stage': 0},
            'stats': {
                'start_date': datetime.now(MSK).isoformat(),
                'last_active_date': datetime.now(MSK).isoformat(),
                'quests_completed': 0,
                'sentences_corrected': 0,
                'daily_words_received': 0
            }
        }
        save_user_data(users)
    users[user_id]['stats']['last_active_date'] = datetime.now(MSK).isoformat()
    save_user_data(users)
    return users[user_id] 