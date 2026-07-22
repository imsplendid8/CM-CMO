# 아키텍처

## 원칙
- **자체완결 단일 HTML**: 도구 1개 = 파일 1개. 외부 라이브러리·빌드·런타임 호출 0. → GitHub Pages 직접접속 + Artifact 발행 둘 다 쉬움.
- **정적·클라이언트 전용**: 데이터는 파일 안에 상수로. 사용자 데이터(예: SERP 스크린샷)는 `localStorage`에만(전송 0).
- **공유 상품 집합**: 5개 도구 모두 동일한 상품 10종(홈·장기7·일반2)을 다룸.

## 저장소 구조
```
index.html            허브(5개 작업공간 진입)
seo-audit.html        1. 테크니컬 SEO 콘솔 (앰버)
keyword-tool.html     2. 검색광고 키워드 추출 (블루)
news-tool.html        3. 카테고리 뉴스 모니터링 (틸)
serp-tool.html        4. 검색결과 주간 아카이브 (바이올렛)
seasonal-tool.html    5. 연간 시즈널 이슈 캘린더 (로즈)
scripts/              네이버 연동 로컬서버 등
.claude/skills/cm-news-analysis/   분석 산출물 톤 스킬
.github/workflows/pages.yml         Pages 자동 배포
docs/ · STATE.md · CLAUDE.md         문서
```

## 디자인 시스템
- 폰트: Pretendard·Noto Sans KR (OFL 계열). 라이트/다크 모두 지원(`prefers-color-scheme` + `data-theme` 토글).
- 도구별 accent 색: SEO 앰버 `#e0850f` · 키워드 블루 `#2b6cb0` · 뉴스 틸 `#0e9e8e` · SERP 바이올렛 `#7c5cd6` · 시즌 로즈 `#d6456f`.
- 레이아웃: 좌측 사이드바 + 상단바 + 콘텐츠. 반응형(820px에서 사이드바 접힘).

## 브랜치·배포
- 레포 `imsplendid8/CM-CMO`, 기본 브랜치 **main**, **트렁크 기반**(짧은 브랜치 → 바로 병합).
- `pages.yml`이 main push 시 정적 사이트를 Pages로 배포. Source=GitHub Actions(설정 완료).
- Pages URL: `https://imsplendid8.github.io/CM-CMO/`.

## 새 도구 추가 절차
1. `<도구>.html` 작성(기존 도구의 사이드바/상단바/CSS 패턴 재사용, accent 색 새로 지정).
2. `index.html`에 카드 1개 추가(파일 링크·아이콘·색·설명).
3. 검증: JS 문법 `node -e 'new Function(...)'`, 렌더 Playwright(`/opt/node22/lib/node_modules/playwright`, `file://`).
4. main 병합·push → 자동 배포.

## Artifact 발행(미리보기)
- 프래그먼트 = 도구 HTML에서 `<!doctype html>`,`<html>`,`<head>`,`</head>`,`<body>`,`</body>`,`</html>` 줄 제거.
- 허브 프래그먼트는 카드 href를 각 도구의 **Artifact URL**로 치환(새 탭). 같은 파일경로로 재발행하면 같은 URL 유지.

## ⚠️ 데이터 거버넌스
- 고객·임직원 개인정보·영업비밀 **금지**. 샘플·공개·비식별/가상 데이터만.
- 뉴스·SERP는 공개 정보. 요약·시사점은 자체 분석. 광고 문구는 광고심의 검수 전제.
- API 키·토큰은 코드/커밋 금지 — `.gitignore`, GitHub Secrets, 로컬만.
