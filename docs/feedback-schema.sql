-- 비공개 Cloudflare D1 또는 사내 DB에 적용하는 피드백 스키마.
-- 공개 GitHub Pages/저장소에는 이 데이터의 실값을 저장하지 않는다.
CREATE TABLE IF NOT EXISTS copy_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  occurred_at TEXT NOT NULL,
  tool TEXT NOT NULL,
  product_key TEXT,
  recommendation_id TEXT,
  action TEXT NOT NULL CHECK (action IN ('copied', 'accepted', 'edit_requested', 'rejected')),
  source_version TEXT,
  text_fingerprint TEXT,
  edit_distance REAL,
  review_status TEXT,
  actor_hash TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_copy_feedback_recency ON copy_feedback(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_copy_feedback_recommendation ON copy_feedback(recommendation_id, action);
CREATE INDEX IF NOT EXISTS idx_copy_feedback_product ON copy_feedback(product_key, action);

CREATE TABLE IF NOT EXISTS performance_outcome (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  recommendation_id TEXT NOT NULL,
  product_key TEXT NOT NULL,
  channel TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  impressions INTEGER,
  clicks INTEGER,
  conversions INTEGER,
  spend REAL,
  revenue REAL,
  source_version TEXT,
  imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_performance_recommendation ON performance_outcome(recommendation_id, period_start);
