# OAuth 팀 대시보드 구축 가이드

## 개요

**Modooflow OAuth 대시보드**는 CM-CMO 팀원들이 개인화된 마케팅 인사이트를 받을 수 있는 시스템입니다.

- 🔐 **OAuth 인증**: Google/GitHub 로그인 지원
- 📊 **개인화 대시보드**: 담당 상품별 맞춤 분석
- 🤖 **Claude API 연동**: AI 기반 마케팅 추천사항
- 📱 **반응형 UI**: 모바일 최적화

---

## 빠른 시작 (5분)

### 1️⃣ 대시보드 페이지 추가

이미 생성된 파일:
- `oauth-dashboard.html` - 프론트엔드
- `api/personalized-dashboard.js` - 백엔드 로직

### 2️⃣ index.html에 링크 추가

```html
<!-- index.html의 TOOLS 섹션에 추가 -->
<div class="tool-card" onclick="window.location.href='oauth-dashboard.html'">
  <div class="tool-icon">👥</div>
  <h3>팀 대시보드</h3>
  <p>개인화된 마케팅 인사이트 (OAuth 로그인)</p>
</div>
```

### 3️⃣ 데모 테스트

브라우저에서 열기:
```
https://yourdomain.com/oauth-dashboard.html
```

좌측 상단 "📱 데모 로그인" 버튼 클릭 → 샘플 대시보드 표시

---

## 아키텍처

```
사용자 브라우저
    ↓
oauth-dashboard.html (React 불필요, 순수 JS)
    ↓
[프론트엔드]
  - OAuth 로그인 처리
  - 토큰 저장 (localStorage)
  - 대시보드 UI 렌더링
    ↓
    ↓
[백엔드 선택]
    ↓
┌─────────────────────┬─────────────────────┐
│                     │                     │
A) Express.js         B) Cloudflare Worker  C) AWS Lambda
   (로컬 개발용)        (프로덕션용)          (확장용)
│                     │                     │
└─────────────────────┴─────────────────────┘
    ↓
personalized-dashboard.js
    ↓
Claude API
    ↓
생성된 KPI, 추천사항, 경고
```

---

## 구현 방법별 가이드

### A) 로컬 개발 (Express.js)

**설치**:
```bash
npm install express cors dotenv @anthropic-ai/sdk
```

**server.js 작성**:
```javascript
const express = require("express");
const cors = require("cors");
require("dotenv").config();

const { createDashboardHandler } = require("./api/personalized-dashboard.js");

const app = express();
app.use(cors());
app.use(express.json());

// 대시보드 엔드포인트
app.post("/api/personalized-dashboard", createDashboardHandler());

// 정적 파일 제공
app.use(express.static("."));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`서버 시작: http://localhost:${PORT}`);
});
```

**환경 변수 (.env)**:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```

**실행**:
```bash
node server.js
```

**테스트**:
```bash
curl -X POST http://localhost:3000/api/personalized-dashboard \
  -H "Authorization: Bearer demo_token_user_001" \
  -H "Content-Type: application/json"
```

---

### B) Cloudflare Workers (프로덕션)

**worker.js에 추가**:
```javascript
// /proxy/naver-proxy-worker.js의 기존 코드에 추가

import { handleDashboardRequest } from "./api/personalized-dashboard.js";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 대시보드 API 라우트
    if (url.pathname === "/api/personalized-dashboard" && request.method === "POST") {
      // Claude API 키 전달
      const dashboardRequest = new Request(request, {
        headers: {
          ...Object.fromEntries(request.headers),
          "x-api-key": env.ANTHROPIC_API_KEY
        }
      });
      return handleDashboardRequest(dashboardRequest);
    }

    // 기존 라우트...
    return handleOtherRoutes(request, env);
  }
};
```

**wrangler.toml에 시크릿 추가**:
```toml
[env.production]
vars = { ENVIRONMENT = "production" }

[[env.production.secrets]]
ANTHROPIC_API_KEY = "sk-ant-xxxxxxxxxxxx"
```

**배포**:
```bash
wrangler deploy --env production
```

---

### C) OAuth 제공자 설정 (실제 구성)

#### Google OAuth 설정

