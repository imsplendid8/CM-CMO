/**
 * Modooflow OAuth 대시보드 백엔드
 * Express.js 서버 (로컬 개발 + 프로덕션 배포용)
 *
 * 사용법:
 * npm install express cors dotenv @anthropic-ai/sdk
 * node server.js
 */

const express = require("express");
const cors = require("cors");
const path = require("path");
require("dotenv").config();

const {
  generatePersonalizedDashboard,
  generateDefaultDashboard,
  authenticateUser,
  USER_PREFERENCES
} = require("./api/personalized-dashboard.js");

const app = express();
const PORT = process.env.PORT || 3000;

// 미들웨어
app.use(cors({
  origin: [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://imsplendid8.github.io"
  ],
  credentials: true
}));
app.use(express.json());
app.use(express.static("."));

/**
 * 헬스 체크
 */
app.get("/api/health", (req, res) => {
  res.json({
    status: "ok",
    message: "Modooflow OAuth Dashboard API",
    timestamp: new Date().toISOString()
  });
});

/**
 * 사용자 목록 (개발용)
 */
app.get("/api/users", (req, res) => {
  const users = Object.values(USER_PREFERENCES).map(u => ({
    id: u.id,
    name: u.name,
    role: u.role,
    email: u.email
  }));

  res.json({ users });
});

/**
 * 개인화 대시보드 생성
 * Authorization: Bearer demo_token_user_001
 */
app.post("/api/personalized-dashboard", async (req, res) => {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader) {
      return res.status(401).json({ error: "No authorization token" });
    }

    const token = authHeader.split(" ")[1];
    const userPreferences = authenticateUser(token);

    if (!userPreferences) {
      return res.status(403).json({ error: "Invalid token" });
    }

    // Claude API가 활성화되면 generatePersonalizedDashboard 사용
    // 지금은 기본값 반환
    const dashboard = generateDefaultDashboard(userPreferences);

    res.json({
      success: true,
      user: {
        id: userPreferences.id,
        name: userPreferences.name,
        role: userPreferences.role,
        email: userPreferences.email
      },
      dashboard: dashboard,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error("대시보드 생성 오류:", error);
    res.status(500).json({
      error: "대시보드를 생성할 수 없습니다",
      message: error.message
    });
  }
});

/**
 * OAuth 콜백 - Google
 * 실제 구현 시 Google API로 토큰 교환 필요
 */
app.get("/oauth/google/callback", (req, res) => {
  const { code, state } = req.query;

  if (!code) {
    return res.status(400).json({ error: "Missing authorization code" });
  }

  // TODO: code → access_token 교환
  // TODO: access_token으로 사용자 정보 조회
  // TODO: JWT 생성 및 클라이언트로 전달

  res.json({
    message: "Google OAuth callback received",
    code: code.substring(0, 10) + "...",
    status: "pending_implementation"
  });
});

/**
 * OAuth 콜백 - GitHub
 * 실제 구현 시 GitHub API로 토큰 교환 필요
 */
app.get("/oauth/github/callback", (req, res) => {
  const { code, state } = req.query;

  if (!code) {
    return res.status(400).json({ error: "Missing authorization code" });
  }

  // TODO: code → access_token 교환 (POST https://github.com/login/oauth/access_token)
  // TODO: access_token으로 사용자 정보 조회 (GET https://api.github.com/user)
  // TODO: JWT 생성 및 클라이언트로 전달

  res.json({
    message: "GitHub OAuth callback received",
    code: code.substring(0, 10) + "...",
    status: "pending_implementation"
  });
});

/**
 * 에러 핸들러
 */
app.use((err, req, res, next) => {
  console.error("Unhandled error:", err);
  res.status(500).json({
    error: "Internal server error",
    message: process.env.NODE_ENV === "development" ? err.message : "An error occurred"
  });
});

/**
 * 404 핸들러
 */
app.use((req, res) => {
  res.status(404).json({
    error: "Not found",
    path: req.path
  });
});

// 서버 시작
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║     Modooflow OAuth Dashboard API          ║
║     http://localhost:${PORT}               ║
╚════════════════════════════════════════════╝

📚 API 엔드포인트:
  GET  /api/health                    헬스 체크
  GET  /api/users                     사용자 목록
  POST /api/personalized-dashboard    개인화 대시보드

🧪 테스트:
  curl -X POST http://localhost:${PORT}/api/personalized-dashboard \\
    -H "Authorization: Bearer demo_token_user_001" \\
    -H "Content-Type: application/json"

📱 프론트엔드:
  http://localhost:${PORT}/oauth-dashboard.html

⚙️ 환경 변수:
  PORT=${PORT}
  ANTHROPIC_API_KEY=${process.env.ANTHROPIC_API_KEY ? "✓ 설정됨" : "✗ 미설정"}
  NODE_ENV=${process.env.NODE_ENV || "development"}
  `);
});

module.exports = app;
