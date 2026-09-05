#!/usr/bin/env node
/**
 * Modooflow OAuth 대시보드 서버
 * Express.js 백엔드 — OAuth 인증 + Claude API 연동
 *
 * 설치:
 *   npm install express cors dotenv @anthropic-ai/sdk
 *
 * 실행:
 *   node server.js
 *   또는: npm start
 *
 * 테스트:
 *   curl -X POST http://localhost:3000/api/personalized-dashboard \
 *     -H "Authorization: Bearer demo_token_user_001" \
 *     -H "Content-Type: application/json"
 */

const express = require("express");
const cors = require("cors");
const path = require("path");
require("dotenv").config();

const {
  createDashboardHandler,
  generateDefaultDashboard,
  USER_PREFERENCES
} = require("./api/personalized-dashboard.js");

const app = express();
const PORT = process.env.PORT || 3000;

// 미들웨어
app.use(cors());
app.use(express.json());
app.use(express.static("."));

// 헬스 체크
app.get("/health", (req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// 대시보드 API
app.post("/api/personalized-dashboard", createDashboardHandler());

// OAuth 콜백 (Google)
app.get("/oauth/google/callback", async (req, res) => {
  try {
    const { code, state } = req.query;

    if (!code) {
      return res.status(400).json({ error: "인증 코드가 없습니다" });
    }

    // TODO: Google OAuth 토큰 교환
    // const token = await exchangeGoogleToken(code);

    // 임시: 데모 토큰 사용
    const demoToken = "demo_token_user_001";
    res.redirect(`/oauth-dashboard.html?token=${demoToken}&provider=google`);

  } catch (error) {
    console.error("Google OAuth 콜백 오류:", error);
    res.status(500).json({ error: "인증 중 오류가 발생했습니다" });
  }
});

// OAuth 콜백 (GitHub)
app.get("/oauth/github/callback", async (req, res) => {
  try {
    const { code, state } = req.query;

    if (!code) {
      return res.status(400).json({ error: "인증 코드가 없습니다" });
    }

    // TODO: GitHub OAuth 토큰 교환
    // const token = await exchangeGithubToken(code);

    // 임시: 데모 토큰 사용
    const demoToken = "demo_token_user_002";
    res.redirect(`/oauth-dashboard.html?token=${demoToken}&provider=github`);

  } catch (error) {
    console.error("GitHub OAuth 콜백 오류:", error);
    res.status(500).json({ error: "인증 중 오류가 발생했습니다" });
  }
});

// 사용자 정보 조회 (로그인된 사용자)
app.get("/api/me", (req, res) => {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader) {
      return res.status(401).json({ error: "인증되지 않음" });
    }

    const token = authHeader.split(" ")[1];

    // 데모 토큰 파싱
    if (token.startsWith("demo_token_")) {
      const userId = token.replace("demo_token_", "");
      const user = USER_PREFERENCES[userId];

      if (user) {
        return res.json({
          success: true,
          user: {
            id: user.id,
            name: user.name,
            email: user.email,
            role: user.role
          }
        });
      }
    }

    res.status(403).json({ error: "유효하지 않은 토큰" });
  } catch (error) {
    console.error("사용자 정보 조회 오류:", error);
    res.status(500).json({ error: "오류가 발생했습니다" });
  }
});

// 기본 대시보드 (토큰 없이 데모용)
app.get("/api/demo-dashboard/:userId", (req, res) => {
  try {
    const { userId } = req.params;
    const user = USER_PREFERENCES[userId];

    if (!user) {
      return res.status(404).json({ error: "사용자를 찾을 수 없습니다" });
    }

    const dashboard = generateDefaultDashboard(user);

    res.json({
      success: true,
      user: {
        id: user.id,
        name: user.name,
        role: user.role
      },
      dashboard: dashboard
    });
  } catch (error) {
    console.error("데모 대시보드 오류:", error);
    res.status(500).json({ error: error.message });
  }
});

// 사용 가능한 사용자 목록 (개발용)
app.get("/api/users", (req, res) => {
  try {
    const users = Object.values(USER_PREFERENCES).map(user => ({
      id: user.id,
      name: user.name,
      role: user.role,
      email: user.email
    }));

    res.json({
      success: true,
      users: users,
      devNote: "개발 환경에서만 사용하세요. 프로덕션에서는 제거해야 합니다."
    });
  } catch (error) {
    console.error("사용자 목록 조회 오류:", error);
    res.status(500).json({ error: error.message });
  }
});

// 로그 기록
app.use((req, res, next) => {
  const now = new Date().toISOString();
  console.log(`[${now}] ${req.method} ${req.path}`);
  next();
});

// 에러 핸들러
app.use((err, req, res, next) => {
  console.error("서버 오류:", err);
  res.status(500).json({
    error: "내부 서버 오류",
    message: process.env.NODE_ENV === "development" ? err.message : undefined
  });
});

// 서버 시작
const server = app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════════════════════════╗
║           Modooflow OAuth 대시보드 서버 시작                            ║
╚════════════════════════════════════════════════════════════════════════╝

🚀 서버: http://localhost:${PORT}
📊 대시보드: http://localhost:${PORT}/oauth-dashboard.html
📝 API 문서: docs/OAUTH_DASHBOARD_SETUP.md

📡 엔드포인트:
  • POST /api/personalized-dashboard — 개인화 대시보드 생성
  • GET  /api/me — 로그인한 사용자 정보
  • GET  /api/demo-dashboard/:userId — 데모 대시보드 (토큰 불필요)
  • GET  /api/users — 사용 가능한 사용자 목록 (개발용)

🔐 환경 변수:
  ANTHROPIC_API_KEY = ${process.env.ANTHROPIC_API_KEY ? "✓ 설정됨" : "✗ 미설정 (필수)"}
  PORT = ${PORT}

💡 테스트 명령:
  curl -X POST http://localhost:${PORT}/api/personalized-dashboard \\
    -H "Authorization: Bearer demo_token_user_001" \\
    -H "Content-Type: application/json"

  또는 브라우저에서 http://localhost:${PORT}/oauth-dashboard.html 방문

  `);
});

// 종료 시그널 처리
process.on("SIGTERM", () => {
  console.log("\n🛑 SIGTERM 신호 수신. 서버를 종료합니다...");
  server.close(() => {
    console.log("✓ 서버 종료됨");
    process.exit(0);
  });
});

// 내보내기 (테스트용)
if (typeof module !== "undefined" && module.exports) {
  module.exports = app;
}
