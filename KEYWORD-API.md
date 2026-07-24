# 실검색량·경쟁도 연동 (네이버 검색광고)

키워드 도구(`keyword-tool.html`)는 후보 키워드를 만들고 분류합니다.
**실검색량·경쟁도**는 네이버 검색광고 API로 채웁니다. (구글은 현재 미사용)

> 브라우저에서 네이버 API를 **직접 호출할 수 없습니다**(CORS 차단 + 키 노출). 그래서 두 경로로 채웁니다.

## 현재 연동 (택1, 둘 다 팀 공유)

### A) 실시간 — 프록시 경유 (권장)
키워드 도구 → 상품 선택 → 🔌 패널 → **네이버 연동 & 검색량 가져오기**.
- 워커 프록시(`/searchad/keywordstool`)가 HMAC 서명을 대신 처리 → 브라우저는 키 입력 불필요.
- 키는 워커 시크릿(`AD_KEY`/`AD_SECRET`/`AD_CUSTOMER`)에 서버 저장(팀 전원 공유). 설정 → **[docs/api-from-url.md](docs/api-from-url.md)**.

### B) 무인 자동 — 주간 Action
`.github/workflows/searchad.yml`(주간) → `scripts/naver_searchad_volume.py` → **`data/volume.json`** 갱신.
키워드 도구가 시작 시 `data/volume.json`을 자동 로드해 상품별 검색량·경쟁도를 매핑합니다(출처=검색광고).

## 도구가 읽는 형식 (`data/volume.json`)
```json
{ "source": "searchad",
  "products": { "cncr": { "keywords": {
    "암보험":      { "pc": 9000, "mobile": 76000, "comp": "높음" },
    "암보험 비교": { "pc": 250,  "mobile": 1900,  "comp": "중간" }
  } } } }
```


---
> 이전의 수동 CLI 파이프라인(`run_keywords.sh`·`naver_searchad_keywords.py`·`google_ads_keywords.py`·`merge_volume.py`)은
> 위 A(프록시)·B(주간 Action)로 대체되어 제거되었습니다. 필요 시 git 이력에서 복구 가능.
