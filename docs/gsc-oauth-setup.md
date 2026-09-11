# Google Search Console OAuth 2.0 설정 가이드

이 문서는 seo-audit.html에서 실제 Google Search Console 데이터를 조회하기 위한 OAuth 2.0 설정 방법입니다.

## 1. Google Cloud Project 생성

### 1.1 프로젝트 생성
1. [Google Cloud Console](https://console.cloud.google.com/)로 이동
2. 상단의 프로젝트 선택 → "새 프로젝트" 클릭
3. 프로젝트 이름: `Modooflow-GSC` (또는 원하는 이름)
4. 프로젝트 생성 완료 기다리기

### 1.2 Search Console API 활성화
1. 프로젝트 선택 후 좌측 메뉴 → "API 및 서비스" → "라이브러리"
2. "Search Console API" 검색 → 클릭
3. "활성화" 버튼 클릭
4. 활성화 완료

## 2. OAuth 2.0 동의 화면 설정

### 2.1 동의 화면 구성
1. 좌측 메뉴 → "API 및 서비스" → "동의 화면" → "외부" 선택 → "만들기"
2. 다음 정보 입력:
   - **앱 이름**: Modooflow SEO 감사
   - **사용자 지원 이메일**: imsplendid8@gmail.com (또는 담당자 이메일)
   - **개발자 연락처 정보**: imsplendid8@gmail.com

### 2.2 범위 추가
1. "범위 추가" → `https://www.googleapis.com/auth/webmasters.readonly` 검색
   - "Search Console 읽기 전용" 선택 → 추가
2. "저장 및 계속" 클릭

### 2.3 테스트 사용자 추가 (선택사항)
- "테스트 사용자" 탭 → "사용자 추가"
- 한화손보 팀원의 Google 계정 이메일 추가
- (프로덕션 배포 시 앱 게시 필요)

## 3. OAuth 2.0 자격증명 생성

### 3.1 클라이언트 ID 생성
1. 좌측 메뉴 → "API 및 서비스" → "사용자 인증정보"
2. "사용자 인증정보 만들기" → "OAuth 2.0 클라이언트 ID"
3. 애플리케이션 유형: "웹 애플리케이션"
4. 이름: `Modooflow-Worker` (또는 원하는 이름)
5. 리디렉션 URI 추가:
   ```
   https://modooflow-naver-proxy.angle0102.workers.dev/gsc/callback
   ```
   (또는 실제 배포 도메인)
6. "만들기" → 클라이언트 ID와 클라이언트 보안 비밀번호 복사

**중요**: 다음 정보를 안전하게 보관하세요:
- **클라이언트 ID** (`GOOGLE_OAUTH_CLIENT_ID`)
- **클라이언트 보안 비밀번호** (`GOOGLE_OAUTH_CLIENT_SECRET`)

## 4. Cloudflare Worker 설정

### 4.1 환경 변수 등록
Cloudflare 대시보드에서 다음 작업을 수행합니다:

1. **Workers & Pages** → `modooflow-naver-proxy` → **Settings** → **Variables and Secrets**

2. **Secrets** (암호화됨) 탭에서 다음 추가:
   ```
   GOOGLE_OAUTH_CLIENT_ID = "YOUR_CLIENT_ID_HERE"
   GOOGLE_OAUTH_CLIENT_SECRET = "YOUR_CLIENT_SECRET_HERE"
   GOOGLE_OAUTH_REDIRECT_URI = "https://modooflow-naver-proxy.angle0102.workers.dev/gsc/callback"
   ```

### 4.2 KV 바인딩 추가
1. **Settings** → **Bindings**
2. "KV namespace 바인딩 추가"
   - 변수명: `GSC_TOKENS` (중요: 정확한 이름)
   - KV namespace: `modooflow-tokens` (또는 기존 namespace)
3. 저장

### 4.3 배포
1. **"배포"** 버튼 클릭 (또는 `wrangler deploy`)
2. 배포 완료 확인

## 5. seo-audit.html 테스트

### 5.1 로컬 테스트 (선택사항)
ALLOW_ORIGINS에 localhost 추가 후 테스트:
```javascript
const ALLOW_ORIGINS = [
  "https://imsplendid8.github.io",
  "http://localhost:8000", // 테스트용 (배포 전 제거)
];
```

### 5.2 프로덕션 테스트
1. [seo-audit.html](https://imsplendid8.github.io/CM-CMO/seo-audit.html) 열기
2. 좌측 사이드바 → "검색 성과" (📊 아이콘) 클릭
3. "GSC 계정 연결" 버튼 클릭
4. Google 로그인 및 권한 승인
5. 성공하면 GSC 데이터가 표시됨

## 6. 트러블슈팅

### 문제: "GSC client not configured"
**원인**: Cloudflare Worker에 환경 변수가 등록되지 않음
**해결**: 위의 4.1 단계를 다시 확인

### 문제: "token exchange failed"
**원인**: 클라이언트 ID/보안 비밀번호 오류 또는 리디렉션 URI 불일치
**해결**: 
- Google Cloud Console에서 자격증명 확인
- 리디렉션 URI가 정확한지 확인

### 문제: "session not found"
**원인**: 토큰이 KV에서 만료됨
**해결**: 다시 로그인하거나 KV TTL 값 증가 (현재 24시간)

### 문제: "GSC query failed"
**원인**: 
- Google 계정이 Search Console 속성에 접근 권한이 없음
- API 할당량 초과
**해결**:
- Google Search Console에서 속성에 팀원 추가
- Google Cloud Console에서 할당량 확인

## 7. 보안 주의사항

1. **클라이언트 보안 비밀번호**
   - 절대 브라우저에 노출하지 않기
   - Worker 시크릿으로만 저장
   - 실수로 커밋하지 않기

2. **리디렉션 URI**
   - HTTPS만 사용 (Google 요구사항)
   - 허용된 도메인만 등록
   - 변경 시 Google Cloud Console에서 업데이트

3. **토큰 관리**
   - 토큰은 Worker 내부에서만 관리
   - sessionId로 간접 접근
   - KV에서 자동 만료 (24시간)

## 8. 속성 선택 (향후)

현재 코드는 하드코딩된 속성(`https://www.hanwhadirect.com/`)을 사용합니다.
나중에 사용자가 선택할 수 있도록 개선하려면:

```javascript
// seo-audit.html에서
const property = "https://www.hanwhadirect.com/"; // 또는 사용자 선택
const resp = await fetch(`${DEFAULT_PROXY}/gsc/query-metrics?sessionId=${sessionId}&property=${encodeURIComponent(property)}`);
```

## 참고 자료

- [Google OAuth 2.0 문서](https://developers.google.com/identity/protocols/oauth2)
- [Search Console API 문서](https://developers.google.com/webmasters/search-console/guides/sunset-migration)
- [Cloudflare KV 문서](https://developers.cloudflare.com/workers/runtime-apis/kv/)
