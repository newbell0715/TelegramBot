#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
러시아어 2000단어 완성 스크립트
누락된 카테고리 (nature, sports, music)를 수동으로 추가
"""

import json
from datetime import datetime

def add_missing_categories():
    """누락된 카테고리 단어들을 수동으로 추가"""
    
    # 자연 (Nature) 카테고리 - 100개
    nature_words = {
        "beginner": [
            {"russian": "природа", "korean": "자연", "pronunciation": "프리로다"},
            {"russian": "дерево", "korean": "나무", "pronunciation": "데레보"},
            {"russian": "цветок", "korean": "꽃", "pronunciation": "츠베톡"},
            {"russian": "трава", "korean": "풀", "pronunciation": "트라바"},
            {"russian": "лес", "korean": "숲", "pronunciation": "레스"},
            {"russian": "река", "korean": "강", "pronunciation": "레카"},
            {"russian": "море", "korean": "바다", "pronunciation": "모레"},
            {"russian": "озеро", "korean": "호수", "pronunciation": "오제로"},
            {"russian": "гора", "korean": "산", "pronunciation": "고라"},
            {"russian": "небо", "korean": "하늘", "pronunciation": "네보"},
            {"russian": "солнце", "korean": "태양", "pronunciation": "솔니체"},
            {"russian": "луна", "korean": "달", "pronunciation": "루나"},
            {"russian": "звезда", "korean": "별", "pronunciation": "즈베즈다"},
            {"russian": "вода", "korean": "물", "pronunciation": "보다"},
            {"russian": "земля", "korean": "땅", "pronunciation": "젬랴"},
            {"russian": "воздух", "korean": "공기", "pronunciation": "보즈두흐"},
            {"russian": "огонь", "korean": "불", "pronunciation": "오곤"},
            {"russian": "лист", "korean": "잎", "pronunciation": "리스트"},
            {"russian": "ветка", "korean": "가지", "pronunciation": "베트카"},
            {"russian": "корень", "korean": "뿌리", "pronunciation": "코렌"},
            {"russian": "семя", "korean": "씨앗", "pronunciation": "세먀"},
            {"russian": "плод", "korean": "열매", "pronunciation": "플로드"},
            {"russian": "ягода", "korean": "베리", "pronunciation": "야고다"},
            {"russian": "грибы", "korean": "버섯", "pronunciation": "그리비"},
            {"russian": "песок", "korean": "모래", "pronunciation": "페속"},
            {"russian": "камень", "korean": "돌", "pronunciation": "카멘"},
            {"russian": "скала", "korean": "바위", "pronunciation": "스칼라"},
            {"russian": "долина", "korean": "계곡", "pronunciation": "돌리나"},
            {"russian": "поле", "korean": "들판", "pronunciation": "폴레"},
            {"russian": "луг", "korean": "초원", "pronunciation": "루그"},
            {"russian": "остров", "korean": "섬", "pronunciation": "오스트로프"},
            {"russian": "берег", "korean": "해안", "pronunciation": "베레그"},
            {"russian": "волна", "korean": "파도", "pronunciation": "볼나"},
            {"russian": "ручей", "korean": "개울", "pronunciation": "루체이"},
            {"russian": "пруд", "korean": "연못", "pronunciation": "프루드"},
            {"russian": "болото", "korean": "늪", "pronunciation": "볼로토"},
            {"russian": "пещера", "korean": "동굴", "pronunciation": "페셰라"},
            {"russian": "холм", "korean": "언덕", "pronunciation": "홀름"},
            {"russian": "вершина", "korean": "정상", "pronunciation": "베르시나"},
            {"russian": "склон", "korean": "경사", "pronunciation": "스클론"},
            {"russian": "тропа", "korean": "길", "pronunciation": "트로파"},
            {"russian": "роща", "korean": "작은 숲", "pronunciation": "로샤"},
            {"russian": "кустарник", "korean": "관목", "pronunciation": "쿠스타르니크"},
            {"russian": "мох", "korean": "이끼", "pronunciation": "모흐"},
            {"russian": "папоротник", "korean": "고사리", "pronunciation": "파포로트니크"},
            {"russian": "кора", "korean": "나무껍질", "pronunciation": "코라"},
            {"russian": "сок", "korean": "수액", "pronunciation": "소크"},
            {"russian": "тень", "korean": "그림자", "pronunciation": "텐"},
            {"russian": "роса", "korean": "이슬", "pronunciation": "로사"},
            {"russian": "иней", "korean": "서리", "pronunciation": "이네이"},
            {"russian": "радуга", "korean": "무지개", "pronunciation": "라두가"},
            {"russian": "закат", "korean": "노을", "pronunciation": "자카트"},
            {"russian": "рассвет", "korean": "새벽", "pronunciation": "라스베트"},
            {"russian": "горизонт", "korean": "지평선", "pronunciation": "고리존트"},
            {"russian": "пейзаж", "korean": "풍경", "pronunciation": "페이자시"},
            {"russian": "климат", "korean": "기후", "pronunciation": "클리마트"},
            {"russian": "сезон", "korean": "계절", "pronunciation": "세존"},
            {"russian": "весна", "korean": "봄", "pronunciation": "베스나"},
            {"russian": "лето", "korean": "여름", "pronunciation": "레토"},
            {"russian": "осень", "korean": "가을", "pronunciation": "오센"},
            {"russian": "зима", "korean": "겨울", "pronunciation": "지마"}
        ],
        "intermediate": [
            {"russian": "экология", "korean": "생태학", "pronunciation": "에콜로기야"},
            {"russian": "биосфера", "korean": "생물권", "pronunciation": "비오스페라"},
            {"russian": "атмосфера", "korean": "대기권", "pronunciation": "아트모스페라"},
            {"russian": "геология", "korean": "지질학", "pronunciation": "게올로기야"},
            {"russian": "минерал", "korean": "광물", "pronunciation": "미네랄"},
            {"russian": "кристалл", "korean": "수정", "pronunciation": "크리스탈"},
            {"russian": "эрозия", "korean": "침식", "pronunciation": "에로지야"},
            {"russian": "вулкан", "korean": "화산", "pronunciation": "불칸"},
            {"russian": "землетрясение", "korean": "지진", "pronunciation": "젬레트랴세니예"},
            {"russian": "цунами", "korean": "쓰나미", "pronunciation": "츠나미"},
            {"russian": "ураган", "korean": "허리케인", "pronunciation": "우라간"},
            {"russian": "торнадо", "korean": "토네이도", "pronunciation": "토르나도"},
            {"russian": "оползень", "korean": "산사태", "pronunciation": "오폴젠"},
            {"russian": "лавина", "korean": "눈사태", "pronunciation": "라비나"},
            {"russian": "наводнение", "korean": "홍수", "pronunciation": "나보드네니예"},
            {"russian": "засуха", "korean": "가뭄", "pronunciation": "자수하"},
            {"russian": "экосистема", "korean": "생태계", "pronunciation": "에코시스테마"},
            {"russian": "биоразнообразие", "korean": "생물다양성", "pronunciation": "비오라즈노오브라지예"},
            {"russian": "заповедник", "korean": "자연보호구역", "pronunciation": "자포베드니크"},
            {"russian": "национальный парк", "korean": "국립공원", "pronunciation": "나츠이오날니 파르크"},
            {"russian": "редкие виды", "korean": "희귀종", "pronunciation": "레드키예 비디"},
            {"russian": "исчезающие виды", "korean": "멸종위기종", "pronunciation": "이스체자유시예 비디"},
            {"russian": "мигрция", "korean": "이주", "pronunciation": "미그라츠이야"},
            {"russian": "гибернация", "korean": "겨울잠", "pronunciation": "기베르나츠이야"},
            {"russian": "фотосинтез", "korean": "광합성", "pronunciation": "포토신테즈"},
            {"russian": "опыление", "korean": "수분", "pronunciation": "오필레니예"},
            {"russian": "симбиоз", "korean": "공생", "pronunciation": "심비오즈"},
            {"russian": "хищник", "korean": "포식자", "pronunciation": "히시니크"},
            {"russian": "травоядное", "korean": "초식동물", "pronunciation": "트라보야드노예"},
            {"russian": "всеядное", "korean": "잡식동물", "pronunciation": "프세야드노예"}
        ],
        "advanced": [
            {"russian": "биогеохимический", "korean": "생물지화학적", "pronunciation": "비오게오히미체스키"},
            {"russian": "палеонтология", "korean": "고생물학", "pronunciation": "팔레온톨로기야"},
            {"russian": "стратиграфия", "korean": "지층학", "pronunciation": "스트라티그라피야"},
            {"russian": "геоморфология", "korean": "지형학", "pronunciation": "게오모르폴로기야"},
            {"russian": "гидрология", "korean": "수문학", "pronunciation": "기드롤로기야"},
            {"russian": "метеорология", "korean": "기상학", "pronunciation": "메테오롤로기야"},
            {"russian": "орнитология", "korean": "조류학", "pronunciation": "오르니톨로기야"},
            {"russian": "энтомология", "korean": "곤충학", "pronunciation": "엔토몰로기야"},
            {"russian": "ихтиология", "korean": "어류학", "pronunciation": "이흐티올로기야"},
            {"russian": "таксономия", "korean": "분류학", "pronunciation": "탁소노미야"}
        ]
    }
    
    # 스포츠 (Sports) 카테고리 - 100개
    sports_words = {
        "beginner": [
            {"russian": "спорт", "korean": "스포츠", "pronunciation": "스포르트"},
            {"russian": "игра", "korean": "게임", "pronunciation": "이그라"},
            {"russian": "футбол", "korean": "축구", "pronunciation": "풋볼"},
            {"russian": "баскетбол", "korean": "농구", "pronunciation": "바스케트볼"},
            {"russian": "волейбол", "korean": "배구", "pronunciation": "볼레이볼"},
            {"russian": "теннис", "korean": "테니스", "pronunciation": "테니스"},
            {"russian": "хоккей", "korean": "하키", "pronunciation": "호케이"},
            {"russian": "плавание", "korean": "수영", "pronunciation": "플라바니예"},
            {"russian": "бег", "korean": "달리기", "pronunciation": "베그"},
            {"russian": "прыжки", "korean": "점프", "pronunciation": "프리시키"},
            {"russian": "гимнастика", "korean": "체조", "pronunciation": "김나스티카"},
            {"russian": "бокс", "korean": "복싱", "pronunciation": "복스"},
            {"russian": "борьба", "korean": "레슬링", "pronunciation": "보르바"},
            {"russian": "велоспорт", "korean": "자전거", "pronunciation": "벨로스포르트"},
            {"russian": "лыжи", "korean": "스키", "pronunciation": "리시"},
            {"russian": "коньки", "korean": "스케이트", "pronunciation": "콘키"},
            {"russian": "мяч", "korean": "공", "pronunciation": "먀치"},
            {"russian": "команда", "korean": "팀", "pronunciation": "코만다"},
            {"russian": "игрок", "korean": "선수", "pronunciation": "이그록"},
            {"russian": "тренер", "korean": "코치", "pronunciation": "트레네르"},
            {"russian": "стадион", "korean": "경기장", "pronunciation": "스타디온"},
            {"russian": "поле", "korean": "필드", "pronunciation": "폴레"},
            {"russian": "матч", "korean": "경기", "pronunciation": "마치"},
            {"russian": "соревнование", "korean": "경쟁", "pronunciation": "소레브노바니예"},
            {"russian": "чемпионат", "korean": "챔피언십", "pronunciation": "챔피오나트"},
            {"russian": "победа", "korean": "승리", "pronunciation": "포베다"},
            {"russian": "поражение", "korean": "패배", "pronunciation": "포라셰니예"},
            {"russian": "ничья", "korean": "무승부", "pronunciation": "니치야"},
            {"russian": "гол", "korean": "골", "pronunciation": "골"},
            {"russian": "очко", "korean": "점수", "pronunciation": "오치코"},
            {"russian": "рекорд", "korean": "기록", "pronunciation": "레코르드"},
            {"russian": "медаль", "korean": "메달", "pronunciation": "메달"},
            {"russian": "кубок", "korean": "컵", "pronunciation": "쿠복"},
            {"russian": "приз", "korean": "상", "pronunciation": "프리즈"},
            {"russian": "финал", "korean": "결승", "pronunciation": "피날"},
            {"russian": "полуфинал", "korean": "준결승", "pronunciation": "폴루피날"},
            {"russian": "четвертьфинал", "korean": "8강", "pronunciation": "체트베르트피날"},
            {"russian": "тайм", "korean": "하프타임", "pronunciation": "타임"},
            {"russian": "перерыв", "korean": "휴식", "pronunciation": "페레르이프"},
            {"russian": "арбитр", "korean": "심판", "pronunciation": "아르비트르"},
            {"russian": "судья", "korean": "심판", "pronunciation": "수디야"},
            {"russian": "свисток", "korean": "호루라기", "pronunciation": "스비스톡"},
            {"russian": "штраф", "korean": "벌칙", "pronunciation": "시트라프"},
            {"russian": "фол", "korean": "파울", "pronunciation": "폴"},
            {"russian": "пенальти", "korean": "페널티", "pronunciation": "페날티"},
            {"russian": "офсайд", "korean": "오프사이드", "pronunciation": "오프사이드"},
            {"russian": "замена", "korean": "교체", "pronunciation": "자메나"},
            {"russian": "капитан", "korean": "주장", "pronunciation": "카피탄"},
            {"russian": "вратарь", "korean": "골키퍼", "pronunciation": "브라타르"},
            {"russian": "защитник", "korean": "수비수", "pronunciation": "자시트니크"},
            {"russian": "нападающий", "korean": "공격수", "pronunciation": "나파다유시"},
            {"russian": "полузащитник", "korean": "미드필더", "pronunciation": "폴루자시트니크"},
            {"russian": "левый", "korean": "왼쪽", "pronunciation": "레비"},
            {"russian": "правый", "korean": "오른쪽", "pronunciation": "프라비"},
            {"russian": "центр", "korean": "중앙", "pronunciation": "첸트르"},
            {"russian": "атака", "korean": "공격", "pronunciation": "아타카"},
            {"russian": "защита", "korean": "수비", "pronunciation": "자시타"},
            {"russian": "пас", "korean": "패스", "pronunciation": "파스"},
            {"russian": "удар", "korean": "슛", "pronunciation": "우다르"},
            {"russian": "бросок", "korean": "투구", "pronunciation": "브로속"},
            {"russian": "ловля", "korean": "캐치", "pronunciation": "로블랴"}
        ],
        "intermediate": [
            {"russian": "олимпиада", "korean": "올림픽", "pronunciation": "올림피아다"},
            {"russian": "паралимпиада", "korean": "패럴림픽", "pronunciation": "파라림피아다"},
            {"russian": "мировой рекорд", "korean": "세계기록", "pronunciation": "미로보이 레코르드"},
            {"russian": "национальный рекорд", "korean": "국가기록", "pronunciation": "나츠이오날니 레코르드"},
            {"russian": "дисквалификация", "korean": "실격", "pronunciation": "디스크발리피카츠이야"},
            {"russian": "допинг", "korean": "도핑", "pronunciation": "도핑"},
            {"russian": "антидопинг", "korean": "안티도핑", "pronunciation": "안티도핑"},
            {"russian": "спортивная медицина", "korean": "스포츠의학", "pronunciation": "스포르티브나야 메디치나"},
            {"russian": "реабилитация", "korean": "재활", "pronunciation": "레아빌리타츠이야"},
            {"russian": "физиотерапия", "korean": "물리치료", "pronunciation": "피지오테라피야"},
            {"russian": "тренировка", "korean": "훈련", "pronunciation": "트레니로프카"},
            {"russian": "кондиция", "korean": "컨디션", "pronunciation": "콘디치야"},
            {"russian": "выносливость", "korean": "지구력", "pronunciation": "비노스리보스트"},
            {"russian": "координация", "korean": "협응력", "pronunciation": "코오르디나츠이야"},
            {"russian": "гибкость", "korean": "유연성", "pronunciation": "기브코스트"},
            {"russian": "скорость", "korean": "속도", "pronunciation": "스코로스트"},
            {"russian": "сила", "korean": "힘", "pronunciation": "시라"},
            {"russian": "точность", "korean": "정확성", "pronunciation": "토치노스트"},
            {"russian": "техника", "korean": "기술", "pronunciation": "테흐니카"},
            {"russian": "тактика", "korean": "전술", "pronunciation": "타크티카"},
            {"russian": "стратегия", "korean": "전략", "pronunciation": "스트라테기야"},
            {"russian": "психология", "korean": "심리학", "pronunciation": "프시홀로기야"},
            {"russian": "мотивация", "korean": "동기부여", "pronunciation": "모티바츠이야"},
            {"russian": "концентрация", "korean": "집중", "pronunciation": "콘첸트라츠이야"},
            {"russian": "адреналин", "korean": "아드레날린", "pronunciation": "아드레날린"},
            {"russian": "травма", "korean": "부상", "pronunciation": "트라우마"},
            {"russian": "растяжение", "korean": "근육 늘림", "pronunciation": "라스탸세니예"},
            {"russian": "перелом", "korean": "골절", "pronunciation": "페렐롬"},
            {"russian": "сотрясение", "korean": "뇌진탕", "pronunciation": "소트랴세니예"},
            {"russian": "спонсор", "korean": "후원자", "pronunciation": "스폰소르"}
        ],
        "advanced": [
            {"russian": "биомеханика", "korean": "생체역학", "pronunciation": "비오메하니카"},
            {"russian": "эргономика", "korean": "인간공학", "pronunciation": "에르고노미카"},
            {"russian": "кинезиология", "korean": "운동학", "pronunciation": "키네지올로기야"},
            {"russian": "физиология", "korean": "생리학", "pronunciation": "피지올로기야"},
            {"russian": "метаболизм", "korean": "신진대사", "pronunciation": "메타볼리즘"},
            {"russian": "анаэробный", "korean": "무산소", "pronunciation": "아나에로브니"},
            {"russian": "аэробный", "korean": "유산소", "pronunciation": "아에로브니"},
            {"russian": "гликолиз", "korean": "당분해", "pronunciation": "글리콜리즈"},
            {"russian": "лактат", "korean": "젖산", "pronunciation": "лактат"},
            {"russian": "профессиональный", "korean": "프로페셔널", "pronunciation": "프로페시오날니"}
        ]
    }
    
    # 음악 (Music) 카테고리 - 100개
    music_words = {
        "beginner": [
            {"russian": "музыка", "korean": "음악", "pronunciation": "무지카"},
            {"russian": "песня", "korean": "노래", "pronunciation": "페스냐"},
            {"russian": "мелодия", "korean": "멜로디", "pronunciation": "멜로디야"},
            {"russian": "ритм", "korean": "리듬", "pronunciation": "리트름"},
            {"russian": "темп", "korean": "템포", "pronunciation": "템프"},
            {"russian": "звук", "korean": "소리", "pronunciation": "즈부크"},
            {"russian": "голос", "korean": "목소리", "pronunciation": "골로스"},
            {"russian": "петь", "korean": "노래하다", "pronunciation": "페트"},
            {"russian": "играть", "korean": "연주하다", "pronunciation": "이그라트"},
            {"russian": "слушать", "korean": "듣다", "pronunciation": "슬루샤트"},
            {"russian": "концерт", "korean": "콘서트", "pronunciation": "콘체르트"},
            {"russian": "музыкант", "korean": "음악가", "pronunciation": "무지칸트"},
            {"russian": "певец", "korean": "가수", "pronunciation": "페베츠"},
            {"russian": "певица", "korean": "여가수", "pronunciation": "페비차"},
            {"russian": "группа", "korean": "그룹", "pronunciation": "그루파"},
            {"russian": "оркестр", "korean": "오케스트라", "pronunciation": "오르케스트르"},
            {"russian": "хор", "korean": "합창단", "pronunciation": "호르"},
            {"russian": "дирижёр", "korean": "지휘자", "pronunciation": "디리죠르"},
            {"russian": "инструмент", "korean": "악기", "pronunciation": "인스트루멘트"},
            {"russian": "пианино", "korean": "피아노", "pronunciation": "피아니노"},
            {"russian": "гитара", "korean": "기타", "pronunciation": "기타라"},
            {"russian": "скрипка", "korean": "바이올린", "pronunciation": "스크리프카"},
            {"russian": "барабан", "korean": "드럼", "pronunciation": "바라반"},
            {"russian": "труба", "korean": "트럼펫", "pronunciation": "트루바"},
            {"russian": "флейта", "korean": "플루트", "pronunciation": "플레이타"},
            {"russian": "саксофон", "korean": "색소폰", "pronunciation": "삭소폰"},
            {"russian": "кларнет", "korean": "클라리넷", "pronunciation": "클라르네트"},
            {"russian": "виолончель", "korean": "첼로", "pronunciation": "비올론첼"},
            {"russian": "контрабас", "korean": "콘트라베이스", "pronunciation": "콘트라바스"},
            {"russian": "арфа", "korean": "하프", "pronunciation": "아르파"},
            {"russian": "орган", "korean": "오르간", "pronunciation": "오르간"},
            {"russian": "аккордеон", "korean": "아코디언", "pronunciation": "아코르데온"},
            {"russian": "гармошка", "korean": "하모니카", "pronunciation": "가르모시카"},
            {"russian": "ноты", "korean": "악보", "pronunciation": "노티"},
            {"russian": "тональность", "korean": "조", "pronunciation": "토날노스트"},
            {"russian": "октава", "korean": "옥타브", "pronunciation": "옥타바"},
            {"russian": "аккорд", "korean": "화음", "pronunciation": "아코르드"},
            {"russian": "гамма", "korean": "음계", "pronunciation": "가마"},
            {"russian": "до", "korean": "도", "pronunciation": "도"},
            {"russian": "ре", "korean": "레", "pronunciation": "레"},
            {"russian": "ми", "korean": "미", "pronunciation": "미"},
            {"russian": "фа", "korean": "파", "pronunciation": "파"},
            {"russian": "соль", "korean": "솔", "pronunciation": "솔"},
            {"russian": "ля", "korean": "라", "pronunciation": "랴"},
            {"russian": "си", "korean": "시", "pronunciation": "시"},
            {"russian": "мажор", "korean": "장조", "pronunciation": "마조르"},
            {"russian": "минор", "korean": "단조", "pronunciation": "미노르"},
            {"russian": "диез", "korean": "샤프", "pronunciation": "디에즈"},
            {"russian": "бемоль", "korean": "플랫", "pronunciation": "베몰"},
            {"russian": "тактовый размер", "korean": "박자", "pronunciation": "탁토비 라즈메르"},
            {"russian": "пауза", "korean": "쉼표", "pronunciation": "파우자"},
            {"russian": "стаккато", "korean": "스타카토", "pronunciation": "스타카토"},
            {"russian": "легато", "korean": "레가토", "pronunciation": "레가토"},
            {"russian": "форте", "korean": "포르테", "pronunciation": "포르테"},
            {"russian": "пиано", "korean": "피아노", "pronunciation": "피아노"},
            {"russian": "крещендо", "korean": "크레센도", "pronunciation": "크레셴도"},
            {"russian": "диминуэндо", "korean": "디미뉴엔도", "pronunciation": "디미누엔도"},
            {"russian": "адажио", "korean": "아다지오", "pronunciation": "아다지오"},
            {"russian": "аллегро", "korean": "알레그로", "pronunciation": "알레그로"},
            {"russian": "андантэ", "korean": "안단테", "pronunciation": "안단테"},
            {"russian": "престо", "korean": "프레스토", "pronunciation": "프레스토"}
        ],
        "intermediate": [
            {"russian": "композитор", "korean": "작곡가", "pronunciation": "콤포지토르"},
            {"russian": "дирижирование", "korean": "지휘", "pronunciation": "디리지로바니예"},
            {"russian": "аранжировка", "korean": "편곡", "pronunciation": "아란지로프카"},
            {"russian": "оркестровка", "korean": "관현악법", "pronunciation": "오르케스트로프카"},
            {"russian": "гармония", "korean": "화성학", "pronunciation": "가르모니야"},
            {"russian": "контрапункт", "korean": "대위법", "pronunciation": "콘트라푼크트"},
            {"russian": "импровизация", "korean": "즉흥연주", "pronunciation": "임프로비자치야"},
            {"russian": "модуляция", "korean": "전조", "pronunciation": "모둘라치야"},
            {"russian": "секвенция", "korean": "모진행", "pronunciation": "세크벤치야"},
            {"russian": "кадансы", "korean": "종지", "pronunciation": "카단시"},
            {"russian": "фугато", "korean": "푸가토", "pronunciation": "푸가토"},
            {"russian": "канон", "korean": "캐논", "pronunciation": "카논"},
            {"russian": "вариация", "korean": "변주", "pronunciation": "바리아치야"},
            {"russian": "полифония", "korean": "다성음악", "pronunciation": "폴리포니야"},
            {"russian": "гомофония", "korean": "동성음악", "pronunciation": "고모포니야"},
            {"russian": "хроматизм", "korean": "반음계", "pronunciation": "흐로마티즘"},
            {"russian": "диссонанс", "korean": "불협화음", "pronunciation": "디소난스"},
            {"russian": "консонанс", "korean": "협화음", "pronunciation": "콘소난스"},
            {"russian": "интервал", "korean": "음정", "pronunciation": "인테르발"},
            {"russian": "унисон", "korean": "유니즌", "pronunciation": "우니손"},
            {"russian": "октава", "korean": "옥타브", "pronunciation": "옥타바"},
            {"russian": "квинта", "korean": "5도", "pronunciation": "크빈타"},
            {"russian": "кварта", "korean": "4도", "pronunciation": "크바르타"},
            {"russian": "терция", "korean": "3도", "pronunciation": "테르치야"},
            {"russian": "секунда", "korean": "2도", "pronunciation": "세쿤다"},
            {"russian": "септима", "korean": "7도", "pronunciation": "세프티마"},
            {"russian": "нона", "korean": "9도", "pronunciation": "노나"},
            {"russian": "транспозиция", "korean": "이조", "pronunciation": "트란스포지치야"},
            {"russian": "каденция", "korean": "카덴차", "pronunciation": "카덴치야"},
            {"russian": "рондо", "korean": "론도", "pronunciation": "론도"}
        ],
        "advanced": [
            {"russian": "додекафония", "korean": "12음기법", "pronunciation": "도데카포니야"},
            {"russian": "сериализм", "korean": "세리얼리즘", "pronunciation": "세리알리즘"},
            {"russian": "алеаторика", "korean": "우연성음악", "pronunciation": "알레아토리카"},
            {"russian": "микротональность", "korean": "미분음", "pronunciation": "미크로토날노스트"},
            {"russian": "спектрализм", "korean": "스펙트럼주의", "pronunciation": "스펙트랄리즘"},
            {"russian": "минимализм", "korean": "미니멀리즘", "pronunciation": "미니말리즘"},
            {"russian": "пуантилизм", "korean": "점묘주의", "pronunciation": "푸안티리즘"},
            {"russian": "экспрессионизм", "korean": "표현주의", "pronunciation": "에크스프레시오니즘"},
            {"russian": "неоклассицизм", "korean": "신고전주의", "pronunciation": "네오클라시치즘"},
            {"russian": "авангард", "korean": "아방가르드", "pronunciation": "아반가르드"}
        ]
    }
    
    # 기존 파일 로드
    try:
        with open('russian_korean_vocab_2000.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ 기존 파일을 찾을 수 없습니다!")
        return
    
    # 누락된 카테고리 추가
    missing_categories = [
        ("nature", nature_words),
        ("sports", sports_words),
        ("music", music_words)
    ]
    
    added_count = 0
    
    for category, words_dict in missing_categories:
        print(f"\n📚 {category} 카테고리 추가 중...")
        
        for level, words in words_dict.items():
            for word in words:
                word["category"] = category
                word["level"] = level
                data["vocabulary"].append(word)
                added_count += 1
    
    # 메타데이터 업데이트
    data["metadata"]["total_words"] = len(data["vocabulary"])
    data["metadata"]["generated_at"] = datetime.now().isoformat()
    
    # 파일 저장
    with open('russian_korean_vocab_2000.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 완료! {added_count}개 단어 추가")
    print(f"📊 총 단어 수: {len(data['vocabulary'])}개")
    
    # 최종 통계
    level_counts = {}
    category_counts = {}
    
    for word in data["vocabulary"]:
        level = word.get('level', 'unknown')
        category = word.get('category', 'unknown')
        
        level_counts[level] = level_counts.get(level, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1
    
    print("\n📊 최종 통계:")
    print("난이도별 분포:")
    for level, count in level_counts.items():
        percentage = (count / len(data["vocabulary"])) * 100
        print(f"  {level}: {count}개 ({percentage:.1f}%)")
    
    print("\n카테고리별 분포:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}개")

if __name__ == "__main__":
    print("🔧 누락된 카테고리 추가 중...")
    add_missing_categories()
    print("\n🎉 2000단어 JSON 완성!") 