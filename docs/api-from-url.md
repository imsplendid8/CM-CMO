# API를 URL에서 바로 — 키를 폴더에 안 붙이는 방법

기존엔 실시간 데이터를 받으려면 **키를 파일/GitHub Secrets에 붙이고 스크립트/Action을 돌려야** 했습니다.
이제 **① 허브 ⚙설정창에 키 1회 입력(브라우저에만 저장) + ② 프록시 워커 1회 배포** 로, 툴이 URL에서 바로 실시간 데이터를 가져옵니다.

## 왜 프록시가 필요한가
네이버 API는 브라우저에서 **직접 호출이 막혀** 있습니다.
- 검색·데이터랩 API → **CORS 차단**(브라우저 요청 거부)
- 검색광고 API → **HMAC 서명** 필요(비밀키를 브라우저에 노출하면 안 됨)

그래서 **본인 소유의 초경량 프록시(Cloudflare Worker · 무료)** 하나가 대신 호출합니다.

## 1) ⚙ 설정창에 키 입력 (30초)
허브 우상단 **⚙** → 키 입력 → **이 브라우저에 저장**.
- 저장 위치: **이 브라우저 localStorage 뿐**. 서버·깃허브로 전송/커밋되지 않습니다.
- 같은 오리진이라 5개 툴이 이 키를 공유해서 씁니다.

## 2) 프록시 워커 배포 (1회, 약 3분)
[Cloudflare 무료 계정](https://dash.cloudflare.com/sign-up) 후, 로컬 터미널에서:

```bash
npm install -g wrangler
cd proxy
wrangler login
wrangler deploy          # → https://modooflow-naver-proxy.<계정>.workers.dev
```

배포되면 나온 주소를 **⚙설정창 › 프록시 URL** 에 붙여넣고 저장.

### 키를 어디에 둘지 두 방식
- **(A) 설정창 방식(기본)** — 브라우저(localStorage)에 키를 두고, 매 요청 헤더로 워커에 전달. 추가 설정 없음.
- **(B) 워커 시크릿 방식(더 안전)** — 키를 브라우저에 안 두고 워커에만:
  ```bash
  wrangler secret put NAVER_ID
  wrangler secret put NAVER_SECRET
  wrangler secret put AD_KEY
  wrangler secret put AD_SECRET
  wrangler secret put AD_CUSTOMER
  ```
  이 경우 설정창엔 **프록시 URL만** 넣으면 됩니다.

> 보안 팁: `naver-proxy-worker.js` 의 `ALLOW_ORIGIN` 을 본인 Pages 도메인(`https://<계정>.github.io`)으로 좁히면, 남이 내 워커를 못 씁니다.

## 3) 확인
- `https://<워커주소>/health` → `{"ok":true}` 나오면 배포 성공.
- 툴에서 실시간 연동 버튼을 누르면 프록시를 통해 데이터가 들어옵니다.

## 라우트 요약 (툴이 호출하는 경로)
| 경로 | 대상 | 용도 |
|---|---|---|
| `GET /naver/v1/search/news.json?query=` | openapi.naver.com | 뉴스 |
| `POST /naver/v1/datalab/search` | openapi.naver.com | 데이터랩 트렌드 |
| `POST /searchad/keywordstool` | api.searchad.naver.com | 검색량(자동 HMAC 서명) |

## 기존 자동화(Action)와의 관계
- **데일리 브리프·주간 검색량·트렌드**는 계속 **GitHub Actions + Secrets**로 무인 실행됩니다(변경 없음).
- 이 프록시는 **대시보드에서 즉석으로** 실시간 데이터를 볼 때 쓰는 경로입니다(키를 파일에 안 붙여도 됨). 둘은 병행 가능합니다.
