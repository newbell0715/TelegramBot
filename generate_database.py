import json
import asyncio
import time
from services.gemini_service import call_gemini

async def generate_vocabulary_batch(start_id, count=100):
    """단어 배치 생성"""
    prompt = f"""
    초급 러시아어 단어 {count}개를 생성해주세요. 다음 JSON 형식으로 제공해주세요:

    [
        {{
            "id": {start_id},
            "russian": "[러시아어 단어]",
            "korean": "[한국어 뜻]",
            "pronunciation": "[한글 발음]",
            "level": "beginner",
            "category": "[카테고리]"
        }},
        ...
    ]

    카테고리 예시: greetings, family, food, colors, numbers, body, animals, weather, time, transportation, emotions, actions, objects, clothing, house, school, work, nature, health, sports

    - 실제 존재하는 러시아어 단어만 사용
    - 초급자가 꼭 알아야 할 기본 단어들
    - 한글 발음은 한국인이 읽기 쉽게 표기
    - 다양한 카테고리에서 균등하게 선택
    - JSON 형식만 출력하고 다른 설명은 생략

    ID는 {start_id}부터 {start_id + count - 1}까지 연속으로 사용하세요.
    """
    
    result = await call_gemini(prompt)
    return result

async def generate_conversations_batch(start_id, count=50):
    """회화 문장 배치 생성"""
    prompt = f"""
    초급 러시아어 회화 문장 {count}개를 생성해주세요. 다음 JSON 형식으로 제공해주세요:

    [
        {{
            "id": {start_id},
            "russian": "[러시아어 문장]",
            "korean": "[한국어 번역]",
            "pronunciation": "[한글 발음]",
            "level": "beginner",
            "category": "[카테고리]"
        }},
        ...
    ]

    카테고리 예시: greetings, introductions, shopping, restaurant, directions, feelings, family, hobbies, weather, time, transportation, daily_life, apologizing, thanking, asking_help

    - 실제 러시아인이 자주 사용하는 자연스러운 문장
    - 초급자가 실생활에서 바로 사용할 수 있는 표현
    - 한글 발음은 한국인이 읽기 쉽게 표기
    - 다양한 상황에서 균등하게 선택
    - JSON 형식만 출력하고 다른 설명은 생략

    ID는 {start_id}부터 {start_id + count - 1}까지 연속으로 사용하세요.
    """
    
    result = await call_gemini(prompt)
    return result

async def generate_full_database():
    """전체 데이터베이스 생성"""
    print("🚀 러시아어 학습 데이터베이스 생성 시작...")
    
    # 기존 데이터베이스 로드
    try:
        with open('russian_learning_database.json', 'r', encoding='utf-8') as f:
            database = json.load(f)
    except FileNotFoundError:
        database = {"vocabulary": [], "conversations": [], "metadata": {}}
    
    # 단어 생성 (2000개)
    print("📚 단어 생성 중...")
    vocabulary_batches = 20  # 100개씩 20번
    
    for i in range(vocabulary_batches):
        start_id = i * 100 + 1
        print(f"  배치 {i+1}/{vocabulary_batches}: ID {start_id}-{start_id+99}")
        
        try:
            batch_result = await generate_vocabulary_batch(start_id, 100)
            # JSON 파싱 시도
            batch_data = json.loads(batch_result.strip())
            database["vocabulary"].extend(batch_data)
            
            # 중간 저장
            with open('russian_learning_database.json', 'w', encoding='utf-8') as f:
                json.dump(database, f, ensure_ascii=False, indent=2)
            
            print(f"    ✅ 완료! 현재 단어 수: {len(database['vocabulary'])}")
            
        except Exception as e:
            print(f"    ❌ 오류: {e}")
            print(f"    응답: {batch_result[:200]}...")
        
        # API 호출 간격 조정
        await asyncio.sleep(2)
    
    # 회화 문장 생성 (1000개)
    print("\n💬 회화 문장 생성 중...")
    conversation_batches = 20  # 50개씩 20번
    
    for i in range(conversation_batches):
        start_id = i * 50 + 1
        print(f"  배치 {i+1}/{conversation_batches}: ID {start_id}-{start_id+49}")
        
        try:
            batch_result = await generate_conversations_batch(start_id, 50)
            # JSON 파싱 시도
            batch_data = json.loads(batch_result.strip())
            database["conversations"].extend(batch_data)
            
            # 중간 저장
            with open('russian_learning_database.json', 'w', encoding='utf-8') as f:
                json.dump(database, f, ensure_ascii=False, indent=2)
            
            print(f"    ✅ 완료! 현재 문장 수: {len(database['conversations'])}")
            
        except Exception as e:
            print(f"    ❌ 오류: {e}")
            print(f"    응답: {batch_result[:200]}...")
        
        # API 호출 간격 조정
        await asyncio.sleep(2)
    
    # 메타데이터 업데이트
    database["metadata"] = {
        "last_updated": "2025-01-18",
        "total_vocabulary": len(database["vocabulary"]),
        "total_conversations": len(database["conversations"]),
        "target_vocabulary": 2000,
        "target_conversations": 1000
    }
    
    # 최종 저장
    with open('russian_learning_database.json', 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 데이터베이스 생성 완료!")
    print(f"📊 총 단어: {len(database['vocabulary'])}개")
    print(f"📊 총 회화: {len(database['conversations'])}개")

if __name__ == "__main__":
    asyncio.run(generate_full_database()) 