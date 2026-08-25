# SERP 기반 보험종목 이미지

## 현재 사용 자산: 3D 애니메이션 v3

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
| `golf-hole-animation-v3.png` | 홀 바로 앞 골프공과 기뻐하는 골퍼 |
| `dental-consult-animation-v3.png` | 치아 모형을 보는 치과 상담 |
| `health-check-animation-v3.png` | 일상 혈압 측정 |
| `family-baby-animation-v3.png` | 임신한 부부와 아기 신발 |
| `travel-airport-animation-v3.png` | 공항·비행기·여행가방 |
| `student-campus-animation-v3.png` | 해외 캠퍼스 도착과 여행가방 |
| `event-safety-animation-v3.png` | 공연장 케이블 커버 안전점검 |

앱은 원본을 214×214 canvas에 중앙 크롭하고 선택적 확대·색감만 적용한다. 상품명, SERP 소구, 브랜드명은 이미지 바깥의 설명과 메타데이터에만 기록한다.
