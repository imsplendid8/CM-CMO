#!/usr/bin/env node
/* Modooflow 핵심 로직 경량 테스트 (의존성 0 · Node로 실행: `node test/logic.test.js`)
   - 실제 data.js / app.js 소스를 그대로 로드해 순수 로직만 검증한다.
   - 브라우저 전용 초기 렌더·이벤트 바인딩은 제거하고(샌드박스), 함수 정의만 평가한다. */
const fs = require('fs'), vm = require('vm'), path = require('path');
const root = path.join(__dirname, '..');

let data = fs.readFileSync(path.join(root, 'data.js'), 'utf8');
let app  = fs.readFileSync(path.join(root, 'app.js'),  'utf8');

// 브라우저 side-effect 제거: 초기 렌더 블록(EOF까지) + addEventListener 등록 줄
app = app.replace(/\/\*\s*──\s*초기 렌더[\s\S]*$/, '');
app = app.split('\n').filter(l => !/\.addEventListener\(/.test(l)).join('\n');

// 검증 코드(샌드박스 내부에서 실행 — 함수/데이터와 같은 스코프)
const asserts = `
let __p=0, __f=0;
function eq(name,a,b){ if(JSON.stringify(a)===JSON.stringify(b)) __p++; else { __f++; console.error('  ✗ '+name+'  ('+JSON.stringify(a)+' !== '+JSON.stringify(b)+')'); } }
function ok(name,c){ if(c) __p++; else { __f++; console.error('  ✗ '+name); } }

/* esc() — XSS 이스케이프 */
eq('esc <script>', esc('<script>'), '&lt;script&gt;');
eq('esc amp',      esc('a&b'),      'a&amp;b');
eq('esc dquote',   esc(String.fromCharCode(34)), '&quot;');
eq('esc squote',   esc(String.fromCharCode(39)), '&#39;');
eq('esc null',     esc(null), '');

/* safeKey() — 프로토타입 오염 방어 */
ok('safeKey __proto__',  safeKey('__proto__')===false);
ok('safeKey constructor',safeKey('constructor')===false);
ok('safeKey prototype',  safeKey('prototype')===false);
ok('safeKey 정상키',      safeKey('당사')===true);

/* termScoreOf() — 용어 친화도(0~100) */
eq('term 당사=0', termScoreOf('당사'), 0);
ok('term S사>당사', termScoreOf('S사') > termScoreOf('당사'));

/* computeScores() — 입력효율·용어 2축(전환율 제거 확인) */
const sc = computeScores();
ok('score 개수=COMPS', sc.length === COMPS.length);
const me = sc.find(function(r){return r.c==='당사';});
ok('당사 sIn=0(입력 최다)', me.sIn === 0);
ok('score에 sConv 없음', !('sConv' in me));
ok('total 0~100', sc.every(function(r){return r.total>=0 && r.total<=100;}));
ok('WEIGHTS 2축(conv 제거)', WEIGHTS.conv === undefined && WEIGHTS.input!=null && WEIGHTS.term!=null);

console.log('\\n  PASS '+__p+'  ·  FAIL '+__f);
if(__f) { process.exitCode = 1; }
`;

// 최소 스텁(혹시 호출돼도 throw 안 하도록)
const sandbox = {
  console,
  process,
  localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
};
sandbox.window = sandbox;
vm.createContext(sandbox);
console.log('Modooflow 핵심 로직 테스트');
try {
  vm.runInContext(data + '\n' + app + '\n' + asserts, sandbox, { filename: 'flowlens.combined.js' });
} catch (e) {
  console.error('실행 오류:', e.message);
  process.exitCode = 1;
}
