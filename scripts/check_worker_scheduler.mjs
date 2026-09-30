#!/usr/bin/env node
/*
 * check_worker_scheduler.mjs — Cloudflare Worker 정시 스케줄러 검증(네트워크 없음).
 * - wrangler.toml [triggers] crons 와 DISPATCH_SCHEDULE 키가 정확히 같은지
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
fs.writeFileSync(tmp, src + "\nexport { DISPATCH_SCHEDULE, runSchedule };\n");
const { DISPATCH_SCHEDULE, runSchedule, default: worker } = await import(pathToFileURL(tmp).href);

const toml = fs.readFileSync(path.join(ROOT, "proxy/wrangler.toml"), "utf8");
const crons = JSON.parse((toml.match(/^crons\s*=\s*(\[.*\])/m) || [])[1] || "[]");
assert.deepEqual([...crons].sort(), Object.keys(DISPATCH_SCHEDULE).sort(), "wrangler.toml crons ↔ DISPATCH_SCHEDULE 불일치");
assert.equal(typeof worker.scheduled, "function");

for (const jobs of Object.values(DISPATCH_SCHEDULE)) for (const job of jobs) {
  const wf = path.join(ROOT, ".github/workflows", job.workflow);
  assert.ok(fs.existsSync(wf), `${job.workflow} 없음`);
  assert.match(fs.readFileSync(wf, "utf8"), /workflow_dispatch:/, `${job.workflow}에 workflow_dispatch 필요`);
  if (/daily-(brief|email)/.test(job.workflow)) assert.equal(job.inputs?.source, "scheduler");
}

const calls = [];
const fake = async (url, init) => { calls.push({ url, body: JSON.parse(init.body), auth: init.headers.Authorization }); return { status: 204 }; };
const r = await runSchedule("0 23 * * *", { GH_DISPATCH_TOKEN: "t0ken" }, fake);
assert.deepEqual(r, [{ workflow: "daily-brief.yml", status: 204, ok: true }]);
assert.equal(calls[0].url, "https://api.github.com/repos/imsplendid8/CM-CMO/actions/workflows/daily-brief.yml/dispatches");
assert.deepEqual(calls[0].body, { ref: "main", inputs: { source: "scheduler", slot: "am" } });
assert.equal(calls[0].auth, "Bearer t0ken");

await runSchedule("20 22 * * *", { GH_DISPATCH_TOKEN: "t" }, fake);
assert.deepEqual(calls[1].body, { ref: "main" }, "입력을 선언하지 않은 수집 워크플로에는 inputs를 보내지 않는다(422 방지)");

const before = calls.length;
const none = await runSchedule("0 23 * * *", {}, fake);
assert.equal(calls.length, before, "토큰이 없으면 호출하지 않음");
assert.equal(none[0].ok, false);
assert.deepEqual(await runSchedule("1 2 * * *", { GH_DISPATCH_TOKEN: "t" }, fake), []);

console.log(`✔ 정시 스케줄러: cron ${crons.length}개 · 워크플로 호출 계약 확인`);
