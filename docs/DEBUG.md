# 디버그 모니터링 시스템

## 개요

모든 도구와 대시보드에 **DebugMonitor** 시스템이 내장되어 문제를 자동으로 감지하고 추적합니다.

### 자동 감지 항목

- ✅ **JavaScript 에러** — 런타임 에러, 미처리 Promise rejection
- ✅ **네트워크 오류** — fetch 실패, 느린 로드, 4xx/5xx 응답
- ✅ **렌더링 상태** — 콘텐츠 로드 여부, DOM 요소 검증
- ✅ **성능 메트릭** — 데이터 로드 시간, 렌더링 성능

---

## 🐛 디버그 패널 사용법

### 1. 대시보드 (`index.html`)에서 열기

홈 화면 상단 네비게이션에서 **🐛 디버그** 버튼을 클릭하면 오른쪽에 슬라이드 패널이 나타납니다.

### 2. 패널 구성

```
┌─────────────────────────┐
│ 🐛 디버그               │ ✕
├─────────────────────────┤
│ 전체: 42    오류: 3    │
│ 경고: 7     도구: 5    │
├─────────────────────────┤
│ [최근 20개 로그]        │
│                         │
│ seo-audit              │
│ 14:32:45               │
│ [Fetch Fail] data...   │
│ (404) Not Found        │
│                         │
│ keyword-tool           │
│ 14:32:42               │
│ [JS Error] is not...   │
└─────────────────────────┘
```

### 3. 통계 읽기

| 항목 | 의미 |
|------|------|
| **전체** | 수집된 모든 로그 항목 개수 |
| **오류** | 심각한 에러 (즉시 확인 필요) |
| **경고** | 부분 실패 또는 느린 로드 (모니터 권장) |
| **도구** | 로그가 있는 도구 개수 |

---

## 📊 콘솔에서 확인하기

각 도구를 열면 자동으로 로그가 콘솔에 출력됩니다.

```javascript
// 콘솔 예시
[keyword-tool] DEBUG [Fetch Start] data/products.json
[keyword-tool] DEBUG [Fetch OK] data/products.json (127ms, 200)
[serp-tool] WARN [Fetch Fail] data/trends.json (404) Not Found
[serp-tool] ERROR [Render Failed] #trend-chart - selector not found
```

### 콘솔 필터링

```javascript
// 오류만 보기
console.log(DebugMonitor.getStatus().errors)

// 특정 도구의 로그 보기
const logs = DebugMonitor.load()
logs.filter(l => l.tool === 'keyword-tool')

// 로그 초기화
DebugMonitor.clear()
```

---

## 🔄 localStorage에서 로그 검색

브라우저 개발자 도구에서:

```javascript
// 저장된 모든 로그 로드
const logs = JSON.parse(localStorage.getItem('mf-debug-log'))
logs.slice(-10)  // 최근 10개

// 에러만 필터링
logs.filter(l => l.level === 'error')

// 특정 키워드로 검색
logs.filter(l => l.msg.includes('404'))
```

---

## 🤖 자동 모니터링 (GitHub Actions)

### health-check.yml 워크플로우

- **주기**: 6시간마다 자동 실행
- **대상**: 모든 8개 도구 (렌더링 검사)
- **실패 시**: GitHub Issues 자동 생성

```
schedule:
  - cron: '0 */6 * * *'  # KST 기준 약 09:00, 15:00, 21:00, 03:00
```

### 자동 이슈 생성 예시

제목: `⚠️ 헬스 체크: 2개 도구 문제`

본문:
```
## 🔴 헬스 체크 실패

**시간**: 2026-09-10 14:32:45

### 문제 도구
- **serp-tool.html**: Error: Timeout waiting for networkidle0
- **adcopy-tool.html**: TypeError: Cannot read property 'length' of undefined

### 확인 필요
1. 도구 렌더링 상태 확인
2. 콘솔 에러 메시지 검토
3. 네트워크 오류 확인
4. 데이터 로드 상태 검증
```

---

## 🎯 개발 중 사용 예시

### 새 기능에 에러 감지 추가

```javascript
// 도구에서 주요 데이터 로드 시
window.DEBUG?.startMeasure('products-load');
const products = await fetch('data/products.json').then(r => r.json());
window.DEBUG?.endMeasure('products-load', { count: products.length });

// 렌더링 검증
window.DEBUG?.checkRender('#product-list', 'Product list');

// 경고 로깅
if (products.length === 0) {
  window.DEBUG?.warn('No products found', { expectedMin: 1 });
}
```

### 데이터 검증

```javascript
try {
  const data = JSON.parse(result);
  window.DEBUG?.checkRender('#data-grid', 'Data grid render');
} catch (err) {
  window.DEBUG?.error('JSON parse failed', { error: err.message, data: result });
}
```

---

## 📋 로그 레벨 정의

| 레벨 | 색상 | 용도 |
|------|------|------|
| **error** | 🔴 빨강 | 기능 실패, 즉시 대응 필요 |
| **warn** | 🟠 주황 | 부분 실패, 폴백 작동, 모니터 권장 |
| **info** | 🟡 노랑 | 성능 지표, 데이터 로드 완료 |
| **debug** | ⚪ 회색 | 상세 추적, fetch 요청/응답 |

---

## 🚀 트러블슈팅

### 패널이 열리지 않음
- 브라우저 console에서 `window.DEBUG` 확인
- localStorage 용량 초과 여부 확인
- 페이지 새로고침 시도

### 로그가 저장되지 않음
- localStorage 사용 불가 확인 (프라이빗 모드, 용량 부족)
- 권한 설정 확인
- 브라우저 개발자 도구 > Application > Local Storage 확인

### 특정 도구의 에러를 못 볼 때
1. 도구를 직접 열기 (iframe 내에서는 localStorage 공유 제한)
2. 콘솔 탭에서 `[tool-name] ERROR` 검색
3. Network 탭에서 실패한 요청 확인

---

## 📝 기록 유지 정책

- **최대 저장**: 500개 항목
- **오버플로우**: 자동으로 오래된 항목 삭제
- **초기화**: `DebugMonitor.clear()` 호출 시 전체 삭제

---

## 🔗 관련 파일

- **Core**: `/scripts/debug-monitor.js`
- **Dashboard**: `/index.html` (임베드)
- **모니터링**: `/.github/workflows/health-check.yml`
- **도구들**: 모두 DebugMonitor 클래스 포함

---

## 📞 피드백

문제가 발견되면:
1. 🐛 디버그 패널에서 오류 메시지 복사
2. GitHub Issues 생성 (자동 생성되거나 수동)
3. 오류 메시지 + 발생 시간 + 재현 방법 포함
