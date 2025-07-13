#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Russian–Korean 2000-word JSON builder (AI-powered version)
---------------------------------------------------------
• 난이도 : 60% beginner / 30% intermediate / 10% advanced
• 카테고리: 20종에 고르게 분포
• 발음    : 한글 음차 표기
"""

import json
import random
import asyncio
import google.generativeai as genai
from datetime import datetime

# Gemini API 설정
GEMINI_API_KEY = "AIzaSyCmH1flv0HSRp8xYa1Y8oL7xnpyyQVuIw8"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 카테고리 정의
CATEGORIES = [
    "greetings", "politeness", "basic", "family", "numbers", "time", 
    "food", "colors", "body", "verbs", "transportation", "weather",
    "emotions", "animals", "house", "clothes", "technology", "nature", 
    "sports", "music"
]

# 난이도별 할당량
LEVEL_QUOTAS = {
    "beginner": 1200,     # 60%
    "intermediate": 600,   # 30%
    "advanced": 200       # 10%
}

async def generate_vocab_batch(category, level, count):
    """특정 카테고리와 난이도의 단어 배치 생성"""
    prompt = f"""
    러시아어 {level} 난이도의 "{category}" 카테고리 단어 {count}개를 생성해주세요.
    
    다음 JSON 형식으로 정확히 응답해주세요:
    [
        {{
            "russian": "привет",
            "korean": "안녕하세요",
            "pronunciation": "프리베트",
            "category": "{category}",
            "level": "{level}"
        }}
    ]
    
    요구사항:
    - 실제 사용되는 러시아어 단어만 포함
    - 한국어 번역은 가장 일반적인 뜻으로
    - 발음은 한글로 자연스럽게 표기
    - 정확히 {count}개의 단어 생성
    - JSON 형식 준수
    """
    
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: model.generate_content(prompt)
        )
        
        # JSON 파싱 시도
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:-3]
        elif response_text.startswith('```'):
            response_text = response_text[3:-3]
        
        vocab_list = json.loads(response_text)
        
        # 데이터 검증
        validated_vocab = []
        for item in vocab_list:
            if all(key in item for key in ["russian", "korean", "pronunciation", "category", "level"]):
                validated_vocab.append(item)
        
        print(f"✅ {category} ({level}) - {len(validated_vocab)}개 단어 생성 완료")
        return validated_vocab
        
    except Exception as e:
        print(f"❌ {category} ({level}) 생성 실패: {e}")
        return []

async def generate_all_vocabulary():
    """전체 2000개 단어 생성"""
    print("🚀 러시아어 2000단어 JSON 생성 시작...")
    
    all_vocabulary = []
    
    # 각 카테고리별로 단어 생성
    for category in CATEGORIES:
        print(f"\n📚 카테고리: {category}")
        
        # 난이도별 분배 (카테고리당 100개씩)
        category_quota = {
            "beginner": 60,      # 60%
            "intermediate": 30,   # 30%
            "advanced": 10       # 10%
        }
        
        for level, count in category_quota.items():
            vocab_batch = await generate_vocab_batch(category, level, count)
            all_vocabulary.extend(vocab_batch)
            
            # API 호출 간격 (할당량 관리)
            await asyncio.sleep(2)
    
    print(f"\n✅ 총 {len(all_vocabulary)}개 단어 생성 완료!")
    return all_vocabulary

def save_vocabulary_json(vocabulary, filename="russian_korean_vocab_2000.json"):
    """JSON 파일로 저장"""
    try:
        # 최종 구조 생성
        final_data = {
            "metadata": {
                "total_words": len(vocabulary),
                "categories": len(CATEGORIES),
                "levels": list(LEVEL_QUOTAS.keys()),
                "generated_at": datetime.now().isoformat(),
                "description": "러시아어-한국어 2000단어 학습 데이터베이스"
            },
            "vocabulary": vocabulary
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 파일 저장 완료: {filename}")
        
        # 통계 출력
        print("\n📊 생성 통계:")
        level_counts = {}
        category_counts = {}
        
        for word in vocabulary:
            level = word.get('level', 'unknown')
            category = word.get('category', 'unknown')
            
            level_counts[level] = level_counts.get(level, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
        
        print("난이도별 분포:")
        for level, count in level_counts.items():
            percentage = (count / len(vocabulary)) * 100
            print(f"  {level}: {count}개 ({percentage:.1f}%)")
        
        print("\n카테고리별 분포:")
        for category, count in sorted(category_counts.items()):
            print(f"  {category}: {count}개")
        
        return True
        
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return False

async def main():
    """메인 실행 함수"""
    print("="*60)
    print("🇷🇺 러시아어-한국어 2000단어 JSON 생성기")
    print("="*60)
    
    # 단어 생성
    vocabulary = await generate_all_vocabulary()
    
    if len(vocabulary) < 1000:
        print("⚠️  생성된 단어 수가 부족합니다. 다시 시도해주세요.")
        return
    
    # JSON 파일 저장
    success = save_vocabulary_json(vocabulary)
    
    if success:
        print("\n🎉 2000단어 JSON 생성 완료!")
        print("📁 파일명: russian_korean_vocab_2000.json")
        print("🔗 봇에서 사용하려면 이 파일을 russian_learning_database.json과 병합하세요.")
    else:
        print("\n❌ 파일 저장 실패")

if __name__ == "__main__":
    asyncio.run(main()) 