/**
 * 개인화된 마케팅 대시보드 API
 * Claude API를 사용해 팀원별 맞춤 분석 제공
 *
 * 사용법:
 * POST /api/personalized-dashboard
 * Authorization: Bearer {oauth_token}
 *
 * 응답:
 * {
 *   kpis: [{label, value, trend, change}, ...],
 *   recommendations: ["...", "..."],
 *   alerts: [{severity, message}, ...]
 * }
 */

// 사용자 선호도 데이터 (DB 대신 JSON으로 관리)
const USER_PREFERENCES = {
  user_001: {
    id: "user_001",
    name: "김마케팅",
    email: "kim.marketing@hanwha.com",
    role: "검색광고 전담",
    products: ["home", "driver", "hrmf"],
    analysisType: "search",
    marketingFocus: "검색량 기반 신호 분석"
  },
  user_002: {
    id: "user_002",
    name: "이컨텐츠",
    email: "lee.content@hanwha.com",
    role: "파워컨텐츠",
    products: ["cncr", "dntl", "birth"],
    analysisType: "content",
    marketingFocus: "콘텐츠 기반 수요 창출"
  },
  user_003: {
    id: "user_003",
    name: "박소재",
    email: "park.creative@hanwha.com",
    role: "SA 소재 담당",
    products: ["golf", "event", "holeinone"],
    analysisType: "creative",
    marketingFocus: "시즌별 창의적 소재 개발"
  }
};

// 샘플 마케팅 신호 데이터
const MARKETING_SIGNALS = {
  newreg: {
    count: 12450,
    trend: "up",
    change: 15,
    monthly: [9800, 10200, 10900, 11200, 11800, 12100, 12450]
  },
  searchAd: {
    roi: 3.2,
    trend: "up",
    change: 8,
    cpc: 1250
  },
  campaigns: {
    active: 24,
    trend: "down",
    change: -3
  },
  seasonalIssues: {
    june: ["장마·집중호우", "여름휴가", "휴가보험 수요"],
    july: ["여름성수기", "장마 영향", "휴가안전"],
    august: ["휴가피크", "물놀이사고", "야외활동보험"]
  }
};

/**
 * 개인화 대시보드 생성 (Claude API 활용)
 */
async function generatePersonalizedDashboard(userId, userPreferences) {
  try {
    const Anthropic = require("@anthropic-ai/sdk");
    const client = new Anthropic.default({
      apiKey: process.env.ANTHROPIC_API_KEY
    });

    // Claude에게 프롬프트 생성
    const systemPrompt = buildSystemPrompt(userPreferences);
    const userPrompt = buildUserPrompt(userPreferences);

    // Claude API 호출
    const response = await client.messages.create({
      model: "claude-opus-5",
      max_tokens: 2048,
      system: systemPrompt,
      messages: [
        {
          role: "user",
          content: userPrompt
        }
      ]
    });

    // 응답 파싱
    const content = response.content[0];
    if (content.type !== "text") {
      throw new Error("Unexpected response type from Claude");
    }

    // JSON 추출 및 파싱
    const jsonMatch = content.text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error("Failed to extract JSON from Claude response");
    }

    return JSON.parse(jsonMatch[0]);

  } catch (error) {
    console.error("Claude API 호출 실패:", error);
    // 폴백: 기본 데이터 반환
    return generateDefaultDashboard(userPreferences);
  }
}

/**
 * 시스템 프롬프트 구성
 */
function buildSystemPrompt(userPreferences) {
  return `당신은 한화손해보험의 마케팅 분석 전문가입니다.

팀원: ${userPreferences.name} (${userPreferences.role})
담당 상품: ${userPreferences.products.join(", ")}
분석 초점: ${userPreferences.marketingFocus}

다음 요구사항을 만족하는 대시보드 데이터를 생성하세요:
1. 팀원의 역할과 담당상품에 맞춘 KPI (최대 4개)
2. 즉시 실행 가능한 마케팅 추천사항 (최대 4개)
3. 주의가 필요한 알림 (높음/중간 심각도, 최대 3개)

응답은 반드시 JSON 형식이어야 합니다:
{
  "kpis": [
    {"label": "지표명", "value": 숫자, "trend": "up|down", "change": 변화율},
    ...
  ],
  "recommendations": ["추천사항 1", "추천사항 2", ...],
  "alerts": [
    {"severity": "high|medium", "message": "경고 메시지"},
    ...
  ]
}

현재 마케팅 신호:
- 월별 신규등록: ${MARKETING_SIGNALS.newreg.count}건 (↑${MARKETING_SIGNALS.newreg.change}%)
- 검색광고 ROI: ${MARKETING_SIGNALS.searchAd.roi} (↑${MARKETING_SIGNALS.searchAd.change}%)
- 활성 캠페인: ${MARKETING_SIGNALS.campaigns.active}개
- 현재 시즌 이슈: ${Object.values(MARKETING_SIGNALS.seasonalIssues).flat().join(", ")}`;
}

