# 고도화 검토 — API·MCP·OSS·Claude 스킬

> 실제로 붙일 수 있는 것만, 효용/노력순으로. 원칙: 자체완결 정적 앱 유지 + 키는 워커·Secrets·로컬만.

## 1) API 연동 (보험사·포털)

### 현실
- **보험사 공개 API는 거의 없음** — 개별 손보사는 공개 REST를 제공하지 않음(가격·상품은 스크래핑/제휴 영역, ToS 주의).
- 그래서 실질 소스는 **공공데이터 + 포털(네이버·카카오)** 이 답.

### 붙일 만한 것 (효용 높음)
| 소스 | 무료 | 쓸 곳 | 효과 |
|---|---|---|---|
| **소방청 화재발생정보** (data.go.kr) | ✅ | 🔥주택화재 수요 트리거 | ‘대형화재’를 뉴스가 아닌 **실통계**로 감지 → 선제 대응 신호 |
| **기상청 특보/예보** (data.go.kr·KMA) | ✅ | 시즌 툴·트리거(장마·한파·폭염) | 누수·동파·폭염 관련 담보 캠페인 타이밍 자동화 |
| **도로교통공단 사고통계** (data.go.kr) | ✅ | 운전자보험 트리거 | 스쿨존·명절 사고 시즌 신호 |
| **한국은행/통계청 지표** | ✅ | 업계 동향 배경 | 가계·물가 등 매크로 맥락(선택) |
| 네이버 검색/데이터랩/검색광고 | ✅ | (연동됨) | 뉴스·트렌드·검색량 |
| 카카오(아래 MCP) | ✅ | 알림·메모 | 텔레그램 대체/병행 |

→ **우선순위 1**: 소방청·기상청 API를 `scripts/`에 붙여 **수요 트리거를 실데이터로** 채우기(주간 Action). 지금은 트리거가 정성 정의(TRIGGERS) — 실통계로 뒷받침하면 설득력↑.

## 2) MCP (이 세션에서 이미 사용 가능)
- **PlayMCP · NaverSearch** (카카오 공식): `search_news`·`search_webkr`·`datalab_search` 등 → 뉴스 수집·분석을 **Claude가 직접** 수행(스킬과 결합). 프록시 없이도 분석 파이프라인 구성 가능(운영은 프록시, 편집·분석은 MCP).
- **PlayMCP · KakaotalkChat(MemoChat)**: 카카오 ‘나에게’ 메모 → **텔레그램과 병행 알림** 채널로. (초기 요구였던 카카오 알림을 MCP로 부활 가능)
- **GitHub MCP**: PR·이슈·Actions 제어(이미 사용 중).

→ **우선순위 2**: 데일리 브리프/뉴스 분석을 **MCP(NaverSearch)+cm-news-analysis 스킬**로 자동 생성하는 흐름 정식화.

## 3) 타인 레포(OSS)
`docs/oss-leverage.md` 참조. 반영됨: Pretendard·Playwright·pixelmatch·Unlighthouse·advertools.
추가 후보: **date-holidays**(공휴일 자동→시즌), **resemble.js/odiff**(SERP diff 정밀), **trafilatura**(뉴스 본문 추출).

## 4) Claude 스킬
현재: `cm-news-analysis`(분석 톤), `insurance-terms`(약관 용어→소비자 표현).
추가 후보:
- **brand-contract-advisor** — 네이버 브랜드검색 단가표 + 검색량으로 3개월 유지 vs 재계약 판단(#2 기능과 연계).
- **card-news-summary** — 뉴스 헤드라인 묶음 → 카드뉴스 요약 자동 생성.
- **seo-copy** — 상품별 title/meta/H1 카피 초안(광고심의 전 초안).

## 실행 로드맵(제안)
1. 소방청·기상청 API → 수요 트리거 실데이터화 (Action 1~2개 추가)
2. NaverSearch MCP + cm-news-analysis 스킬로 뉴스 분석 자동화
3. (사용자 대기 중) #2 브랜드·계약: 단가표 기반 + brand-contract-advisor 스킬
4. 카카오 메모챗 병행 알림(선택)
