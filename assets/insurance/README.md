# SERP 기반 보험종목 이미지

## 현재 사용 자산: 3D 애니메이션 v3·v4

- 생성 모드: 신규 생성(ImageGen), 2026-08-26
- 스타일 참조: 사용자가 제공한 SERP 썸네일의 3D 애니메이션 느낌과 정사각형 구도만 참조
- 공통 프롬프트: `premium stylized 3D animated feature-film frame, rounded miniature proportions, slightly oversized heads, large expressive eyes, smooth toy-like materials, clearly illustrated and not a photograph`
- 출력 기준: 1:1 정사각형, 214×214에서도 피사체와 사고·상황이 즉시 식별됨
- 무문자 기준: 이미지 생성과 canvas 합성 모두 텍스트·글자·숫자·로고·UI를 삽입하지 않음
- 안전 기준: 부상·공포·경쟁사 고유 캐릭터·브랜드·수치·할인 표현 제외

| 파일 | 장면 |
|---|---|
| `home-fire-animation-v3.png` | 실외기 화재와 놀란 가족 |
| `home-leak-animation-v3.png` | 천장 누수와 걱정하는 거주자 |
| `calculator-animation-v3.png` | 숫자와 기호가 없는 3D 보험료 계산기 |
| `driver-safe-animation-v3.png` | 안전벨트를 맨 운전자와 앞차 |
| `driver-schoolzone-animation-v4.png` | 스쿨존 앞에서 감속하는 운전자 |
| `driver-accident-animation-v4.png` | 가벼운 접촉사고 현장을 확인하는 운전자 |
| `driver-rain-animation-v4.png` | 비 오는 저녁 도로에서 방어운전하는 운전자 |
| `golf-hole-animation-v3.png` | 홀 바로 앞 골프공과 기뻐하는 골퍼 |
| `dental-consult-animation-v3.png` | 치아 모형을 보는 치과 상담 |
| `health-check-animation-v3.png` | 일상 혈압 측정 |
| `family-baby-animation-v3.png` | 임신한 부부와 아기 신발 |
| `travel-airport-animation-v3.png` | 공항·비행기·여행가방 |
| `student-campus-animation-v3.png` | 해외 캠퍼스 도착과 여행가방 |
| `event-safety-animation-v3.png` | 공연장 케이블 커버 안전점검 |

앱은 원본을 214×214 canvas에 중앙 크롭하고 선택적 확대·색감만 적용한다. 상품명, SERP 소구, 브랜드명은 이미지 바깥의 설명과 메타데이터에만 기록한다.

## 월간 제안 자동화

- 매월 1일 09:30 KST에 직전 35일 SERP 패턴을 기준으로 상품별 이미지 4장 세트를 갱신한다.
- 각 상품의 후보 원본 5장 중 서로 다른 4장을 순환 선정하므로 한 세트 안에서 같은 원본을 반복하지 않는다.
- 월별 결과는 `data/adcopy/image-plans/YYYY-MM.json`에 보존한다.
- 이 자동화는 승인된 이미지 라이브러리에서 새 세트를 제안하는 방식이다. 외부 이미지 API 호출이나 유료 이미지 생성은 자동 실행하지 않는다.

## 생성 대기열과 완료 처리

- `scripts/image_generation_queue.py`가 `data/adcopy/image-generation-queue.json`에 상품별 슬롯·프롬프트·참고 원본·예상 파일 경로를 저장한다.
- `pending`은 이미지가 덜 만들어진 실패 상태가 아니라, 실제 생성기가 아직 연결되지 않은 상태다. 전월 원본은 스타일 참고용으로만 남긴다.
- 외부 생성기 또는 운영자가 `assets/insurance/generated/<상품>-<월>-<슬롯>.png`를 저장한 뒤 `python scripts/image_generation_queue.py --sync`를 실행하면, 파일이 확인된 슬롯만 계획의 실제 asset으로 승격된다.
- 파일이 없는 상태에서 다른 보험종목 이미지를 끼워 넣지 않는다. 이 규칙이 썸네일 혼입을 막는다.