/**
 * 사용자 프롬프트 구성
 */
function buildUserPrompt(userPreferences) {
  const focus = userPreferences.analysisType;

  let analysisContext = "";
  switch (focus) {
    case "search":
      analysisContext = "검색광고 성과 최대화. 키워드 입찰 전략, 광고 성과율, 경쟁사 분석";
      break;
    case "content":
      analysisContext = "콘텐츠 기반 수요 창출. 파워컨텐츠 배포 일정, 검색 근거, SEO 기회";
      break;
    case "creative":
      analysisContext = "시즌별 창의적 소재 개발. 시각화 아이디어, 메시지 톤, A/B 테스트 안건";
      break;
    default:
      analysisContext = "종합 마케팅 성과 분석";
  }

  return `${userPreferences.name}님(${userPreferences.role})을 위한 개인화 대시보드를 생성하세요.

담당상품: ${userPreferences.products.join(", ")}
분석초점: ${analysisContext}

${userPreferences.name}님이 이번주와 다음달에 집중해야 할 마케팅 활동을 제시하세요.
데이터 기반의 실행 가능한 조언을 JSON으로 반환하세요.`;
}

/**
 * 기본 대시보드 (Claude API 실패 시 폴백)
 */
function generateDefaultDashboard(userPreferences) {
  const dashboards = {
    search: {
      kpis: [
        { label: "월별 신규등록", value: 12450, trend: "up", change: 15 },
        { label: "검색광고 ROI", value: 3.2, trend: "up", change: 8 },
        { label: "평균 CPC", value: 1250, trend: "up", change: 12 },
        { label: "클릭수", value: 4850, trend: "up", change: 22 }
      ],
      recommendations: [
        "🔔 6월 장마철 누수 보장 검색광고 강화 (예상 수요 +45%)",
        "💡 운전자보험: 6월 말 휴가철 캠페인 준비 시작",
        "📈 신규 키워드 추가: 관련 검색량 지수 +35% 확인",
        "⭐ 경쟁사 입찰가 모니터링: 평균 입찰가 상승 추세 (+8%)"
      ],
      alerts: [
        { severity: "high", message: "🚨 [긴급] 암보험 입찰가 경쟁 심화 - 예산 재검토 필요" },
        { severity: "medium", message: "⚠️ 여성보험 전환율 하락 (지난주 대비 -12%) - 소재 개선 권장" },
        { severity: "medium", message: "📊 운전자보험 검색량 계절성 피크 진입 - 재고 확인" }
      ]
    },
    content: {
      kpis: [
        { label: "파워콘텐츠 뷰", value: 28500, trend: "up", change: 34 },
        { label: "평균 체류시간", value: "3분 42초", trend: "up", change: 18 },
        { label: "검색 근거 점수", value: 8.2, trend: "up", change: 12 },
        { label: "구독자 증가", value: 1245, trend: "up", change: 28 }
      ],
      recommendations: [
        "✍️ 암보험 파워컨텐츠 추가: 검색량 지수 높음, 콘텐츠 격차 큼",
        "🎯 시즌별 콘텐츠 로드맵: 7월 휴가보험, 8월 물놀이 안전",
        "📱 모바일 최적화: 모바일 이탈율 23% - UI/UX 개선 필요",
        "🔍 SEO 기회: 미타겟 키워드 3개 발굴, 순위 도약 가능"
      ],
      alerts: [
        { severity: "high", message: "🚨 일반건강보험 콘텐츠 부족 - 긴급 작성 필요" },
        { severity: "medium", message: "⚠️ 유병자보험 검색 근거 약화 - 콘텐츠 리모델링 검토" },
        { severity: "medium", message: "📊 모바일 CTR 하락 - 제목/썸네일 A/B 테스트 안건" }
      ]
    },
    creative: {
      kpis: [
        { label: "소재 CTR", value: "4.2%", trend: "up", change: 15 },
        { label: "A/B 테스트 승인율", value: "78%", trend: "up", change: 22 },
        { label: "월간 소재 생산량", value: 156, trend: "up", change: 31 },
        { label: "브랜드 호감도", value: 8.5, trend: "up", change: 12 }
      ],
      recommendations: [
        "🎨 6월 장마철 소재: 누수 걱정 해소 메시지, 감정 어필 강화",
        "⚡ 여름휴가 캠페인: 신나는 톤 & 안전보장 메시지 결합",
        "🔄 성과 있는 소재 변형: 기존 고성능 소재 A/B 3개 생성",
        "👥 페르소나별 소재 개발: 20대 VS 40대 메시지 차별화"
      ],
      alerts: [
        { severity: "high", message: "🚨 준법심의 지적 건수 증가 - 표현 가이드 리뷰 필요" },
        { severity: "medium", message: "⚠️ 이미지 소재 피로도 높음 - 신규 비주얼 트렌드 반영" },
        { severity: "medium", message: "📊 동영상 소재 성과 우수 - 확대 투자 검토" }
      ]
    }
  };

  return dashboards[userPreferences.analysisType] || dashboards.search;
}

