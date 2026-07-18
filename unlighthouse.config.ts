// unlighthouse.config.ts
// 한화손보 장기CM(CM사업부) 담당 URL — 테크니컬 SEO 실측 크롤 설정
// 도구: harlan-zw/unlighthouse (MIT) · https://github.com/harlan-zw/unlighthouse
// 실행: npx unlighthouse --config-file unlighthouse.config.ts
//   → 크롤 후 나온 JSON을 index.html(범용 PRO)의 "크롤러 결과 불러오기"에 붙여넣어 To-Do 자동화
import { defineConfig } from 'unlighthouse'

export default defineConfig({
  // 모바일 우선색인 기준 — 실제 색인은 m.hanwhadirect.com
  site: 'https://m.hanwhadirect.com',
  scanner: {
    device: 'mobile',
    samples: 1,
    // ▼ CM사업부 담당 라우트만 (TM·오프라인·자동차 제외)
    include: [
      '/',                       // 다이렉트 홈(메인 태그)
      '/ltr/hrmf/**',            // 주택화재 (한화 다이렉트 직접)
      '/ltr/golf/**',            // 골프
      '/ltr/cncr/**',            // 암
      '/ltr/dntl/**',            // 치아
      '/cmcom/carrotBridge.do**' // 운전자·여성건강·임신출산·해외여행 (캐롯 분기)
    ],
  },
  // 테크니컬 SEO 중심(성능 카테고리 제외)
  lighthouseOptions: {
    onlyCategories: ['seo', 'accessibility', 'best-practices'],
  },
  // CI 실패 임계값 — 파이프라인에서 회귀 감지
  ci: {
    budget: { seo: 90, accessibility: 90 },
  },
})

// ── 브릿지 목적지(캐롯)도 별도 점검하려면 아래로 실행 ──
// npx unlighthouse --site https://www.carrotins.com \
//   --scanner.include "/long-term/driver,/long-term/women-signature,/product/overseas"
