#!/usr/bin/env node
/*
 * check_worker_scheduler.mjs — Cloudflare Worker 정시 스케줄러 검증(네트워크 없음).
 * - wrangler.toml [triggers] crons 가 SCHEDULER_CRON 하나뿐인지(무료 요금제 Cron Trigger 5개 제한), 시각이 5분 단위인지
 * - 발송 워크플로에는 source=scheduler 입력을 넘기는지, 토큰이 없으면 호출하지 않는지
 */
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const src = fs.readFileSync(path.join(ROOT, "proxy/naver-proxy-worker.js"), "utf8");
const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "worker-")), "worker.mjs");
fs.writeFileSync(tmp, src + "\nexport { DISPATCH_SCHEDULE, SCHEDULER_CRON, scheduleSlot, runSchedule, healthReport };\n");
const { DISPATCH_SCHEDULE, SCHEDULER_CRON, scheduleSlot, runSchedule, healthReport, default: worker } = await import(pathToFileURL(tmp).href);

const toml = fs.readFileSync(path.join(ROOT, "proxy/wrangler.toml"), "utf8");
const crons = JSON.parse((toml.match(/^crons\s*=\s*(\[.*\])/m) || [])[1] || "[]");
assert.deepEqual(crons, [SCHEDULER_CRON], "Cron Trigger는 5분마다 1개만(무료 요금제 5개 제한)");
for (const slot of Object.keys(DISPATCH_SCHEDULE)) assert.match(slot, /^([01]\d|2[0-3]):[0-5][05]$/, `${slot}: 5분 단위 UTC HH:MM이어야 함`);
// 트리거가 몇 초 늦게 와도 같은 칸 · 23:00 UTC = 08:00 KST
assert.equal(scheduleSlot(Date.UTC(2026, 9, 1, 23, 0, 7)), "23:00");
assert.equal(scheduleSlot(Date.UTC(2026, 9, 1, 23, 4, 59)), "23:00");
assert.equal(scheduleSlot(Date.UTC(2026, 9, 1, 23, 5, 0)), "23:05");
assert.equal(typeof worker.scheduled, "function");

for (const jobs of Object.values(DISPATCH_SCHEDULE)) for (const job of jobs) {
  const wf = path.join(ROOT, ".github/workflows", job.workflow);
  assert.ok(fs.existsSync(wf), `${job.workflow} 없음`);
  assert.match(fs.readFileSync(wf, "utf8"), /workflow_dispatch:/, `${job.workflow}에 workflow_dispatch 필요`);
  if (/daily-(brief|email)/.test(job.workflow)) assert.equal(job.inputs?.source, "scheduler");
}

const calls = [];
const fake = async (url, init) => { calls.push({ url, body: JSON.parse(init.body), auth: init.headers.Authorization }); return { status: 204 }; };
const r = await runSchedule("23:00", { GH_DISPATCH_TOKEN: "t0ken" }, fake);
assert.deepEqual(r, [{ workflow: "daily-brief.yml", status: 204, ok: true }]);
assert.equal(calls[0].url, "https://api.github.com/repos/imsplendid8/CM-CMO/actions/workflows/daily-brief.yml/dispatches");
assert.deepEqual(calls[0].body, { ref: "main", inputs: { source: "scheduler", slot: "am" } });
assert.equal(calls[0].auth, "Bearer t0ken");

await runSchedule("22:20", { GH_DISPATCH_TOKEN: "t" }, fake);
assert.deepEqual(calls[1].body, { ref: "main" }, "입력을 선언하지 않은 수집 워크플로에는 inputs를 보내지 않는다(422 방지)");

const before = calls.length;
const none = await runSchedule("23:00", {}, fake);
assert.equal(calls.length, before, "토큰이 없으면 호출하지 않음");
assert.equal(none[0].ok, false);
assert.deepEqual(await runSchedule("12:35", { GH_DISPATCH_TOKEN: "t" }, fake), [], "정해진 시각이 아니면 아무것도 호출하지 않음");

console.log(`✔ 정시 스케줄러: Cron 1개(${SCHEDULER_CRON}) · 호출 시각 ${Object.keys(DISPATCH_SCHEDULE).length}개 · 워크플로 호출 계약 확인`);

// /health: 값 없이 빠진 설정 이름과 최근 정시 호출 결과만
{
  const kv = new Map();
  const USAGE = { put: async (k, v) => kv.set(k, v), get: async (k) => kv.get(k) ?? null };
  await runSchedule("23:00", { USAGE }, fake);
  const h = await healthReport({ USAGE, NAVER_ID: "secret-value" });
  assert.equal(h.ok, false);
  assert.ok(h.missing.includes("GH_DISPATCH_TOKEN") && !h.missing.includes("NAVER_ID"));
  assert.equal(h.scheduler.slot, "23:00");
  assert.equal(h.scheduler.results[0].reason, "no_token");
  assert.ok(!JSON.stringify(h).includes("secret-value"), "/health에 시크릿 값이 실리면 안 됨");
  console.log("✔ /health: 누락 설정 이름·최근 정시 호출 결과(값 비노출)");
}