/**
 * 사용자 인증 검증
 */
function authenticateUser(token) {
  // 실제 구현에서는 OAuth 토큰 검증
  // 예시: JWT 검증, OAuth 제공자 검증 등

  if (token.startsWith("demo_token_")) {
    const userId = token.replace("demo_token_", "");
    return USER_PREFERENCES[userId] || null;
  }

  // 실제 OAuth 토큰의 경우
  // return await verifyOAuthToken(token);

  return null;
}

/**
 * Express 미들웨어 - 실제 사용 예시
 */
function createDashboardHandler() {
  return async (req, res) => {
    try {
      // 토큰 추출
      const authHeader = req.headers.authorization;
      if (!authHeader) {
        return res.status(401).json({ error: "No authorization token" });
      }

      const token = authHeader.split(" ")[1];

      // 사용자 인증
      const userPreferences = authenticateUser(token);
      if (!userPreferences) {
        return res.status(403).json({ error: "Invalid token" });
      }

      // 개인화 대시보드 생성
      const dashboard = await generatePersonalizedDashboard(
        userPreferences.id,
        userPreferences
      );

      // 응답
      res.json({
        success: true,
        user: {
          id: userPreferences.id,
          name: userPreferences.name,
          role: userPreferences.role
        },
        dashboard: dashboard
      });

    } catch (error) {
      console.error("대시보드 생성 오류:", error);
      res.status(500).json({
        error: "대시보드를 생성할 수 없습니다",
        message: error.message
      });
    }
  };
}

/**
 * Cloudflare Worker 호환 핸들러 (worker.js에서 사용)
 */
async function handleDashboardRequest(request) {
  try {
    const authHeader = request.headers.get("authorization");
    if (!authHeader) {
      return new Response(JSON.stringify({ error: "No authorization token" }), {
        status: 401,
        headers: { "content-type": "application/json" }
      });
    }

    const token = authHeader.split(" ")[1];
    const userPreferences = authenticateUser(token);

    if (!userPreferences) {
      return new Response(JSON.stringify({ error: "Invalid token" }), {
        status: 403,
        headers: { "content-type": "application/json" }
      });
    }

    // 기본 대시보드 반환 (Cloudflare Workers에서는 외부 API 호출 제한 있음)
    const dashboard = generateDefaultDashboard(userPreferences);

    return new Response(JSON.stringify({
      success: true,
      user: {
        id: userPreferences.id,
        name: userPreferences.name,
        role: userPreferences.role
      },
      dashboard: dashboard
    }), {
      headers: { "content-type": "application/json" }
    });

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { "content-type": "application/json" }
    });
  }
}

// 모듈 내보내기
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    generatePersonalizedDashboard,
    generateDefaultDashboard,
    createDashboardHandler,
    handleDashboardRequest,
    authenticateUser,
    USER_PREFERENCES
  };
}
