# 빠른 시작 가이드 — Modooflow OAuth 대시보드

팀원들이 개인화된 마케팅 인사이트를 받을 수 있는 대시보드를 로컬에서 실행하거나 GitHub Actions로 자동화하는 방법입니다.

---

## 1️⃣ 로컬 개발 환경 (5분 설정)

### 전제 조건
- **Node.js** 18+ (확인: `node --version`)
- **Python** 3.10+ (확인: `python3 --version`)
- **npm** (확인: `npm --version`)

### 설정 단계

#### 1-1. 저장소 클론 및 의존성 설치
```bash
# 이미 클론한 경우 생략
cd CM-CMO

# 패키지 설치
npm install
pip install anthropic pydantic
```

#### 1-2. 환경 변수 설정
```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일에 API 키 입력
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
```

Anthropic API 키는 [여기서](https://console.anthropic.com/account/keys) 발급받습니다.

#### 1-3. 서버 시작
```bash
npm start
# 또는: node server.js
```

출력 예시:
```
╔════════════════════════════════════════════════════════════════════════╗
║           Modooflow OAuth 대시보드 서버 시작                            ║
╚════════════════════════════════════════════════════════════════════════╝

🚀 서버: http://localhost:3000
📊 대시보드: http://localhost:3000/oauth-dashboard.html
```

#### 1-4. 브라우저에서 접속
- 대시보드: [http://localhost:3000/oauth-dashboard.html](http://localhost:3000/oauth-dashboard.html)
- "📱 데모 로그인" 버튼 클릭 → 샘플 대시보드 확인

---

## 2️⃣ GitHub Actions 자동화 (SA 썸네일 생성)

### 전제 조건
- GitHub Repository **Secrets** 설정

### 설정 단계

#### 2-1. GitHub Secrets 추가
1. Repository 페이지 → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭
3. 다음 정보 입력:
   - **Name**: `ANTHROPIC_API_KEY`
   - **Secret**: Claude API 키 (예: `sk-ant-...`)
4. **Add secret** 클릭

#### 2-2. 워크플로우 확인
1. Repository 페이지 → **Actions** 탭
2. **SA Thumbnail Auto-Generation** 워크플로우 확인

#### 2-3. 수동으로 실행 (테스트)
1. **Actions** 탭 → **SA Thumbnail Auto-Generation**
2. **Run workflow** 클릭
3. 옵션 선택 (기본값 OK):
   - Limit: 8 (최대 생성 개수)
   - Product: 빈 값 (전체 상품)
   - Force: false (기존 이미지는 유지)
4. **Run workflow** 클릭

#### 2-4. 자동 스케줄 설정
- **매주 월요일 08:00 UTC** (한국 시간 월요일 17:00) 자동 실행
- 수동으로도 언제든지 실행 가능

---

## 3️⃣ 팀원 가이드

### 대시보드 접속
1. 로컬 서버 실행 또는 프로덕션 URL 접속
2. "📱 데모 로그인" 클릭
3. 역할별 맞춤 KPI, 추천사항, 경고 확인

### 데이터 해석

#### KPI (핵심 지표)
| 지표 | 설명 |
|------|------|
| 월별 신규등록 | 해당 달 신규 가입자 수 |
| 검색광고 ROI | 광고비 대비 수익률 |
| 활성 캠페인 | 운영 중인 캠페인 수 |
| 평균 CPC | 클릭당 평균 광고비 |

#### 추천사항 (Action Items)
- 즉시 실행 가능한 마케팅 활동
- 역할(검색광고/콘텐츠/소재)에 따라 맞춤 제공
- 데이터 기반의 실행 우선순위 제시

#### 경고 (Alerts)
- **🔴 높음**: 긴급 대응 필요
- **🟡 중간**: 주의 및 계획 필요

---

## 🧪 테스트 명령어

### API 테스트
```bash
# 데모 대시보드 생성
curl -X POST http://localhost:3000/api/personalized-dashboard \
  -H "Authorization: Bearer demo_token_user_001" \
  -H "Content-Type: application/json"

# 로그인한 사용자 정보 조회
curl -X GET http://localhost:3000/api/me \
  -H "Authorization: Bearer demo_token_user_001"

# 사용 가능한 사용자 목록 (개발용)
curl -X GET http://localhost:3000/api/users
```

### Python 스크립트 테스트
```bash
# SA 썸네일 생성 (로컬 테스트)
# 주의: ANTHROPIC_API_KEY 환경변수 설정 필수
export ANTHROPIC_API_KEY="sk-ant-..."

python3 scripts/generate_sa_thumbnails.py --limit 2 --product driver
```

---

## ⚠️ 주의사항

### 보안
- **API 키는 절대 커밋하지 마세요**
  - `.env` 파일은 `.gitignore`에 포함되어 있습니다
  - GitHub Secrets를 통해서만 관리하세요

- **로컬 개발에서만 데모 로그인 사용**
  - 프로덕션에서는 실제 OAuth 토큰 검증 필수

### 비용
- Claude API: 실제 호출 시 비용 발생
  - 개발 환경에서는 로컬 테스트로 최소화
  - GitHub Actions 자동화는 주간 1회만 실행

### 데이터
- 샘플 데이터: 공개 정보 기반 (MARKETING_SIGNALS)
- 실제 운영 데이터는 별도로 연동 (추후 구현)
- 개인정보는 저장하지 않습니다

---

## 🔧 다음 단계 (추후 구현)

### 우선순위 높음
- [ ] 실제 OAuth (Google, GitHub) 토큰 검증
- [ ] 실제 마케팅 신호 데이터 연동
- [ ] 데이터베이스 (Cloudflare D1) 연동
- [ ] 팀원별 권한 관리

### 우선순위 중간
- [ ] 대시보드 공유 기능
- [ ] 데이터 시각화 (차트 추가)
- [ ] 일일/주간 이메일 브리프
- [ ] 접속 분석 및 사용률 모니터링

### 우선순위 낮음
- [ ] 다국어 지원
- [ ] 모바일 앱
- [ ] Slack 봇 통합

---

## 📞 문제 해결

| 문제 | 원인 | 해결 |
|------|------|------|
| "Cannot find module 'express'" | npm 설치 미완료 | `npm install` 실행 |
| "ANTHROPIC_API_KEY not found" | 환경변수 미설정 | `export ANTHROPIC_API_KEY=...` |
| "port 3000 already in use" | 포트 충돌 | `PORT=3001 npm start` |
| API 응답 오류 | API 키 무효 | 키 유효성 확인 후 재시도 |
| 브라우저 접속 불가 | 방화벽/프록시 | localhost 대신 127.0.0.1 시도 |

---

## 📚 참고 문서

- [OAuth 대시보드 전체 설정 가이드](./OAUTH_DASHBOARD_SETUP.md)
- [아키텍처 및 설계](./architecture.md)
- [마케팅 신호 데이터](./daily-brief.md)

---

**마지막 업데이트**: 2026년 9월 5일
