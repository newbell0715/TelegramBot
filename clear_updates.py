import requests
import json

# 봇 토큰
BOT_TOKEN = "8064422632:AAFkFqQDA_35OCa5-BFxeHPA9_hil4cY8Rg"

def clear_pending_updates():
    """Telegram Bot API의 모든 pending updates를 클리어합니다."""
    
    print("🔄 Pending updates 클리어 중...")
    
    # getUpdates API 호출하여 모든 pending updates 가져오기
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    
    try:
        # 가장 높은 offset으로 모든 업데이트 클리어
        response = requests.get(url + "?offset=-1")
        
        if response.status_code == 200:
            print("✅ Pending updates 클리어 완료!")
            print("📊 응답:", response.json())
        else:
            print(f"❌ 클리어 실패: {response.status_code}")
            print("📊 응답:", response.text)
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def check_bot_status():
    """봇 상태 확인"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            bot_info = response.json()
            print("🤖 봇 정보:")
            print(f"   이름: {bot_info['result']['first_name']}")
            print(f"   사용자명: @{bot_info['result']['username']}")
            print(f"   ID: {bot_info['result']['id']}")
            print("✅ 봇이 정상적으로 활성화되어 있습니다!")
        else:
            print(f"❌ 봇 상태 확인 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 봇 상태 확인 중 오류: {e}")

if __name__ == "__main__":
    print("🚀 Telegram Bot 충돌 해결 스크립트")
    print("=" * 50)
    
    # 1. 봇 상태 확인
    check_bot_status()
    print()
    
    # 2. Pending updates 클리어
    clear_pending_updates()
    print()
    
    print("✅ 작업 완료!")
    print("💡 이제 Railway에서 봇을 다시 시작하면 정상 작동할 것입니다.") 