**1️⃣ Google Cloud Console에서:**

1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 새 프로젝트 생성:
   - Project name: `CM-CMO`
   - Organization: Hanwha (선택사항)
3. **APIs & Services > OAuth consent screen** 클릭
   - User Type: "외부" 선택 → CREATE
   - App name: `Modooflow 팀 대시보드`
   - User support email: team@hanwha.com
   - Developer contact: team@hanwha.com
   - SAVE AND CONTINUE
4. **Credentials > Create Credentials > OAuth client ID** 클릭
   - Application type: **웹 애플리케이션**
   - Name: `Modooflow Dashboard`
   - Authorized redirect URIs 추가:
     ```
     https://imsplendid8.github.io/CM-CMO/oauth/google/callback
     https://yourdomain.com/oauth/google/callback
     ```
   - CREATE
5. **Client ID 복사** (형식: `xxx-yyy-zzz.apps.googleusercontent.com`)

**2️⃣ 대시보드에 입력:**

1. https://imsplendid8.github.io/CM-CMO/oauth-dashboard.html 열기
2. **⚙️ OAuth 설정** 클릭
3. Google Client ID 입력 → **💾 저장**

#### GitHub OAuth 설정

**1️⃣ GitHub에서:**

1. [GitHub Settings > Developer settings > OAuth Apps](https://github.com/settings/developers) 접속
2. **New OAuth App** 클릭
3. 설정 입력:
   ```
   Application name: Modooflow
   Homepage URL: https://imsplendid8.github.io/CM-CMO/
   Authorization callback URL: https://imsplendid8.github.io/CM-CMO/oauth/github/callback
   ```
4. **Register application** 클릭
5. **Client ID 복사** (Settings에 표시됨)

**2️⃣ 대시보드에 입력:**

1. https://imsplendid8.github.io/CM-CMO/oauth-dashboard.html 열기
2. **⚙️ OAuth 설정** 클릭
3. GitHub Client ID 입력 → **💾 저장**

---

### OAuth 콜백 핸들러 (백엔드 필수)

OAuth 로그인 후 콜백 처리를 위해 **백엔드 서버** 필요:

**Express.js 예시** (`/oauth/google/callback`):
```javascript
app.get("/oauth/google/callback", async (req, res) => {
  const { code } = req.query;
  
  // 1. code를 액세스 토큰으로 교환
  const token = await exchangeCodeForToken(code, "google");
  
  // 2. 토큰 검증 & 사용자 정보 조회
  const user = await verifyToken(token, "google");
  
  // 3. localStorage 토큰 설정 후 대시보드로 리다이렉트
  res.redirect(`/oauth-dashboard.html?token=${token}&user=${user.id}`);
});
```

**프로덕션 배포 필수 사항:**
- ✅ HTTPS (OAuth 필수)
- ✅ 콜백 핸들러 구현 (Express/Cloudflare/AWS Lambda)
- ✅ 토큰 교환 엔드포인트
- ✅ 사용자 정보 조회 엔드포인트

---

## Claude API 연동

### 자동 대시보드 생성

```javascript
// personalized-dashboard.js의 generatePersonalizedDashboard() 함수
// 실제 Claude API 호출:

const response = await client.messages.create({
  model: "claude-opus-5",
  max_tokens: 2048,
  system: systemPrompt,  // 사용자 역할 기반 커스텀
  messages: [
    {
      role: "user",
      content: `분석 데이터:
        - 담당상품: ${products}
        - 마케팅신호: ${signals}
        
        KPI, 추천사항, 경고를 JSON으로 생성하세요.`
    }
  ]
});
```

### 토큰 비용 절감

```javascript
// 프롬프트 캐싱 활용
const response = await client.messages.create({
  model: "claude-opus-5",
  max_tokens: 2048,
  system: [
    {
      type: "text",
      text: stableSystemPrompt,
      cache_control: { type: "ephemeral" }  // 5분 캐시
    }
  ],
  messages: [
    {
      role: "user",
      content: userSpecificPrompt
    }
  ]
});

// 결과
console.log(response.usage.cache_read_input_tokens);  // ~0.1x 비용
```

---

## 사용자 관리

### 사용자 추가

**api/personalized-dashboard.js의 USER_PREFERENCES 수정**:

```javascript
const USER_PREFERENCES = {
  user_001: { /* 기존 */ },
  user_new: {
    id: "user_new",
    name: "홍길동",
    email: "hong.gildong@hanwha.com",
    role: "검색광고 팀장",
    products: ["home", "driver", "golf"],
    analysisType: "search",
    marketingFocus: "검색광고 ROI 최대화"
  }
};
```

### 데이터 동기화 (선택)

```javascript
// DB에서 사용자 데이터 로드
async function loadUserPreferences(userId) {
  const user = await database.query(
    "SELECT * FROM users WHERE id = ?", 
    [userId]
  );
  return user;
}
```

---

## 테스트

### 단위 테스트

```javascript
// test.js
const { generateDefaultDashboard, authenticateUser } = require("./api/personalized-dashboard.js");

// 테스트: 대시보드 생성
const testUser = { id: "user_001", analysisType: "search" };
const dashboard = generateDefaultDashboard(testUser);

console.assert(dashboard.kpis.length > 0, "KPI 필수");
console.assert(dashboard.recommendations.length > 0, "추천사항 필수");
console.assert(dashboard.alerts.length > 0, "경고 필수");

console.log("✅ 모든 테스트 통과");
```

### 통합 테스트

```bash
# 데모 로그인 테스트
curl -X POST http://localhost:3000/api/personalized-dashboard \
  -H "Authorization: Bearer demo_token_user_001"

# 응답 예시:
# {
#   "success": true,
#   "user": {"id": "user_001", "name": "김마케팅"},
#   "dashboard": {
#     "kpis": [...],
#     "recommendations": [...],
#     "alerts": [...]
#   }
# }
```

---

## 보안 체크리스트

- [ ] HTTPS 사용 (OAuth 필수)
- [ ] CSRF 보호 추가
- [ ] 토큰 만료 시간 설정 (권장: 1시간)
- [ ] 민감 정보 로그 제외
- [ ] API 키 환경변수로 관리
- [ ] CORS 설정 제한

```javascript
// CORS 설정 예시
const cors = require("cors");
app.use(cors({
  origin: ["https://yourdomain.com", "https://app.yourdomain.com"],
  credentials: true
}));
```

---

## 성능 최적화

### 캐싱 전략

```javascript
// Redis 캐싱 (선택)
const redis = require("redis");
const client = redis.createClient();

async function getCachedDashboard(userId) {
  const cached = await client.get(`dashboard:${userId}`);
  if (cached) return JSON.parse(cached);
  
  const dashboard = await generatePersonalizedDashboard(userId);
  await client.setex(`dashboard:${userId}`, 3600, JSON.stringify(dashboard));
  return dashboard;
}
```

### 배치 처리

```javascript
// 매일 밤 모든 팀원의 대시보드 미리 생성
async function prebuildDashboards() {
  for (const userId in USER_PREFERENCES) {
    const user = USER_PREFERENCES[userId];
    const dashboard = await generatePersonalizedDashboard(userId, user);
    await cache.set(`dashboard:${userId}`, dashboard, 86400);  // 24시간
  }
}
```

---

## 문제 해결

| 문제 | 해결법 |
|------|-------|
| "토큰이 없습니다" 에러 | localStorage에 토큰 확인, 로그인 다시 시도 |
| Claude API 타임아웃 | 프롬프트 크기 축소, max_tokens 감소 |
| 대시보드가 로드되지 않음 | 브라우저 콘솔 확인, 네트워크 탭에서 요청 상태 확인 |
| OAuth 콜백 실패 | 리다이렉트 URI 설정 확인, HTTPS 사용 확인 |

---

## 다음 단계

1. **팀 협업 기능**: 대시보드 공유, 댓글 기능
2. **데이터 시각화**: Chart.js/D3로 차트 추가
3. **자동화**: 일일/주간 이메일 브리프
4. **모니터링**: 대시보드 접속 분석, 기능별 사용률

---

## 지원

질문이나 버그 리포트: GitHub Issues 또는 팀 Slack #마케팅-개발

**마지막 업데이트**: 2026년 9월 5일
