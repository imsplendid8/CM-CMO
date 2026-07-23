# API를 URL에서 바로 — 키를 폴더에 안 붙이는 방법

**팀 전원이 설정 없이** 대시보드에서 실시간 데이터를 쓰게 만드는 방법입니다.
핵심: **키는 각자 브라우저가 아니라 프록시 워커(Cloudflare)에 서버 저장** → 팀원은 아무 입력 없이 사이트만 열면 동작. (프록시 URL은 이미 툴에 기본 내장되어 있음)

## 왜 프록시가 필요한가
네이버 API는 브라우저에서 **직접 호출이 막혀** 있습니다.
- 검색·데이터랩 API → **CORS 차단**(브라우저 요청 거부)
- 검색광고 API → **HMAC 서명** 필요(비밀키를 브라우저에 노출하면 안 됨)

그래서 **본인 소유의 초경량 프록시(Cloudflare Worker · 무료)** 하나가 대신 호출합니다.

## 팀 공유 설정 (권장) — 키를 워커에 넣기, 코드 X

프록시 워커는 이미 배포돼 있습니다: `https://modooflow-naver-proxy.angle0102.workers.dev`
(이 주소는 툴에 기본 내장되어 있어 팀원이 따로 입력할 필요 없음)

Cloudflare 대시보드에서 **폼 입력만** 하면 됩니다:

1. **Workers & Pages → `modooflow-naver-proxy` → Settings → Variables and Secrets**
2. **Add** → 아래를 **Secret(Encrypt)** 로 등록:
   - `NAVER_ID`, `NAVER_SECRET` (검색·데이터랩 · developers.naver.com)
   - (검색량도 쓰면) `AD_KEY`, `AD_SECRET`, `AD_CUSTOMER` (searchad.naver.com)
3. 저장 → **Deploy**

이제 **팀원 누구든** `imsplendid8.github.io/CM-CMO/` 를 열고 툴의 **실시간 갱신**을 누르면, 아무 키 입력 없이 데이터가 들어옵니다.

> 보안: 워커 코드의 `ALLOW_ORIGIN` 이 `https://imsplendid8.github.io` 로 설정돼 있어 **우리 사이트에서만** 이 워커를 쓸 수 있습니다. (커스텀 도메인을 쓰면 그 값으로 바꾸세요)

### (선택) 개인 override — ⚙ 설정창
워커 시크릿을 안 쓰고 나 혼자 임시로 쓰거나 팀 기본값을 덮어쓸 때만: 허브 **⚙** 에 키 입력 → **이 브라우저에만** 저장(서버·깃 전송 0). 팀 공유는 안 됩니다.

## 확인
- `https://modooflow-naver-proxy.angle0102.workers.dev/health` → `{"ok":true}` (배포 성공)
- 워커 시크릿 등록 후, 툴의 **실시간 갱신** → 데이터가 들어오면 완료.

## 라우트 요약 (툴이 호출하는 경로)
| 경로 | 대상 | 용도 |
|---|---|---|
| `GET /naver/v1/search/news.json?query=` | openapi.naver.com | 뉴스 |
| `POST /naver/v1/datalab/search` | openapi.naver.com | 데이터랩 트렌드 |
| `POST /searchad/keywordstool` | api.searchad.naver.com | 검색량(자동 HMAC 서명) |

## 기존 자동화(Action)와의 관계
- **데일리 브리프·주간 검색량·트렌드**는 계속 **GitHub Actions + Secrets**로 무인 실행됩니다(변경 없음).
- 이 프록시는 **대시보드에서 즉석으로** 실시간 데이터를 볼 때 쓰는 경로입니다(키를 파일에 안 붙여도 됨). 둘은 병행 가능합니다.
