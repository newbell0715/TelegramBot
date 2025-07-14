import json
import asyncio
import time
from services.gemini_service import call_gemini

# 레벨별 설정
LEVELS = {
    "beginner": {"count": 400, "categories": ["greetings","introductions","shopping","restaurant","directions","feelings","family","hobbies","weather","time","transportation","daily_life","apologizing","thanking","asking_help"]},
    "intermediate": {"count": 400, "categories": ["work","travel","health","opinions","past_experience","future_plans","culture","education","technology","news","relationships","problems","suggestions","comparisons"]},
    "advanced": {"count": 200, "categories": ["business","politics","philosophy","literature","science","debate","negotiation","presentation","formal_speech","abstract_concepts","complex_emotions","social_issues","academic_topics","professional_situations"]}
}

async def generate_conversations_batch(start_id, level, count, categories):
    prompt = f"""
러시아어 {level} 회화 문장 {count}개를 생성해주세요. 다음 JSON 형식으로만 제공해주세요:

[
  {{
    "id": {start_id},
    "russian": "[러시아어 문장]",
    "korean": "[한국어 번역]",
    "pronunciation": "[한글 발음]",
    "level": "{level}",
    "category": "[카테고리]"
  }},
  ...
]

- 실제 러시아인이 자주 사용하는 자연스러운 문장
- {level} 수준에 맞는 문법과 어휘
- 한글 발음은 한국인이 읽기 쉽게 표기
- 카테고리는 다음 중 하나로: {', '.join(categories)}
- ID는 {start_id}부터 {start_id+count-1}까지 연속 사용
- JSON 형식만 출력, 다른 설명 금지
"""
    return await call_gemini(prompt)

async def generate_full_database():
    print("🚀 러시아어 회화문장 데이터베이스 생성 시작...")
    database = {"conversations": [], "metadata": {}}
    current_id = 1

    for level, cfg in LEVELS.items():
        batches = cfg["count"] // 50
        for i in range(batches):
            start = current_id
            print(f"  [{level}] 배치 {i+1}/{batches}: ID {start}-{start+49}")
            try:
                result = await generate_conversations_batch(start, level, 50, cfg["categories"])
                batch = json.loads(result.strip())
                database["conversations"].extend(batch)
                current_id += 50
                with open('russian_conversations_database.json','w',encoding='utf-8') as f:
                    json.dump(database, f, ensure_ascii=False, indent=2)
                print(f"    ✅ 완료! 총 문장 수: {len(database['conversations'])}")
            except Exception as e:
                print(f"    ❌ 오류: {e}")
            await asyncio.sleep(2)

    database["metadata"] = {
        "last_updated": time.strftime("%Y-%m-%d"),
        "total_conversations": len(database["conversations"]),
        "levels": {lvl: LEVELS[lvl]["count"] for lvl in LEVELS}
    }
    with open('russian_conversations_database.json','w',encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    print("🎉 데이터베이스 생성 완료!")

if __name__ == "__main__":
    asyncio.run(generate_full_database()) 