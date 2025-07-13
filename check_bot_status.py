import asyncio
import telegram
import os
from datetime import datetime
import pytz
import json

# 봇 토큰으로 봇 인스턴스 생성
bot = telegram.Bot(token='8064422632:AAFkFqQDA_35OCa5-BFxeHPA9_hil4cY8Rg')

async def check_bot_status():
    try:
        # 봇 정보 확인
        bot_info = await bot.get_me()
        print(f'봇 상태: {bot_info.first_name} (@{bot_info.username})')
        
        # 현재 시간 확인 (모스크바 시간)
        msk = pytz.timezone('Europe/Moscow')
        current_time = datetime.now(msk)
        print(f'현재 모스크바 시간: {current_time.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # 웹훅 상태 확인
        webhook_info = await bot.get_webhook_info()
        print(f'웹훅 URL: {webhook_info.url}')
        print(f'웹훅 상태: {"활성" if webhook_info.url else "비활성"}')
        
        # 단어 발송 테스트
        from SimpleBot import send_daily_learning
        print("단어 발송 테스트 실행 중...")
        await send_daily_learning(bot)
        print("단어 발송 테스트 완료")
        
    except Exception as e:
        print(f'봇 상태 확인 중 오류: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_bot_status()) 