/* ============================================================
   app.js — 대시보드 동작 로직 (렌더 + 이벤트)
   data.js 가 먼저 로드되어 있어야 합니다.

   [목차]  ── 각 섹션은 아래 주석 배너로 구분 ──
   0) 공통 유틸        : esc(XSS) · safeKey(프로토타입 오염)
   0) 셸               : NAVMETA · setPage · 사이드바 내비
      관리자/사용 모드 : applyAdmin
   1) 플로우           : renderFixed · pivotRender
   2) 단계별 분석      : stepRender
   3) 용어 비교        : termChips · termRender (표준의미 → 경쟁사 근거 → 당사 제안)
   4) 벤치마크         : termScoreOf · computeScores · scoreRender   (입력효율·용어 2축)
      관리자 설정      : getWeights/setWeights · getFields/setFields
   5) A/B 시나리오     : abRender · abSVG(Figma) · abCopy
   6) 뉴스 감지        : newsKw · newsRender (상태=localStorage)
   7) 퍼널 리포트      : lsRender (Looker 임베드 · 구글 도메인만)
   9) 내보내기         : dlCSV(수식 인젝션 방어) · exFlow/exStep/exTerm
      플로우맵         : NSHAPE · getFlowMap · flowmapRender (SVG 분기도)
      개선방안(insightsRender) · 마스킹 캡쳐(shotsRender) · 초기 렌더(파일 하단)
   ============================================================ */

/* HTML 이스케이프 (XSS 방지) — 사용자 입력·임포트 데이터는 반드시 통과시킴 */
function esc(s){return (s==null?'':''+s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
/* 프로토타입 오염 방지 — 임포트 데이터의 객체 키 화이트리스트 */
function safeKey(k){return k!=='__proto__'&&k!=='constructor'&&k!=='prototype';}

/* ── 셸: 사이드바 내비 + 상단 타이틀 + KPI ── */
const NAVMETA = {
 t1:["플로우","리스팅 ↔ 플로우(분기 다이어그램) 보기 전환"],
 t2:["단계별 분석","단계별 입력 항목 비교"],
 t3:["고객친화 용어표현","어려운 약관용어 → 쉬운 표현 + 경쟁사 비교"],
 t4:["벤치마크·개선","점수 → 진단 → A/B·업셀 → 방법론(로직)"]
};
var curTab='t1';
function setPage(t){curTab=t;const m=NAVMETA[t];if(!m)return;document.getElementById('pageTitle').textContent=m[0];document.getElementById('pageSub').textContent=m[1];}
function upsellRender(){if(typeof UPSELL==='undefined')return;
 var sum='<div class="summary info">업셀 기회 <b>'+UPSELL.length+'</b>개 — <b>담보선택</b> 단계가 핵심 업셀 지점</div>';
 var steps=['견적/정보','담보선택 ★','청약완료'];
 var flow='<span class="lbl">업셀 발생 지점</span><div class="fline" style="margin-top:8px;gap:8px;">'+steps.map(function(s,i){var hot=s.indexOf('★')>=0;return '<span class="node" style="flex:0 0 auto;text-align:center;'+(hot?'border-color:var(--brand);background:var(--brand-50);font-weight:700;':'')+'">'+esc(s.replace(' ★',''))+(hot?' <span style="color:var(--brand)">★</span>':'')+'</span>'+(i<steps.length-1?'<span class="arrow">→</span>':'');}).join('')+'</div>';
 var cards=UPSELL.map(function(u){return '<div class="sec" style="display:flex;gap:13px;align-items:flex-start;margin-bottom:12px;">'
  +'<span class="badge" style="background:var(--brand-50);color:var(--brand-600);white-space:nowrap;">'+esc(u.step)+'</span>'
  +'<div style="flex:1;min-width:0;"><div style="font-weight:700;font-size:14px;">'+esc(u.base)+' <span style="color:var(--brand);">→ '+esc(u.up)+'</span></div>'
  +'<div style="color:var(--ink-2);font-size:13px;margin-top:4px;">'+esc(u.benefit)+'</div>'
  +'<div class="proto-sub" style="margin-top:5px;">제안 멘트 : "'+esc(u.ment)+'"</div></div>'
  +'</div>';}).join('');
 var cmpRows=[['상해','자기신체사고(자손)','자동차상해 업그레이드'],['대물','대물 2억','한도 상향 5~10억'],['자차','선택 가입','자차+자기부담금 옵션'],['특약','기본','운전자보험·법률비용']];
 var cmp='<div class="sec"><h2>당사 표준 담보 vs 타사 업셀 담보 <span class="lbl" style="font-weight:600">· 신규 기준</span></h2><div class="caphint">경쟁사는 표준 담보 위에 ‘업셀 담보’를 제안해 객단가를 올립니다. 당사도 적합성 내에서 동일 기회.</div><table><tr><td class="lbl">담보</td><td class="lbl">당사 (표준 제안)</td><td class="lbl">타사 업셀 담보</td></tr>'+cmpRows.map(function(r){return '<tr><td style="font-weight:700;width:70px">'+esc(r[0])+'</td><td style="color:var(--ink-2)">'+esc(r[1])+'</td><td style="color:var(--brand-600);font-weight:700">'+esc(r[2])+'</td></tr>';}).join('')+'</table></div>';
 var caps=[];try{caps=recGet().filter(function(r){return r.status==='confirmed'&&(r.upcover||r.fee);});}catch(e){}
 var capHTML=caps.length?'<div class="sec"><h2>캡쳐 기반 업셀 제안 <span class="lbl" style="font-weight:600">· 입력값 자동 반영</span></h2><div class="caphint">측정기록의 업셀 제안담보·보험료를 그대로 불러옵니다.</div><table><tr><td class="lbl">회사</td><td class="lbl">화면</td><td class="lbl">제안 담보</td><td class="lbl">보험료</td></tr>'+caps.map(function(r){return '<tr><td style="font-weight:700;white-space:nowrap">'+esc(r.co)+'</td><td style="color:var(--ink-2)">'+esc(recDisp(r))+'</td><td style="color:var(--brand-600);font-weight:700">'+esc(r.upcover||'-')+'</td><td style="white-space:nowrap">'+esc(r.fee||'-')+'</td></tr>';}).join('')+'</table></div>':'';
 document.getElementById('upsellsum').innerHTML=sum;document.getElementById('upsellflow').innerHTML=flow;document.getElementById('upsells').innerHTML=capHTML+cmp+cards;}
document.querySelector('.nav').addEventListener('click',function(e){const it=e.target.closest('.nav-item');if(!it)return;const t=it.dataset.t;this.querySelectorAll('.nav-item').forEach(function(x){x.classList.remove('on');});it.classList.add('on');document.querySelectorAll('.view').forEach(function(x){x.classList.remove('on');});document.getElementById(t).classList.add('on');setPage(t);document.querySelector('.content').scrollTop=0;});

/* ── 관리자 모드 / 사용(발표) 모드 ── */
function applyAdmin(){const admin=localStorage.getItem('cap_admin')==='1';document.body.classList.toggle('use-mode',!admin);const b=document.getElementById('adminToggle');if(b){b.textContent=admin?'🔓 관리자 모드 (켜짐)':'🔒 사용 모드 (편집 숨김)';b.classList.toggle('on',admin);}}
document.getElementById('adminToggle')&&document.getElementById('adminToggle').addEventListener('click',function(){const admin=localStorage.getItem('cap_admin')==='1';localStorage.setItem('cap_admin',admin?'0':'1');applyAdmin();});

/* ── 1) 플로우 ── */
let pmode="case",pcase="신규",pcomp="S사",curStep="운전자정보",curCanon=null,curTerm="자기신체사고",upFilter=true;/* pcase 기본=신규 */
function caseLabel(v){return (typeof CASELABEL!=='undefined'&&CASELABEL[v])?CASELABEL[v]:v;}
function renderFixed(){const list=pmode==='case'?CASES:COMPS,cur=pmode==='case'?pcase:pcomp;document.getElementById('fixed').innerHTML='<span class="lbl">'+(pmode==='case'?'고객 기준 고정':'회사 고정')+'</span><br>'+list.map(function(v){return '<span class="chip'+(v===cur?' on':'')+'" data-v="'+v+'">'+(pmode==='case'?esc(caseLabel(v)):esc(v))+'</span>';}).join('')+'<span class="cgrp" style="margin-left:12px;">필터</span><span class="chip'+(upFilter?' on':'')+'" data-upf="1" title="업셀링 시점 강조 켜기/끄기">★ 업셀링 시점</span>';var mh=document.getElementById('modehint');if(mh)mh.textContent=pmode==='case'?'한 고객 기준을 고정하고 '+COMPS.length+'개사 화면을 나란히 비교합니다.':'한 회사를 고정하고 고객 기준 '+CASES.length+'가지를 비교합니다.';}
/* 업셀 시점: 파일명/화면명에 '업셀'이 들어가면 업셀링 단계로 자동 인식 (담보선택 포함) */
function isUpStep(name){var s=''+name;return s.indexOf('업셀')>=0||s.indexOf('담보선택')>=0;}
/* 같은 화면(버튼만 다른 변형) 묶기 — 파일명 표기 (1of4)/(1/4) 인식 → base가 같으면 한 노드로 1/N */
var _variantStore={},_vid=0;
function _variantBase(name){var s=(''+name).replace(/[\(\[]\s*\d+\s*(?:of|\/|분의|중)\s*\d+\s*[\)\]]/i,'').replace(/\s+/g,' ').trim();s=s.replace(/^\d+/,'').replace(/\d+$/,'').trim();/* 앞뒤 숫자 제거 → '3본인인증5'·'본인인증1' 등 변형을 한 base로 묶음 */return s||(''+name);}
function groupVariants(steps){var out=[],last=null;steps.forEach(function(st){var base=_variantBase(st[0]);if(last&&last.base===base){last.items.push(st);}else{last={base:base,items:[st]};out.push(last);}});return out;}
/* 표시 이름 정리 — 파일명 앞의 '회사 가입유형'(예: 삼성 신규 / KB 신규)은 분류용일 뿐이므로 라벨에서 제거.
   회사·케이스는 이미 co/case로 분류에 쓰임. 토큰은 공백·_ 로 구분된 경우만 제거(오탐 방지). */
var _CO_ALI=['삼성화재','현대해상','DB손해보험','KB손해보험','삼성','현대','메리츠','한화','롯데','흥국','DB','KB','당사','S사','H사','D사','K사'];
var _CASE_W=['최초신규','타사만기도래','타사만기미도래','만기도래','만기미도래','신규','갱신'];
function _stripLead(s,toks){for(var i=0;i<toks.length;i++){var t=toks[i];if(s.indexOf(t)===0&&(s.length===t.length||/[\s_]/.test(s.charAt(t.length))))return s.slice(t.length).replace(/^[\s_]+/,'');}return s;}
function dispName(name){var s=(''+name).trim();var s2=_stripLead(s,_CO_ALI);s2=_stripLead(s2,_CASE_W);return s2||s;}
/* 기록 표시이름: 회사·케이스 접두어 제거 + '화면명 › 세부단계' 병합 (STEP번호는 유지). 세부단계 없으면 화면명만 */
/* 세부단계(이름2) 추론 — 기록에 substep이 없으면 화면명에서 STEP 토큰 뒤 한글토큰을 2번째 이름으로 */
function _deriveSub(screen){var toks=(''+(screen||'')).split(/[_\-\s]+/).filter(Boolean);var si=-1;for(var i=0;i<toks.length;i++){if(/STEP\s*0*\d+/i.test(toks[i])){si=i;break;}}if(si<0)return '';for(var j=si+1;j<toks.length;j++){var t=toks[j].replace(/\([^)]*\)/g,'').trim();if(t&&/[가-힣]/.test(t)&&!/^(만기미도래|만기도래|갱신|신규|현기차|현기)$/.test(t))return t;}return '';}
function recDisp(r){var nm=dispName((r&&(r.screen||r.step))||'단계');var sub=((r&&r.substep)||'').trim()||_deriveSub((r&&r.screen)||'');if(!sub)return nm;var e=sub.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');var base=nm.replace(new RegExp('\\s*'+e+'\\s*$'),'').trim()||nm;return base+' › '+sub;}
/* 플로우 이미지 표시: 'img'=적정 길이(크롭) / 'full'=긴 캡쳐 전체 펼치기 / 'text'=텍스트만 */
function imgOn(){return flowImgMode==='img'||flowImgMode==='full';}
function imgCSS(h){return flowImgMode==='full'?'width:100%;height:auto;object-fit:contain;display:block;cursor:pointer':'width:100%;height:'+h+'px;object-fit:cover;object-position:top center;display:block;cursor:pointer';}
/* 변형 썸네일(공용): urls 배열 → 1장이면 단일, 여러 장이면 ◀ k/N ▶ 페이저. 텍스트모드는 'N개 변형' */
function variantThumb(urls,h){urls=(urls||[]).filter(function(u){return u;});if(!imgOn())return urls.length>1?'<div style="font-size:10px;color:var(--brand-600);font-weight:700;margin-top:3px">'+urls.length+'개 변형</div>':'';if(!urls.length)return '<div class="thumb" style="margin-top:5px;height:48px">캡쳐 없음</div>';if(urls.length===1)return '<div class="thumb" style="padding:0;overflow:hidden;border-style:solid;height:auto;margin-top:5px"><img src="'+esc(urls[0])+'" loading="lazy" style="'+imgCSS(h)+'" data-lb="1"></div>';var vkey='v'+(_vid++);_variantStore[vkey]=urls;return '<div class="thumb" style="padding:0;overflow:hidden;border-style:solid;height:auto;margin-top:5px"><img class="vimg" data-vkey="'+vkey+'" data-vidx="0" data-lb="1" src="'+esc(urls[0])+'" loading="lazy" style="'+imgCSS(h)+'"></div><div style="display:flex;align-items:center;justify-content:center;gap:6px;margin-top:4px;font-size:11px"><button data-vnav="'+vkey+'" data-d="-1" style="border:1px solid var(--line);background:#fff;border-radius:6px;cursor:pointer;padding:1px 7px">◀</button><span class="vpage" data-vkey="'+vkey+'" style="font-weight:700;color:var(--brand-600)">1/'+urls.length+'</span><button data-vnav="'+vkey+'" data-d="1" style="border:1px solid var(--line);background:#fff;border-radius:6px;cursor:pointer;padding:1px 7px">▶</button></div>';}
var _BR_PREF=['신규','타사만기도래','타사만기미도래'],_BR_COL={'신규':'#16a34a','타사만기도래':'#e0850f','타사만기미도래':'#6b8ff3'};
function _stripStep(s){return (''+s).replace(/^\s*STEP\s*0*\d+\s*/i,'').trim();}
function _nm2(st){var p=_variantBase(st[0]).split(' › ');var n1=_stripStep(p[0])||p[0];return {n1:n1,n2:(p[1]||n1)};}
function _thumb2(co,st,h){if(!imgOn())return '';var u=SHOTS[shotKey(co,st[0])]||'';return u?'<div class="thumb" style="padding:0;overflow:hidden;border-style:solid;height:auto;margin-top:5px"><img class="vimg" src="'+esc(u)+'" loading="lazy" style="'+imgCSS(h)+'"></div>':'<div class="thumb" style="margin-top:5px;height:46px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:11px">캡쳐 없음</div>';}
/* 분기 칸 전용 — 전체 펼치기 모드에서도 고정 높이(거대해지지 않게). object-fit:cover */
function _capThumb(co,st,h){if(!imgOn())return '';var u=SHOTS[shotKey(co,st[0])]||'';return u?'<div class="thumb" style="padding:0;overflow:hidden;border-style:solid;height:auto;margin-top:5px"><img class="vimg" src="'+esc(u)+'" loading="lazy" data-lb="1" style="width:100%;height:'+h+'px;object-fit:cover;object-position:top center;display:block;cursor:pointer"></div>':'<div class="thumb" style="margin-top:5px;height:42px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:10px">캡쳐 없음</div>';}
/* 한 정규단계(canon)의 step들을 분기 박스(고객타입별)와 공통 step으로 분리.
   분기 변형은 이름이 달라도(차량선택/차량확인/차량입력) 타사만기도래/미도래 존재 시 같은 순번끼리 묶는다. */
function _splitBranch(steps){var by={'신규':[],'타사만기도래':[],'타사만기미도래':[]};
 steps.forEach(function(st){var b=st[3];if(b==='타사만기도래')by['타사만기도래'].push(st);else if(b==='타사만기미도래')by['타사만기미도래'].push(st);else by['신규'].push(st);});
 var nPos=Math.max(by['타사만기도래'].length,by['타사만기미도래'].length),boxes=[];
 for(var k=0;k<nPos;k++){var box={};_BR_PREF.forEach(function(b){if(by[b][k])box[b]=by[b][k];});boxes.push(box);}
 return {boxes:boxes,common:by['신규'].slice(nPos),hasBranch:nPos>0};}
function pivotRender(){const host=document.getElementById('pivot');_variantStore={};_vid=0;host.innerHTML=upFilter?'<div class="caphint" style="margin:0 0 8px;"><span style="color:var(--brand);font-weight:800;">★ 업셀링 시점</span> — 담보선택에서 상위 담보·특약 제안, 산출완료 직후 업셀링 화면으로 객단가↑ (적합성 준수)</div>':'';const items=pmode==='case'?COMPS:CASES;
 var _drawn=0;items.forEach(function(it){const d=pmode==='case'?(DATA[pcase]&&DATA[pcase][it]):(DATA[it]&&DATA[it][pcomp]);if(!d)return;_drawn++;var _co=pmode==='case'?it:pcomp;
  /* STEP(canon=이름1)별 밴드 카드 → 카드 안에 이름2 화면들을 순번 가로 나열. 같은 이름2가 분기(st[3])로 갈라지면 분기 가로 칸으로 */
  var byCanon=[],ci={};d.steps.forEach(function(st,i){var cn=(st[2]!=null&&(''+st[2]).trim()!=='')?('c'+st[2]):('s'+i);if(ci[cn]==null){ci[cn]=byCanon.length;byCanon.push({canon:(st[2]!=null?st[2]:null),steps:[]});}byCanon[ci[cn]].steps.push(st);});
  var cards=byCanon.map(function(card){
    var h1={};card.steps.forEach(function(st){h1[_nm2(st).n1]=1;});var heads=Object.keys(h1);var band=(card.canon!=null?'STEP'+card.canon:'화면')+(heads.length===1?' '+heads[0]:'');
    /* 분기 박스(고객타입) + 공통 이름2 묶음 분리 */
    var sp=_splitBranch(card.steps),units=[];
    sp.boxes.forEach(function(box){units.push({branch:box});});
    var ci2={},commons=[];sp.common.forEach(function(st){var b=_variantBase(st[0]);if(ci2[b]==null){ci2[b]=commons.length;commons.push({n2:_nm2(st).n2,items:[]});}commons[ci2[b]].items.push(st);});
    commons.forEach(function(c){units.push({common:c});});
    var inner=units.map(function(u,sidx){
      var num=(sidx+1)+'.';
      if(u.branch){/* 분기: 서브밴드(이름1) + 신규/타사만기도래/미도래 가로 칸 (이미지2) */
        var box=u.branch,rep=box['신규']||box['타사만기도래']||box['타사만기미도래'],up=isUpStep(rep[0]),subName=_nm2(rep).n1;
        var bx=_BR_PREF.filter(function(b){return box[b];}).map(function(b){var st=box[b],c=_BR_COL[b];return '<div style="flex:0 0 122px;border:1.5px solid '+c+';border-radius:8px;padding:5px 6px;background:#fff"><div style="font-size:10px;font-weight:800;color:'+c+';margin-bottom:2px;text-align:center">'+esc(b)+'</div><div style="font-size:10px;color:#555;text-align:center;line-height:1.2;margin-bottom:1px">'+esc(_nm2(st).n2||_nm2(st).n1)+'</div>'+_capThumb(_co,st,116)+'</div>';}).join('');
        return '<div class="node'+(up?' upnode':'')+'" style="flex:0 0 auto;border-color:var(--brand)"><div style="font-size:11px;font-weight:800;color:var(--brand-600);text-align:center;background:var(--brand-50);border-radius:6px;padding:3px 8px;margin-bottom:6px">'+num+esc(subName)+(up?' ★':'')+' · 고객타입 분기</div><div style="display:flex;gap:6px;align-items:flex-start">'+bx+'</div></div>';
      }
      /* 공통 이름2: 캡쳐 1장(여러 변형이면 ◀1/N▶ 페이저) */
      var sub=u.common,up=isUpStep(sub.items[0][0]),multi=sub.items.length>1,urls=sub.items.map(function(st){return SHOTS[shotKey(_co,st[0])]||'';});
      var _th='',pager='';
      if(imgOn()){
        if(multi){var vkey='v'+(_vid++);_variantStore[vkey]=urls;var u0=urls[0];
          _th='<div class="thumb" style="padding:0;overflow:hidden;border-style:solid;height:auto;margin-top:5px">'+(u0?'<img class="vimg" data-vkey="'+vkey+'" data-vidx="0" src="'+esc(u0)+'" loading="lazy" style="'+imgCSS(150)+'">':'<div style="height:110px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:11px">캡쳐 없음</div>')+'</div>';
          pager='<div style="display:flex;align-items:center;justify-content:center;gap:6px;margin-top:4px;font-size:11px"><button data-vnav="'+vkey+'" data-d="-1" style="border:1px solid var(--line);background:#fff;border-radius:6px;cursor:pointer;padding:1px 7px">◀</button><span class="vpage" data-vkey="'+vkey+'" style="font-weight:700;color:var(--brand-600)">1/'+sub.items.length+'</span><button data-vnav="'+vkey+'" data-d="1" style="border:1px solid var(--line);background:#fff;border-radius:6px;cursor:pointer;padding:1px 7px">▶</button></div>';
        } else { _th=_thumb2(_co,sub.items[0],150); }
      } else if(multi){ pager='<div style="font-size:10px;color:var(--brand-600);margin-top:3px;font-weight:700">'+sub.items.length+'개 변형</div>'; }
      var first=sub.items[0],_upc=first[6]||'',_fee=first[7]||'',_btn=first[4];
      return '<div class="node'+(up?' upnode':'')+'" style="min-width:118px;margin:0"><div style="font-size:11px;font-weight:700;line-height:1.3">'+num+esc(sub.n2)+(up?' <span style="color:var(--brand)">★</span>':'')+(multi?' <span style="font-size:10px;color:var(--brand-600);font-weight:700">('+sub.items.length+')</span>':'')+'</div>'+_th+pager+((_btn!=null&&_btn!=='')?'<div style="font-size:10px;margin-top:2px;color:#6b7180;font-weight:700">🔘 버튼 '+esc(_btn)+'</div>':'')+(up?'<div style="font-size:11px;margin-top:3px;color:var(--brand-600);font-weight:700">객단가↑ 제안</div>':'')+((_upc||_fee)?'<div style="font-size:10px;margin-top:2px;color:#b45309;font-weight:700">💡 '+esc(_upc||'제안담보')+(_fee?' · '+esc(_fee):'')+'</div>':'')+'</div>';
    }).join('<span class="arrow" style="align-self:center">→</span>');
    return '<div style="border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#fff;flex:0 0 auto"><div style="background:var(--brand);color:#fff;font-size:11px;font-weight:800;text-align:center;padding:3px 9px;letter-spacing:.3px">'+esc(band)+'</div><div style="display:flex;align-items:flex-start;gap:4px;padding:8px">'+inner+'</div></div>';
  }).join('<span class="arrow" style="align-self:center">→</span>');
  const me=pmode==='case'&&it==='당사';host.innerHTML+='<div class="frow"><div class="flabel'+(me?' fme':'')+'">'+it+'</div><div class="fline" style="align-items:stretch">'+cards+'</div></div>';
 });if(!_drawn)host.innerHTML+=liveMode()?'<div class="caphint">아직 분석된 캡쳐가 없습니다. <b>관리자 도구(mask-tool.html) → 측정 기록</b>에서 화면을 확인·기록하면 이 플로우가 채워집니다.</div>':'<div class="caphint">표시할 데이터가 없습니다.</div>';}
document.getElementById('pivot')&&document.getElementById('pivot').addEventListener('click',function(e){var nav=e.target.closest('[data-vnav]');if(nav){var vkey=nav.getAttribute('data-vnav'),dd=+nav.getAttribute('data-d'),urls=_variantStore[vkey]||[];if(!urls.length)return;var img=this.querySelector('.vimg[data-vkey="'+vkey+'"]'),pg=this.querySelector('.vpage[data-vkey="'+vkey+'"]');if(!img)return;var idx=(+img.getAttribute('data-vidx')||0);idx=((idx+dd)%urls.length+urls.length)%urls.length;img.setAttribute('data-vidx',idx);if(urls[idx])img.src=urls[idx];if(pg)pg.textContent=(idx+1)+'/'+urls.length;e.stopPropagation();return;}var im=e.target.closest('img.vimg');if(im){var lb=document.getElementById('lbimg');if(lb){lb.src=_fullOf[im.src]||im.src;document.getElementById('lightbox').classList.add('on');}}});

/* ── 2) 단계별 분석 (고객 케이스별 · DATA 기반 → 항상 채워짐) ── */
let curCase2="신규";
/* 케이스: 신규(최초신규·타사만기 도래/미도래) / 갱신(당사) — 한 줄 표현 */
const STEP_ORDER=["차량확인","운전자정보","본인인증","정보입력","정보확인","담보선택","담보조정","산출완료","업셀링","결제하기","가입완료"];
function caseChipRow(cur){function ch(v){return '<span class="chip'+(v===cur?' on':'')+'" data-v="'+v+'">'+esc(caseLabel(v))+'</span>';}return '<span class="cgrp">가입유형</span>'+ch("신규")+ch("갱신");}/* 가입유형=신규/갱신만 (분기는 신규 플로우 안에서) */
function stepCaseChips(){document.getElementById('stpcase').innerHTML=caseChipRow(curCase2);}
function stepSummary(){var host=document.getElementById('stpsummary');if(!host)return;
 var html='<h2>단계 순서 요약 <span class="lbl" style="font-weight:600">· 정규단계 기준 · 공통/전용 정리</span></h2><div class="caphint" style="margin:2px 0 10px;">정규단계 번호순 · <b style="color:var(--brand)">[OO전용]</b>=특정 유형만(공통은 표시 생략) · <i>숫자</i>=입력수 · ★=업셀 · 당사=빨강</div>';
 var cases=Object.keys(DATA);
 html+=COMPS.map(function(co){
   var pcs=cases.filter(function(cs){return DATA[cs]&&DATA[cs][co]&&DATA[cs][co].steps&&DATA[cs][co].steps.length;});
   if(!pcs.length)return '';
   var me=co==='당사',byCanon={},order=[];
   pcs.forEach(function(cs){DATA[cs][co].steps.forEach(function(st,i){var canon=(st[2]!=null?st[2]:(i+1));if(!byCanon[canon]){byCanon[canon]={canon:canon,name:st[0],cases:{},cnt:st[1]};order.push(canon);}byCanon[canon].cases[cs]=st[0];if(cs==='신규'){byCanon[canon].name=st[0];byCanon[canon].cnt=st[1];}});});
   order=order.filter(function(v,i,a){return a.indexOf(v)===i;}).sort(function(a,b){return a-b;});
   var seq=order.map(function(canon){var n=byCanon[canon],cw=Object.keys(n.cases),common=cw.length===pcs.length,tag=common?'':(cw.map(function(c){return caseLabel(c);}).join('/')+'전용'),up=isUpStep(n.name);return '<span class="seqstep'+(up?' up':'')+'">'+canon+'. '+esc(n.name)+(up?'★':'')+(tag?' <small style="color:var(--brand)">['+esc(tag)+']</small>':'')+(n.cnt?' <i>'+n.cnt+'</i>':'')+'</span>';}).join('<span class="seqar">›</span>');
   return '<div class="seqrow'+(me?' me':'')+'"><span class="seqco">'+esc(co)+'</span><span class="seqline">'+seq+'</span></div>';
 }).join('')||'<div class="caphint">표시할 데이터가 없습니다.</div>';
 host.innerHTML=html;}
function stepNamesFor(cs){var seen={},names=[];COMPS.forEach(function(co){var d=DATA[cs]&&DATA[cs][co];if(!d)return;d.steps.forEach(function(st){if(!seen[st[0]]){seen[st[0]]=1;names.push(st[0]);}});});names.sort(function(a,b){var ia=STEP_ORDER.indexOf(a),ib=STEP_ORDER.indexOf(b);return (ia<0?99:ia)-(ib<0?99:ib);});return names;}
/* 단계 선택도 순서요약과 동일하게 정규단계(canon)로 묶음 */
function stepCanonGroups(cs){var byCanon={},order=[];COMPS.forEach(function(co){var d=DATA[cs]&&DATA[cs][co];if(!d)return;d.steps.forEach(function(st,i){var canon=(st[2]!=null?st[2]:(i+1));if(!byCanon[canon]){byCanon[canon]={canon:canon,name:_variantBase(st[0]),fromMe:false};order.push(canon);}if(co==='당사'){byCanon[canon].name=_variantBase(st[0]);byCanon[canon].fromMe=true;}else if(!byCanon[canon].fromMe){byCanon[canon].name=_variantBase(st[0]);}});});order=order.filter(function(v,i,a){return a.indexOf(v)===i;}).sort(function(a,b){return a-b;});return {order:order,byCanon:byCanon};}
function canonAgg(cs,co,canon){var d=DATA[cs]&&DATA[cs][co];if(!d||canon==null)return null;var sts=[];d.steps.forEach(function(st,i){var c=(st[2]!=null?st[2]:(i+1));if(c===canon)sts.push(st);});if(!sts.length)return null;var fields=[],fseen={},r=null;sts.forEach(function(st){var sd=STEP[st[0]]&&STEP[st[0]][co];if(sd){if(sd.f)sd.f.forEach(function(f){if(f&&!fseen[f]){fseen[f]=1;fields.push(f);}});if(sd.r&&!r)r=sd.r;}});var cnt=fields.length||sts.reduce(function(s,st){return s+(st[1]||0);},0);return {cnt:cnt,fields:fields,r:r,vcount:sts.length};}
/* 단계별 순서 표(정규단계 매트릭스) + 자동 분석 — 경쟁사 단계를 STEP별로 정리 */
function stepTable(){var host=document.getElementById('stptable');if(!host)return;
 function parseNm(s){var nm=_variantBase(s),p=nm.split(' › '),n1=(p[0]||'').replace(/^\s*STEP\s*0*\d+\s*/i,'').trim()||(p[0]||'');return {n1:n1,n2:(p[1]||n1)};}
 function isOther(b){return b==='타사만기도래'||b==='타사만기미도래';}/* 공통분기만 카운트 */
 function canonOf(st,i){return (st[2]!=null&&(''+st[2]).trim()!=='')?parseInt(st[2],10):(i+1);}
 var th='border:1px solid var(--line);padding:5px 8px;font-size:12px;';
 function tbl(cs){
  var cosWith=COMPS.filter(function(co){return DATA[cs]&&DATA[cs][co]&&DATA[cs][co].steps&&DATA[cs][co].steps.length;});
  if(!cosWith.length)return '';
  var cols=[],colKey={};
  function ensureCol(canon,n1,label,key,isBr){var k=canon+'|'+key;if(colKey[k]==null){colKey[k]=cols.length;cols.push({canon:canon,n1:n1,label:label,key:k,isBr:isBr,seq:cols.length});}else if(n1&&!cols[colKey[k]].n1){cols[colKey[k]].n1=n1;}return k;}
  var comp={};/* 회사별 칸 캡쳐개수 */
  cosWith.forEach(function(co){
   var byCanon=[],ci={};DATA[cs][co].steps.forEach(function(st,i){var cn=canonOf(st,i),ck='c'+cn;if(ci[ck]==null){ci[ck]=byCanon.length;byCanon.push({canon:cn,steps:[]});}byCanon[ci[ck]].steps.push(st);});
   var counts={};
   byCanon.forEach(function(card){var sp=_splitBranch(card.steps),headN1=parseNm(card.steps[0][0]).n1;
    sp.boxes.forEach(function(box,pos){var rep=box['신규']||box['타사만기도래']||box['타사만기미도래'],n1=parseNm(rep[0]).n1,k=ensureCol(card.canon,n1,n1,'#br'+pos,true);counts[k]=box['신규']?1:0;/* 공통분기(신규)만 카운트 */});
    var g={};sp.common.forEach(function(st){var n2=parseNm(st[0]).n2;g[n2]=(g[n2]||0)+1;});
    Object.keys(g).forEach(function(n2){var k=ensureCol(card.canon,headN1,n2,n2,false);counts[k]=g[n2];});
   });
   comp[co]=counts;
  });
  cols.sort(function(a,b){return a.canon-b.canon||a.seq-b.seq;});
  var groups=[],gi={};cols.forEach(function(c){var k='c'+c.canon;if(gi[k]==null){gi[k]=groups.length;groups.push({canon:c.canon,n1:c.n1,cols:[]});}groups[gi[k]].cols.push(c);if(c.n1&&!groups[gi[k]].n1)groups[gi[k]].n1=c.n1;});
  var top='<tr><th rowspan="2" style="'+th+'background:#faf7f2;font-weight:700">회사</th>'+groups.map(function(g){return '<th colspan="'+g.cols.length+'" style="'+th+'background:var(--brand);color:#fff;font-weight:800">STEP'+g.canon+' '+esc(g.n1||'')+'</th>';}).join('')+'</tr>';
  var sub='<tr>'+groups.map(function(g){return g.cols.map(function(c,j){return '<th style="'+th+'background:#f3eee6;font-weight:700;font-size:11px;white-space:nowrap">'+(j+1)+'.'+esc(c.label)+(c.isBr?' <small style="color:var(--brand);font-weight:800">분기</small>':'')+'</th>';}).join('');}).join('')+'</tr>';
  var body=cosWith.map(function(co){var me=co==='당사';return '<tr><td style="'+th+'font-weight:700;text-align:left;'+(me?'color:var(--bad)':'')+'">'+esc(co)+'</td>'+cols.map(function(c){var v=(comp[co]&&comp[co][c.key])||0;return '<td style="'+th+'text-align:center;'+(me?'background:#fff6ef;font-weight:800;color:var(--bad)':'font-weight:600')+'">'+(v||'<span style="color:#ccc">·</span>')+'</td>';}).join('')+'</tr>';}).join('');
  return '<div style="margin-bottom:18px"><div style="font-weight:800;font-size:14px;color:var(--brand-600);margin:0 0 6px">📋 '+esc(caseLabel(cs))+'</div><div style="overflow-x:auto"><table style="border-collapse:collapse;min-width:max-content">'+top+sub+body+'</table></div></div>';
 }
 var head='<h2>단계 비교 표 <span class="lbl" style="font-weight:600">· 신규 / 갱신 · 화면별 캡쳐 개수</span></h2><div class="caphint" style="margin:2px 0 10px">행=회사 · 상단=STEP(이름1) → 하단=순번.이름2 · 칸=그 회사가 그 화면에서 측정한 <b>캡쳐 개수</b>. <b>공통분기만</b> 카운트(타사만기도래·미도래 변형 제외). 당사=빨강.</div>';
 var t1=tbl('신규'),t2=tbl('갱신');
 host.innerHTML=head+(t1||'')+(t2||'')+((!t1&&!t2)?'<div class="caphint">표시할 데이터가 없습니다.</div>':'');
}
function stepChips(){var g=stepCanonGroups(curCase2);if(g.order.indexOf(curCanon)<0)curCanon=g.order.length?g.order[0]:null;document.getElementById('stp').innerHTML=g.order.map(function(canon){var n=g.byCanon[canon];return '<span class="chip'+(canon===curCanon?' on':'')+'" data-canon="'+canon+'">'+canon+'. '+esc(n.name)+'</span>';}).join('');}
function stepCount(cs,co,name){var d=DATA[cs]&&DATA[cs][co];if(!d)return null;for(var i=0;i<d.steps.length;i++)if(d.steps[i][0]===name)return d.steps[i][1];return null;}
function stepRender(){var canon=curCanon,g=stepCanonGroups(curCase2),n0=(canon!=null?g.byCanon[canon]:null),label=n0?(canon+'. '+n0.name):'';
 var aggs={},cos=COMPS.filter(function(c){var a=canonAgg(curCase2,c,canon);if(a)aggs[c]=a;return !!a;});
 if(!cos.length){document.getElementById('svz').innerHTML='';document.getElementById('ssum').innerHTML='<div class="summary info">이 케이스에는 해당 단계가 없습니다.</div>';document.getElementById('sdet').innerHTML='';return;}
 var counts=cos.map(function(c){return aggs[c].cnt;});var max=Math.max.apply(null,counts),min=Math.min.apply(null,counts),minCo=cos[counts.indexOf(min)],mine=aggs['당사']?aggs['당사'].cnt:null;
 var viz='<div class="caphint" style="margin:0 0 9px">선택 단계에서 <b>회사별 입력 항목 수</b> — 적을수록 가입이 쉬움. <span style="color:var(--good);font-weight:700">초록=최소(가장 쉬움)</span> · <span style="color:var(--bad);font-weight:700">빨강=최다</span> · ★=자사</div>';cos.forEach(function(c){var n=aggs[c].cnt,me=c==='당사';var col=(n===min?'var(--good)':(n===max&&max>min?'var(--bad)':'var(--brand)'));viz+='<div class="barrow"><span class="nm'+(me?' me':'')+'">'+esc(c)+(me?' ★':'')+'</span><span class="track"><span class="fill" style="width:'+Math.round(n/(max||1)*100)+'%;background:'+col+'"></span></span><span class="sc" style="color:'+col+'">'+n+'</span></div>';});document.getElementById('svz').innerHTML=viz;
 document.getElementById('ssum').innerHTML='<div class="summary'+(mine!=null&&mine>min?'':' info')+'"><b>'+esc(caseLabel(curCase2))+' · '+esc(label)+'</b> — '+(mine!=null?'당사 '+mine+'개'+(mine===max&&max>min?' (최다)':''):'당사 해당 단계 없음')+', 최소 '+esc(minCo)+' '+min+'개.'+(mine!=null&&mine>min?' 입력 '+(mine-min)+'개 줄일 여지.':'')+'</div>';
 var det='';cos.forEach(function(c){var a=aggs[c],n=a.cnt,me=c==='당사';var r=a.r||(n===min?'good':(n===max&&max>min?'bad':'mid')),rc=RC[r];var fields=a.fields.length?a.fields.join(' · '):(n>0?'주요 입력 '+n+'개':'입력 없음 (확인·결과 화면)');var vlab=a.vcount>1?' <span style="color:var(--brand-600);font-weight:700">('+a.vcount+'변형)</span>':'';det+='<div class="stp"><span style="font-weight:'+(me?'600':'400')+';">'+esc(c)+(me?' (자사)':'')+vlab+' <span style="color:var(--muted);font-weight:600;">입력 '+n+'</span><br><span style="font-size:11px;color:#999;">'+esc(fields)+'</span></span><span class="badge" style="background:'+rc[0]+';color:'+rc[1]+';">'+rc[2]+'</span></div>';});document.getElementById('sdet').innerHTML=det;}

/* ── 3) 용어 비교 ── */
function termChips(){document.getElementById('termchips').innerHTML=Object.keys(TERM).map(function(t){return '<span class="chip'+(t===curTerm?' on':'')+'" data-v="'+t+'">'+t+'</span>';}).join('');}
function termRender(){const d=TERM[curTerm];
 /* ① 표준 용어·의미 */
 document.getElementById('thead').innerHTML='<div class="head"><div class="term">'+esc(d.official)+'</div><div class="def">뜻: '+esc(d.def)+'</div></div>';
 /* 경쟁사 = 자사(당사) 제외 — 캡쳐된 근거 데이터 */
 const comps=COMPS.filter(function(c){return c!=='당사'&&d.comp[c];});
 let good=0,bad=0;comps.forEach(function(c){if(d.comp[c].r==='good')good++;if(d.comp[c].r==='bad')bad++;});
 const best=comps.filter(function(c){return d.comp[c].r==='good';})[0];
 document.getElementById('tsum').innerHTML='<div class="summary info">경쟁사 표현 <b>'+comps.length+'</b>곳 · 쉽게 풀어씀 <b>'+good+'</b> · 용어만 노출 <b>'+bad+'</b>. 아래 <b>당사 표현은 제안(샘플)</b>입니다.</div>';
 /* ② 경쟁사 표현 (캡쳐 근거) */
 let html='<div class="lbl" style="margin:4px 0 8px;">② 경쟁사 표현 <span style="color:var(--muted);">— 캡쳐 근거</span></div>';
 comps.forEach(function(c){const x=d.comp[c],rc=RT[x.r],isBest=(c===best);html+='<div class="trow"><span class="co">'+esc(c)+(isBest?'<br><span style="font-size:10px;color:var(--good);">벤치마크</span>':'')+'</span><span class="txt"><span class="q'+(x.r==='bad'?' bad':'')+'">"'+esc(x.t)+'"</span></span><span class="badge" style="background:'+rc[0]+';color:'+rc[1]+';">'+rc[2]+'</span></div>';});
 if(!comps.length)html+='<div class="caphint">아직 캡쳐된 경쟁사 표현이 없습니다.</div>';
 /* ③ 당사 표현 (제안 · 샘플) */
 html+='<div class="lbl" style="margin:16px 0 8px;">③ 당사 표현 <span style="color:var(--muted);">— 제안 · 샘플</span></div>';
 html+='<div class="tcard"><div class="kv" style="border-top:none;padding-top:0;"><span class="k">고객 친화적 권장 표현</span><span class="v rec">"'+esc(d.rec)+'"</span></div>';
 if(d.comp['당사']){const u=d.comp['당사'],ru=RT[u.r];html+='<div class="kv"><span class="k">현재 당사 표현 (샘플)</span><span class="v"><span class="q'+(u.r==='bad'?' bad':'')+'">"'+esc(u.t)+'"</span> &nbsp;<span class="badge" style="background:'+ru[0]+';color:'+ru[1]+';">'+ru[2]+'</span></span></div>';}
 html+='<div class="diag">'+esc(best?('벤치마크('+best+')처럼 핵심 뜻을 인라인으로 노출하는 것을 제안합니다.'):'권장 표현처럼 쉬운 설명을 함께 노출하세요.')+'</div></div>';
 document.getElementById('trows').innerHTML=html;}

var flowImgMode='img';/* 'img' 이미지 보기 / 'text' 텍스트만 */
document.getElementById('flowview').addEventListener('click',function(e){if(!e.target.dataset.v)return;this.querySelectorAll('button').forEach(function(x){x.classList.remove('on');});e.target.classList.add('on');var map=e.target.dataset.v==='map';document.getElementById('flow-list').style.display=map?'none':'block';document.getElementById('flow-map').style.display=map?'block':'none';if(map)flowPivotRender();});
document.getElementById('flowimg')&&document.getElementById('flowimg').addEventListener('click',function(e){if(!e.target.dataset.fi)return;flowImgMode=e.target.dataset.fi;this.querySelectorAll('button').forEach(function(x){x.classList.remove('on');});e.target.classList.add('on');pivotRender();try{flowPivotRender();}catch(_){}});
document.getElementById('t4sub')&&document.getElementById('t4sub').addEventListener('click',function(e){if(!e.target.dataset.s)return;this.querySelectorAll('button').forEach(function(x){x.classList.remove('on');});e.target.classList.add('on');var s=e.target.dataset.s;document.querySelectorAll('#t4 .t4p').forEach(function(p){p.style.display=(p.dataset.p===s)?'block':'none';});document.querySelector('.content').scrollTop=0;});
document.getElementById('mode').addEventListener('click',function(e){if(!e.target.dataset.m)return;this.querySelectorAll('button').forEach(function(x){x.classList.remove('on');});e.target.classList.add('on');pmode=e.target.dataset.m;renderFixed();pivotRender();flowPivotRender();});
document.getElementById('fixed').addEventListener('click',function(e){if(e.target.dataset.upf){upFilter=!upFilter;renderFixed();pivotRender();return;}if(!e.target.dataset.v)return;if(pmode==='case')pcase=e.target.dataset.v;else pcomp=e.target.dataset.v;renderFixed();pivotRender();flowPivotRender();});
document.getElementById('stpcase').addEventListener('click',function(e){if(!e.target.dataset.v)return;curCase2=e.target.dataset.v;stepCaseChips();stepSummary();stepChips();stepRender();});
document.getElementById('stp').addEventListener('click',function(e){if(e.target.dataset.canon==null)return;this.querySelectorAll('.chip').forEach(function(x){x.classList.remove('on');});e.target.classList.add('on');curCanon=+e.target.dataset.canon;stepRender();});
document.getElementById('termchips').addEventListener('click',function(e){if(!e.target.dataset.v)return;curTerm=e.target.dataset.v;termChips();termRender();});

/* ── 마스킹 캡쳐 보관/표시 + 이미지 유사도(분기 플로우용) ── */
/* 관리자 도구(mask-tool)에서 검수 완료한 마스킹본(IndexedDB) → 용어 탭에 썸네일로 표시 */
function idbOpen(){return new Promise(function(res,rej){var r=indexedDB.open('modooflow',1);r.onupgradeneeded=function(){r.result.createObjectStore('shots',{keyPath:'id'});};r.onsuccess=function(){res(r.result);};r.onerror=function(){rej(r.error);};});}
function idbAll(){return idbOpen().then(function(db){return new Promise(function(res){var tx=db.transaction('shots','readonly'),out=[];tx.objectStore('shots').openCursor().onsuccess=function(e){var c=e.target.result;if(c){out.push(c.value);c.continue();}else res(out);};});}).catch(function(){return [];});}
/* 캡쳐 썸네일 맵(회사|화면 → url)과 이미지 해시(aHash, 유사도 판정용) */
var SHOTS={},SHOTHASH={},_fullOf={};/* SHOTS=플로우용 썸네일 / _fullOf[썸네일URL]=원본URL (라이트박스 확대용) */
function shotKey(co,screen){return (co||'')+'|'+(screen||'');}
function aHash(url){return new Promise(function(res){try{var im=new Image();im.onload=function(){try{var c=document.createElement('canvas');c.width=8;c.height=8;var x=c.getContext('2d');x.drawImage(im,0,0,8,8);var d=x.getImageData(0,0,8,8).data,g=[],sum=0;for(var i=0;i<64;i++){var v=(d[i*4]*0.299+d[i*4+1]*0.587+d[i*4+2]*0.114);g.push(v);sum+=v;}var m=sum/64,h='';for(i=0;i<64;i++)h+=(g[i]>m?'1':'0');res(h);}catch(e){res(null);}};im.onerror=function(){res(null);};im.src=url;}catch(e){res(null);}});}
function hamming(a,b){if(!a||!b||a.length!==b.length)return 99;var n=0;for(var i=0;i<a.length;i++)if(a[i]!==b[i])n++;return n;}
function shotsRender(){idbAll().then(function(arr){
  SHOTS={};
  /* 캡쳐는 기록 id로 보관 → 기록의 '현재' 회사·화면명으로 키 매핑(이름 바뀌어도 정확) */
  var recById={};try{recGet().forEach(function(r){recById[r.id]=r;});}catch(e){}
  /* 이중 키: ①기록의 현재 회사·화면명 ②캡쳐 저장 당시 회사·화면명 — 둘 중 하나만 맞아도 이미지 표시(이름/CSV 변경에도 최대한 연결) */
  arr.forEach(function(s){var r=recById[s.id];var co=(r&&r.co)||s.co,screen=(r&&r.screen)||s.screen;var thumb=s.thumb||s.url;if(thumb&&s.url)_fullOf[thumb]=s.url;if(co&&screen){SHOTS[shotKey(co,screen)]=thumb;var dn=dispName(screen);if(dn!==screen&&!SHOTS[shotKey(co,dn)])SHOTS[shotKey(co,dn)]=thumb;if(r){var rd=recDisp(r);if(!SHOTS[shotKey(co,rd)])SHOTS[shotKey(co,rd)]=thumb;}}/* 플로우엔 썸네일, 라이트박스는 _fullOf로 원본 */if(s.co&&s.screen&&!SHOTS[shotKey(s.co,s.screen)])SHOTS[shotKey(s.co,s.screen)]=thumb;});
  try{pivotRender();}catch(e){}
  Promise.all(arr.map(function(s){return aHash(s.url).then(function(h){if(h){var r=recById[s.id];SHOTHASH[shotKey((r&&r.co)||s.co,(r&&r.screen)||s.screen)]=h;}});})).then(function(){try{flowPivotRender();}catch(e){}});
 });}
/* 마스킹 썸네일(용어 탭) 클릭 → 라이트박스 확대 */
document.getElementById('lightbox').addEventListener('click',function(){this.classList.remove('on');});

/* ── 6) 뉴스 감지 ── */
function nGet(id,def){try{return (JSON.parse(localStorage.getItem('cap_news_st')||'{}'))[id]||def;}catch(e){return def;}}
function nSet(id,st){let m={};try{m=JSON.parse(localStorage.getItem('cap_news_st')||'{}');}catch(e){}m[id]=st;localStorage.setItem('cap_news_st',JSON.stringify(m));}
/* 뉴스 설정(#9): 키워드 가중치·중복제거·알림 임계값 */
function nCfg(){try{var c=JSON.parse(localStorage.getItem('cap_news_cfg')||'{}');return {w:(c.w||{}),dedup:!!c.dedup,thr:(c.thr!=null?c.thr:2)};}catch(e){return {w:{},dedup:false,thr:2};}}
function nCfgSet(c){localStorage.setItem('cap_news_cfg',JSON.stringify(c));}
function newsScore(n,cfg){var s=0;(n.kws||[]).forEach(function(k){s+=(cfg.w[k]!=null?cfg.w[k]:1);});return s;}
function nTitleKey(t){return (t||'').replace(/\s+/g,'').replace(/[\[\]()·…,.\-—'"]/g,'').toLowerCase();}
function newsKw(){if(!document.getElementById('newskw'))return;var cfg=nCfg();document.getElementById('newskw').innerHTML=NKW.map(function(k){var w=(cfg.w[k]!=null?cfg.w[k]:1);return '<span class="chip'+(w>0?' on':'')+'" title="가중치 '+w+'">#'+esc(k)+(w!==1?' ×'+w:'')+'</span>';}).join('');}
function newsCfgRender(){var host=document.getElementById('newscfg');if(!host)return;var cfg=nCfg();
 host.innerHTML='<div class="form-grid" style="grid-template-columns:repeat(auto-fill,minmax(148px,1fr))">'+NKW.map(function(k){return '<label style="font-size:11px">'+esc(k)+'<input type="number" min="0" step="1" data-kw="'+esc(k)+'" value="'+(cfg.w[k]!=null?cfg.w[k]:1)+'"></label>';}).join('')+'</div>'
  +'<div style="display:flex;gap:16px;align-items:center;margin-top:12px;flex-wrap:wrap"><label style="font-size:12px"><input type="checkbox" id="nc_dedup"'+(cfg.dedup?' checked':'')+'> 중복 제거(제목 유사)</label><label style="font-size:12px">알림 임계값 <input type="number" id="nc_thr" min="0" value="'+cfg.thr+'" style="width:64px"></label><button class="btn" data-act="nc_save" style="width:auto;padding:8px 16px">저장</button><button class="btn" data-act="nc_reset" style="width:auto;padding:8px 16px;background:#9aa0ab;box-shadow:none">기본값</button></div>';}
function newsRender(){if(!document.getElementById('newslist'))return;var cfg=nCfg();var SRC=((window.NEWS&&window.NEWS.length)?window.NEWS:NEWS).slice();
 if(cfg.dedup){var seen={};SRC=SRC.filter(function(n){var k=nTitleKey(n.title);if(seen[k])return false;seen[k]=1;return true;});}
 SRC.sort(function(a,b){return newsScore(b,cfg)-newsScore(a,cfg);});
 var cN=0,cT=0,cD=0,cA=0;var SHARE='<svg class="ni" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 13v6a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-6"/><path d="M12 3v13M8 7l4-4 4 4"/></svg>';var MARK='<svg class="ni" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/></svg>';
 var cards=SRC.map(function(n,i){var st=nGet(n.id,n.st),b=NST[st];if(st==='new')cN++;if(st==='todo')cT++;if(st==='done')cD++;var sc=newsScore(n,cfg);var alarm=(cfg.thr>0&&sc>=cfg.thr&&st!=='ignore')?'<span class="badge st-new" title="가중치 '+sc+' ≥ 임계값 '+cfg.thr+'">🔔 알림</span>':'';if(alarm)cA++;var eid=esc(n.id);var acts='';if(st==='new')acts='<button class="pri" data-id="'+eid+'" data-to="todo">'+esc(n.co)+' 가입화면 점검</button><button data-id="'+eid+'" data-to="ignore">무시</button>';else if(st==='todo')acts='<button class="pri" data-id="'+eid+'" data-to="done">완료</button><button data-id="'+eid+'" data-to="new">되돌리기</button>';else acts='<button data-id="'+eid+'" data-to="new">되돌리기</button>';var kws=(n.kws||[]).map(function(k){return '<span class="kw">#'+esc(k)+'</span>';}).join('');return '<article class="nws'+(st==='ignore'?' off':'')+'">'+'<div class="nws-top"><span class="nws-num">'+(i+1)+'</span>'+'<span class="nws-ico">'+alarm+'<span class="badge '+b[1]+'">'+b[0]+'</span>'+SHARE+MARK+'</span></div>'+'<h4 class="nws-title">'+esc(n.title)+'</h4>'+'<div class="nws-kws">'+kws+'</div>'+'<div class="nws-date">'+esc(n.co)+' · '+esc(n.src)+' · '+esc(n.date)+'</div>'+'<div class="nws-acts">'+acts+'</div></article>';}).join('');var sampleNote=(window.NEWS&&window.NEWS.length)?'':'<div class="ds-note" style="margin-bottom:10px;">📌 예시(샘플) — 실데이터는 <code>news_watch.py</code>가 수집한 공개 뉴스로 자동 갱신됩니다.</div>';document.getElementById('newssum').innerHTML=sampleNote+'<div class="summary info">신규 감지 <b>'+cN+'</b> · 점검 대기 <b>'+cT+'</b> · 완료 <b>'+cD+'</b> · 🔔 알림 <b>'+cA+'</b></div>';document.getElementById('newslist').innerHTML=cards;}
document.getElementById('newslist')&&document.getElementById('newslist').addEventListener('click',function(e){if(!e.target.dataset.id)return;nSet(e.target.dataset.id,e.target.dataset.to);newsRender();});
document.getElementById('newscfg')&&document.getElementById('newscfg').addEventListener('click',function(e){var act=e.target.dataset.act;if(!act)return;if(act==='nc_save'){var w={};this.querySelectorAll('input[data-kw]').forEach(function(i){w[i.dataset.kw]=Math.max(0,+i.value||0);});nCfgSet({w:w,dedup:document.getElementById('nc_dedup').checked,thr:Math.max(0,+document.getElementById('nc_thr').value||0)});newsKw();newsCfgRender();newsRender();alert('뉴스 감지 설정을 저장했습니다.');}else if(act==='nc_reset'){localStorage.removeItem('cap_news_cfg');newsKw();newsCfgRender();newsRender();}});
document.getElementById('newsrefresh')&&document.getElementById('newsrefresh').addEventListener('click',function(){alert('뉴스 감지는 news_watch.py(카카오 알림 포함)가 생성하는 newsdata.js를 읽습니다.\n\n실제 연동:\n1) python3 news_watch.py 로 키워드 뉴스 감지\n2) 신규 기사 → 카카오톡 \'나에게 보내기\' 알림\n3) newsdata.js 갱신 → 이 화면에 자동 반영\n\n경쟁사 가입사이트 자동 접근·캡쳐는 하지 않으며, 가입화면 점검은 사람이 수동으로 합니다.');});

/* ── 7) 퍼널 리포트 (Looker Studio 임베드) ──
   Looker Studio '임베드 URL'을 넣으면 이 자리에 리포트가 표시되고, 없으면 '샘플 이미지'를 보여준다. */
function lsValid(u){return /^https:\/\/(lookerstudio|datastudio)\.google\.com\/embed\/[^\s"'<>]+$/.test(u);}
var DEFAULT_LS="";/* 여기에 Looker Studio 임베드 URL을 넣으면 자동으로 바로 떠요 (예: https://lookerstudio.google.com/embed/reporting/...) */
var SAMPLE_IMG="";/* 직접 캡쳐한 샘플 이미지를 쓰려면 경로 지정 (예: "assets/ds_sample.png"). 비우면 내장 샘플 그래픽 표시 */
/* 내장 샘플 리포트 그래픽 (자리표시) — 실제 데이터 아님. 회색 처리로 '샘플'임을 표시 */
function sampleReportSVG(){
 var don=[['351.8 88',0,'#9aa0ab'],['44 395.8',-351.8,'#bcc1cb'],['26.4 413.4',-395.8,'#d2d6de'],['17.6 422.2',-422.2,'#e4e7ec']]
  .map(function(s){return '<circle cx="170" cy="150" r="70" fill="none" stroke="'+s[2]+'" stroke-width="28" stroke-dasharray="'+s[0]+'" stroke-dashoffset="'+s[1]+'" transform="rotate(-90 170 150)"/>';}).join('');
 var usr='380,158 430,120 480,134 530,108 580,148 630,96 680,80 730,128 780,114 830,142 880,170 930,198 960,186';
 var nu ='380,200 430,166 480,176 530,158 580,186 630,134 680,150 730,170 780,164 830,182 880,206 930,226 960,214';
 var kpi=[['Sessions','80.0K'],['Users','61.2K'],['New Users','56.9K'],['Bounce','47.6%'],['Pages/Sess','5.5'],['Conv. Rate','17.9%']];
 var kx=40,kw=150,ky=320;
 var kpis=kpi.map(function(k,i){var x=kx+i*kw;return '<rect x="'+x+'" y="'+ky+'" width="'+(kw-14)+'" height="86" rx="9" fill="#f4f5f8" stroke="#e3e6ec"/>'
  +'<text x="'+(x+16)+'" y="'+(ky+30)+'" font-size="12" fill="#9aa0ab">'+k[0]+'</text>'
  +'<text x="'+(x+16)+'" y="'+(ky+64)+'" font-size="26" font-weight="800" fill="#6b7180">'+k[1]+'</text>';}).join('');
 return '<svg viewBox="0 0 980 430" width="100%" font-family="-apple-system,Apple SD Gothic Neo,sans-serif">'
  +'<rect width="980" height="430" fill="#ffffff"/>'
  +'<rect x="20" y="20" width="320" height="250" rx="10" fill="#fbfbfc" stroke="#eceef2"/><text x="40" y="50" font-size="14" font-weight="700" fill="#7c828d">유입 채널 (Top Acquisition)</text>'+don
  +'<text x="170" y="156" text-anchor="middle" font-size="18" font-weight="800" fill="#8b909a">79.9%</text>'
  +'<rect x="360" y="20" width="600" height="250" rx="10" fill="#fbfbfc" stroke="#eceef2"/><text x="380" y="50" font-size="14" font-weight="700" fill="#7c828d">사용자 추이 (Users vs. New)</text>'
  +'<polyline points="'+usr+'" fill="none" stroke="#a7adb8" stroke-width="2.5"/><polyline points="'+nu+'" fill="none" stroke="#c6c0d0" stroke-width="2.5"/>'
  +'<line x1="380" y1="250" x2="960" y2="250" stroke="#e3e6ec"/>'
  +kpis+'</svg>';
}
function lsSamplePanel(){
 var img=SAMPLE_IMG?'<img src="'+esc(SAMPLE_IMG)+'" alt="데이터스튜디오 샘플 리포트" style="width:100%;display:block;">':sampleReportSVG();
 return '<div class="ds-sample"><span class="ds-badge">샘플 · SAMPLE</span>'+img+'</div>';
}
function lsRender(){const w=document.getElementById('lswrap');if(!w)return;const u=localStorage.getItem('cap_ls_url')||DEFAULT_LS;const inp=document.getElementById('lsurl');if(u&&inp)inp.value=u;if(!u){w.innerHTML=lsSamplePanel();return;}const f=document.createElement('iframe');f.className='lsframe';f.src=u;f.setAttribute('allowfullscreen','');f.setAttribute('sandbox','allow-scripts allow-same-origin allow-popups allow-forms');w.innerHTML='';w.appendChild(f);}
document.getElementById('lsload')&&document.getElementById('lsload').addEventListener('click',function(){const u=document.getElementById('lsurl').value.trim();if(!lsValid(u)){alert('Looker Studio 임베드 URL만 허용됩니다.\n예: https://lookerstudio.google.com/embed/reporting/...\n\n(리포트 → 공유 → 보고서 임베드 에서 복사)');return;}localStorage.setItem('cap_ls_url',u);lsRender();});
document.getElementById('lsopen')&&document.getElementById('lsopen').addEventListener('click',function(){const u=(localStorage.getItem('cap_ls_url')||document.getElementById('lsurl').value.trim());if(!lsValid(u)){alert('먼저 올바른 임베드 URL을 입력/불러오기 하세요.');return;}window.open(u,'_blank','noopener');});
document.getElementById('lsclear')&&document.getElementById('lsclear').addEventListener('click',function(){localStorage.removeItem('cap_ls_url');document.getElementById('lsurl').value='';lsRender();});

/* ── 5) A/B 시나리오 + Figma SVG 내보내기 ── */
function abRows(t){return [["가설",t.hyp],["주지표",t.metric],["가드레일 지표",t.guard],["대상·세그먼트",t.seg],["표본·MDE",t.sample+" · MDE "+t.mde],["기간",t.period],["성공기준",t.success]];}
/* 디자인 제안서: 분석(개선·업셀) → 디자인 제안 + AI 프롬프트 + 디자이너 요청 자동 생성 → 피그마/AI로 내보내기 */
var _designBriefMD='';
function designBriefRender(){var host=document.getElementById('designbrief');if(!host)return;var items=[];
 if(typeof UPSELL!=='undefined'&&UPSELL.length){var u=UPSELL[0];items.push({t:'업셀링 팝업 — '+u.up,why:u.benefit+' ('+u.effect+')',prompt:'자동차보험 견적완료 직후 노출되는 모바일 업셀링 팝업을 디자인해줘.\n- 제안: "'+u.up+'"\n- 혜택 문구: "'+u.ment+'"\n- 금액 강조 예: +월 1만원(총 10만원)\n- 1탭 [지금 추가] / [나중에] 2버튼, 혜택 3줄 이내, 과장 없는 신뢰형 톤, 적합성 안내 1줄.',ask:'견적완료 후 업셀 팝업 1종 — '+u.up+' 제안. 수락/나중에 2버튼, 혜택 3줄, 금액(+10만원) 강조.'});}
 try{var ins=deriveInsights();(ins.improve||[]).slice(0,4).forEach(function(im){items.push({t:im[0],why:im[1],prompt:'자동차보험 가입플로우 개선안 화면(모바일 세로)을 디자인해줘.\n- 개선: "'+im[0]+'"\n- 근거: '+im[1]+'\n- 해결방향: '+im[2]+'\n- 진행률 표시, 입력 최소화, 핵심 CTA 1개.',ask:im[0]+' → '+im[2]});});}catch(e){}
 if(!items.length){host.innerHTML='<div class="caphint">개선·업셀 데이터가 쌓이면 제안서가 자동 생성됩니다.</div>';_designBriefMD='';return;}
 var md='# 디자인 요청서 (분석 기반 자동 생성)\n\n';
 host.innerHTML=items.map(function(it,i){md+='## '+(i+1)+'. '+it.t+'\n- 근거: '+it.why+'\n- 디자이너 요청: '+it.ask+'\n- AI 프롬프트:\n```\n'+it.prompt+'\n```\n\n';
  return '<div class="sec" style="margin-bottom:10px;background:#fbfbfd"><div style="font-weight:700;font-size:13px;margin-bottom:4px">'+(i+1)+'. '+esc(it.t)+'</div>'
   +'<div class="caphint" style="margin:0 0 6px">근거: '+esc(it.why)+'</div>'
   +'<div style="font-size:12px;margin-bottom:4px"><b style="color:var(--brand-600)">🧑‍🎨 디자이너 요청</b><br>'+esc(it.ask)+'</div>'
   +'<div style="font-size:12px"><b style="color:#6b8ff3">🤖 AI 프롬프트</b><pre style="white-space:pre-wrap;background:#fff;border:1px solid var(--line);border-radius:6px;padding:8px;margin:3px 0 0;font-size:11.5px;font-family:inherit">'+esc(it.prompt)+'</pre></div></div>';}).join('');
 _designBriefMD=md;}
document.getElementById('db_copy')&&document.getElementById('db_copy').addEventListener('click',function(){if(!_designBriefMD){alert('생성된 제안서가 없습니다.');return;}if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(_designBriefMD).then(function(){alert('디자인 제안서를 복사했습니다. AI(클로드 등)·노션·피그마 설명에 붙여넣으세요.');},function(){alert('복사 실패: 브라우저 권한을 확인하세요.');});}else alert('이 브라우저는 자동 복사를 지원하지 않습니다.');});
document.getElementById('db_md')&&document.getElementById('db_md').addEventListener('click',function(){if(!_designBriefMD){alert('생성된 제안서가 없습니다.');return;}var blob=new Blob([_designBriefMD],{type:'text/markdown'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='디자인요청서.md';a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},1500);});
function abRender(){document.getElementById('ablist').innerHTML=ABTESTS.map(function(t){const c=ABPRI[t.pri]||ABPRI[3];const rows=abRows(t).map(function(r){return '<tr><td class="lbl" style="width:92px;vertical-align:top;">'+r[0]+'</td><td style="text-align:left;">'+r[1]+'</td></tr>';}).join('');return '<div class="sec"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;"><span style="font-size:15px;font-weight:700;">'+t.name+'</span><span class="badge" style="background:'+c[0]+';color:'+c[1]+';">우선순위 '+t.pri+'</span></div><div class="ba" style="margin-bottom:10px;"><div class="abc"><div style="font-size:11px;color:#666;margin-bottom:5px;">변형 A · 현행</div><div style="font-size:12px;">'+t.a+'</div></div><div class="abc b"><div style="font-size:11px;color:#e0850f;margin-bottom:5px;">변형 B · 실험</div><div style="font-size:12px;">'+t.b+'</div></div></div><table>'+rows+'</table></div>';}).join('');}
function xmlEsc(s){return (''+s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function buildABSVG(){const W=820,padX=24;let y=64;const parts=['<text x="'+padX+'" y="40" font-size="22" font-weight="700" fill="#1a1f36">A/B 테스트 시나리오 · 요건정의</text>'];ABTESTS.forEach(function(t){const lines=[["변형","A: "+t.a+"    →    B: "+t.b]].concat(abRows(t));const cardH=30+lines.length*22+16;parts.push('<rect x="'+(padX-8)+'" y="'+y+'" rx="12" width="'+(W-2*padX+16)+'" height="'+cardH+'" fill="#ffffff" stroke="#e9ebf2"/>');parts.push('<text x="'+padX+'" y="'+(y+26)+'" font-size="15" font-weight="700" fill="#1a1f36">'+xmlEsc('우선순위 '+t.pri+'. '+t.name)+'</text>');let ly=y+26+24;lines.forEach(function(ln){parts.push('<text x="'+padX+'" y="'+ly+'" font-size="11" fill="#9aa0ab">'+xmlEsc(ln[0])+'</text>');parts.push('<text x="'+(padX+86)+'" y="'+ly+'" font-size="12" fill="#333">'+xmlEsc(ln[1])+'</text>');ly+=22;});y+=cardH+16;});const H=y+8;const svg='<svg xmlns="http://www.w3.org/2000/svg" width="'+W+'" height="'+H+'" viewBox="0 0 '+W+' '+H+'" font-family="-apple-system, Apple SD Gothic Neo, sans-serif"><rect width="'+W+'" height="'+H+'" fill="#f5f6fa"/>'+parts.join('')+'</svg>';return svg;}
function abSVG(){var svg=buildABSVG();var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml;charset=utf-8'}));a.download='ab_시나리오_요건정의.svg';a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},1500);}
function abPNG(){var svg=buildABSVG();var url=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml;charset=utf-8'}));var img=new Image();img.onload=function(){var s=2,c=document.createElement('canvas');c.width=img.width*s;c.height=img.height*s;var ctx=c.getContext('2d');ctx.fillStyle='#f5f6fa';ctx.fillRect(0,0,c.width,c.height);ctx.scale(s,s);ctx.drawImage(img,0,0);URL.revokeObjectURL(url);c.toBlob(function(b){var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='ab_시나리오.png';a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},1500);});};img.onerror=function(){URL.revokeObjectURL(url);alert('PNG 변환 실패 — SVG 저장을 사용하세요.');};img.src=url;}
/* Figma 미러 + 당사 화면 PNG */
function figValid(u){return /^https:\/\/([\w-]+\.)?figma\.com\//.test(u);}
function figOpen(){var u=document.getElementById('figurl').value.trim();if(!figValid(u)){alert('먼저 Figma URL을 입력하세요.');return;}window.open(u,'_blank','noopener');}
function figCapPNG(file){var rd=new FileReader();rd.onload=function(){var img=new Image();img.onload=function(){var c=document.createElement('canvas');c.width=img.naturalWidth;c.height=img.naturalHeight;c.getContext('2d').drawImage(img,0,0);var w=document.getElementById('figwrap');w.innerHTML='<div class="caphint">업로드한 당사 화면</div><img alt="당사 화면" src="'+c.toDataURL("image/png")+'" style="max-width:320px;border:1px solid var(--line);border-radius:10px;display:block;margin:8px 0;"><button class="btn" id="figcapdl" style="width:auto;padding:9px 16px;">이 화면 PNG로 저장</button>';document.getElementById('figcapdl').onclick=function(){c.toBlob(function(b){var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='당사화면.png';a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},1500);});};};img.src=rd.result;};rd.readAsDataURL(file);}
document.getElementById('figopen')&&document.getElementById('figopen').addEventListener('click',figOpen);
document.getElementById('figcap')&&document.getElementById('figcap').addEventListener('change',function(e){if(e.target.files&&e.target.files[0])figCapPNG(e.target.files[0]);e.target.value='';});
function abCopy(){const html=document.getElementById('ablist').innerHTML;if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(html).then(function(){alert('A/B 시나리오 HTML을 복사했습니다.\nFigma의 html.to.design 플러그인 → HTML 탭에 붙여넣으세요.');},function(){alert('복사 실패: 브라우저 클립보드 권한을 확인하세요.');});}else{alert('이 브라우저는 자동 복사를 지원하지 않습니다. SVG 내보내기를 사용하세요.');}}
document.getElementById('t4').addEventListener('click',function(e){const x=e.target.dataset.ab;if(x==='svg')abSVG();if(x==='html')abCopy();if(x==='png')abPNG();});


/* ── 9) 내보내기 (CSV / PDF) ── */
function csvEsc(v){v=(''+v);if(/^[=+\-@\t\r]/.test(v))v="'"+v;/* 엑셀 수식 인젝션 방어 */v=v.replace(/"/g,'""');return /[",\n\r]/.test(v)?'"'+v+'"':v;}
function dlCSV(name,rows){const csv=rows.map(function(r){return r.map(csvEsc).join(',');}).join('\r\n');const blob=new Blob(['﻿'+csv],{type:'text/csv;charset=utf-8;'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},1500);}
function exFlow(){const rows=[['케이스','회사','순서','단계명','입력항목수']];CASES.forEach(function(c){COMPS.forEach(function(co){const d=DATA[c]&&DATA[c][co];if(!d)return;d.steps.forEach(function(st,i){rows.push([c,co,i+1,st[0],st[1]]);});});});dlCSV('플로우_요약.csv',rows);}
function exStep(){const rows=[['단계','회사','입력항목수','입력항목','평가']];Object.keys(STEP).forEach(function(s){const data=STEP[s];COMPS.forEach(function(co){const d=data[co];if(!d)return;rows.push([s,co,d.f.length,d.f.join(' / '),RC[d.r][2]]);});});dlCSV('단계별_입력항목.csv',rows);}
function exTerm(){const rows=[['용어','뜻','회사','표현','평가']];Object.keys(TERM).forEach(function(t){const d=TERM[t];COMPS.forEach(function(co){const x=d.comp[co];if(!x)return;rows.push([d.official,d.def,co,x.t,RT[x.r][2]]);});});dlCSV('용어_표현비교.csv',rows);}
function curExport(){if(curTab==='t2')exStep();else if(curTab==='t3')exTerm();else if(curTab==='t1'||curTab==='t12')exFlow();else{exFlow();exStep();exTerm();}}
document.getElementById('expCsv').addEventListener('click',curExport);
document.getElementById('expPdf').addEventListener('click',function(){window.print();});

/* ── 플로우맵: 분기 다이어그램 (SVG) ── */
const NSHAPE={circle:{w:76,h:76,fill:"#ead9fb",stroke:"#9a6fd4",tc:"#5b3a87"},rect:{w:118,h:58,fill:"#fdeee0",stroke:"#e0850f",tc:"#33408f"},diamond:{w:120,h:84,fill:"#f6ddcf",stroke:"#c4724f",tc:"#8a4628"},sticky:{w:118,h:62,fill:"#f7eccb",stroke:"#d8c178",tc:"#7a6320"}};
const COLW=152,ROWH=104,PAD=24;
function buildLinear(co,cs){const d=DATA[cs]&&DATA[cs][co];const steps=d?d.steps:[];const nodes=[{id:"in",type:"circle",label:"진입",col:0,row:0}];let col=1;steps.forEach(function(st,i){nodes.push({id:"s"+i,type:"rect",label:st[0],col:col++,row:0});});nodes.push({id:"end",type:"sticky",label:"완료",col:col,row:0});const edges=[];for(var i=0;i<nodes.length-1;i++)edges.push({from:nodes[i].id,to:nodes[i+1].id});return {nodes:nodes,edges:edges};}
/* 신규 3종(최초신규·타사만기 도래/미도래)을 한 분기 다이어그램으로 — 공통 진입→유형 분기→공통 꼬리 재수렴 */
/* 공통 분기 다이어그램 빌더 — cases=[[key,label],…], seqs=[[단계명,…],…] → 진입→유형분기→공통 꼬리 재수렴 */
function _branchDiagram(cases,seqs){
 if(cases.length<2)return null;
 var rowMap=cases.length===2?[0,2]:cases.map(function(_x,i){return i;});
 var minLen=Math.min.apply(null,seqs.map(function(s){return s.length;})),suf=[];
 for(var i=1;i<=minLen;i++){var nm=seqs[0][seqs[0].length-i];if(seqs.every(function(s){return s[s.length-i]===nm;}))suf.unshift(nm);else break;}
 var uniq=seqs.map(function(s){return s.slice(0,s.length-suf.length);});
 var maxU=Math.max.apply(null,uniq.map(function(u){return u.length;}));
 var nodes=[{id:'in',type:'circle',label:'진입',col:0,row:1},{id:'br',type:'diamond',label:'고객\n유형?',col:1,row:1}],edges=[{from:'in',to:'br'}];
 cases.forEach(function(c,ci){var prev='br';uniq[ci].forEach(function(st,si){var id='u'+ci+'_'+si;nodes.push({id:id,type:'rect',label:st,col:2+si,row:rowMap[ci]});edges.push({from:prev,to:id,label:si===0?c[1]:''});prev=id;});edges.push({from:prev,to:'s0',label:uniq[ci].length?'':c[1]});});
 var startCol=2+maxU;
 if(!suf.length){nodes.push({id:'s0',type:'sticky',label:'완료',col:startCol,row:1});}
 else suf.forEach(function(st,si){nodes.push({id:'s'+si,type:(si===suf.length-1?'sticky':'rect'),label:st,col:startCol+si,row:1});if(si>0)edges.push({from:'s'+(si-1),to:'s'+si});});
 return {nodes:nodes,edges:edges};
}
function buildBranchNew(co){
 var dN=DATA['신규']&&DATA['신규'][co];
 /* 라이브: 신규 케이스 내부를 step의 분기(branch=index3)로 갈라 표시 (최초신규/타사만기 도래·미도래) */
 if(dN&&dN.steps&&dN.steps.some(function(s){return s[3];})){
  var pref=['신규','타사만기도래','타사만기미도래'],grp={},order=[];
  dN.steps.forEach(function(s){var br=s[3]||'신규';if(!grp[br]){grp[br]=[];order.push(br);}grp[br].push(s[0]);});
  order.sort(function(a,b){var ia=pref.indexOf(a),ib=pref.indexOf(b);return (ia<0?9:ia)-(ib<0?9:ib);});
  if(order.length<2)return buildLinear(co,'신규');
  return _branchDiagram(order.map(function(br){return [br,br];}),order.map(function(br){return grp[br];}))||buildLinear(co,'신규');
 }
 /* 샘플 폴백: DATA['신규'/'만기도래'/'만기미도래'] 키로 분기 (2종만 있어도 표시) */
 var allCases=[['신규','최초신규'],['만기도래','타사만기도래'],['만기미도래','타사만기미도래']];
 var cs2=allCases.filter(function(c){var d=DATA[c[0]]&&DATA[c[0]][co];return d&&d.steps&&d.steps.length;});
 if(!cs2.length)return buildLinear(co,'신규');
 if(cs2.length===1)return buildLinear(co,cs2[0][0]);
 return _branchDiagram(cs2.map(function(c){return [c[0],c[1]];}),cs2.map(function(c){return DATA[c[0]][co].steps.map(function(s){return s[0];});}))||buildLinear(co,'신규');
}
/* 실데이터 공통/분기: 신규·갱신 단계를 화면명 + 캡쳐 이미지 유사도(aHash)로 정렬 → 공통 백본 + 분기 */
function caseSteps(cs,co){var d=DATA[cs]&&DATA[cs][co];return d?d.steps.map(function(s){return s[0];}):[];}
function sameStep(co,a,b){if(a===b)return true;var ha=SHOTHASH[shotKey(co,a)],hb=SHOTHASH[shotKey(co,b)];return !!(ha&&hb&&hamming(ha,hb)<=8);}
function buildCaseBranchLive(co){
 var A=caseSteps('신규',co),B=caseSteps('갱신',co);
 if(!A.length&&!B.length)return buildLinear(co,'신규');
 if(!A.length)return buildLinear(co,'갱신');
 if(!B.length)return buildLinear(co,'신규');
 var m=A.length,n=B.length,dp=[],i,j;for(i=0;i<=m;i++){dp[i]=[];for(j=0;j<=n;j++)dp[i][j]=0;}
 for(i=1;i<=m;i++)for(j=1;j<=n;j++)dp[i][j]=sameStep(co,A[i-1],B[j-1])?dp[i-1][j-1]+1:Math.max(dp[i-1][j],dp[i][j-1]);
 var seq=[];i=m;j=n;while(i>0&&j>0){if(sameStep(co,A[i-1],B[j-1])){seq.unshift({t:'c',name:A[i-1]});i--;j--;}else if(dp[i-1][j]>=dp[i][j-1]){seq.unshift({t:'a',name:A[i-1]});i--;}else{seq.unshift({t:'b',name:B[j-1]});j--;}}
 while(i>0){seq.unshift({t:'a',name:A[i-1]});i--;}while(j>0){seq.unshift({t:'b',name:B[j-1]});j--;}
 var nodes=[{id:'in',type:'circle',label:'진입',col:0,row:1}],edges=[],col=1,lastA='in',lastB='in';
 seq.forEach(function(s,k){var id=s.t+k;
  if(s.t==='c'){nodes.push({id:id,type:'rect',label:s.name+'\n(공통)',col:col,row:1});edges.push({from:lastA,to:id});if(lastB!==lastA)edges.push({from:lastB,to:id});lastA=lastB=id;}
  else if(s.t==='a'){nodes.push({id:id,type:'rect',label:s.name,col:col,row:0});edges.push({from:lastA,to:id,label:(lastA===lastB?'신규':'')});lastA=id;}
  else{nodes.push({id:id,type:'rect',label:s.name,col:col,row:2});edges.push({from:lastB,to:id,label:(lastA===lastB?'갱신':'')});lastB=id;}
  col++;});
 nodes.push({id:'end',type:'sticky',label:'완료',col:col,row:1});edges.push({from:lastA,to:'end'});if(lastB!==lastA)edges.push({from:lastB,to:'end'});
 return {nodes:nodes,edges:edges};
}
function getFlowMap(){
 if(fmMode!=='diagram')return buildLinear(fmCo,fmCase);
 if(fmCase==='신규')return buildBranchNew(fmCo);                                  /* 신규 = 3종(최초신규·타사만기 도래/미도래) 분기 — 차량입력 유무 등으로 갈라짐 */
 if(fmCase==='갱신'){if(!liveMode()&&FLOWMAP[fmCo]&&FLOWMAP[fmCo]['갱신'])return FLOWMAP[fmCo]['갱신'];return buildLinear(fmCo,'갱신');}  /* 갱신은 갱신 플로우 그대로 */
 if(liveMode())return buildCaseBranchLive(fmCo);
 if(FLOWMAP[fmCo]&&FLOWMAP[fmCo][fmCase])return FLOWMAP[fmCo][fmCase];
 return buildLinear(fmCo,fmCase);}
function flowNodeSVG(n){const s=NSHAPE[n.type]||NSHAPE.rect;const cx=PAD+n.col*COLW+COLW/2,cy=PAD+n.row*ROWH+ROWH/2;let shape='';if(n.type==='circle')shape='<circle cx="'+cx+'" cy="'+cy+'" r="38" fill="'+s.fill+'" stroke="'+s.stroke+'" stroke-width="2"/>';else if(n.type==='diamond')shape='<polygon points="'+cx+','+(cy-42)+' '+(cx+60)+','+cy+' '+cx+','+(cy+42)+' '+(cx-60)+','+cy+'" fill="'+s.fill+'" stroke="'+s.stroke+'" stroke-width="2"/>';else shape='<rect x="'+(cx-s.w/2)+'" y="'+(cy-s.h/2)+'" width="'+s.w+'" height="'+s.h+'" rx="'+(n.type==='sticky'?4:13)+'" fill="'+s.fill+'" stroke="'+s.stroke+'" stroke-width="2"/>';const lines=n.label.split("\n"),tot=lines.length;const txt='<text x="'+cx+'" y="'+cy+'" text-anchor="middle" font-size="12.5" font-weight="700" fill="'+s.tc+'">'+lines.map(function(l,i){return '<tspan x="'+cx+'" dy="'+(i===0?(tot>1?'-0.2em':'0.32em'):'1.15em')+'">'+xmlEsc(l)+'</tspan>';}).join('')+'</text>';return shape+txt;}
function flowHalf(n){return (NSHAPE[n.type]||NSHAPE.rect).w/2*(n.type==='circle'?1:1);}
function flowmapRender(){const fm=getFlowMap();const byId={};fm.nodes.forEach(function(n){byId[n.id]=n;});const maxCol=Math.max.apply(null,fm.nodes.map(function(n){return n.col;})),maxRow=Math.max.apply(null,fm.nodes.map(function(n){return n.row;}));const W=PAD*2+(maxCol+1)*COLW,H=PAD*2+(maxRow+1)*ROWH;function cx(n){return PAD+n.col*COLW+COLW/2;}function cy(n){return PAD+n.row*ROWH+ROWH/2;}function hw(n){return n.type==='circle'?38:(NSHAPE[n.type]||NSHAPE.rect).w/2;}let edges='',labels='';fm.edges.forEach(function(e){const a=byId[e.from],b=byId[e.to];if(!a||!b)return;const sx=cx(a)+hw(a),sy=cy(a),ex=cx(b)-hw(b),by=cy(b);const mx=sx+Math.max(18,(ex-sx)/2);edges+='<path d="M'+sx+','+sy+' H'+mx+' V'+by+' H'+ex+'" fill="none" stroke="#aab0c2" stroke-width="2" marker-end="url(#fmarr)"/>';if(e.label)labels+='<rect x="'+(mx-15)+'" y="'+((sy+by)/2-19)+'" width="30" height="15" rx="4" fill="#fff" opacity="0.9"/><text x="'+mx+'" y="'+((sy+by)/2-8)+'" text-anchor="middle" font-size="10.5" font-weight="700" fill="#6b7180">'+xmlEsc(e.label)+'</text>';});const nodes=fm.nodes.map(flowNodeSVG).join('');document.getElementById('flowmap').innerHTML='<svg width="'+W+'" height="'+H+'" viewBox="0 0 '+W+' '+H+'" font-family="-apple-system,Apple SD Gothic Neo,sans-serif"><defs><marker id="fmarr" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#aab0c2"/></marker></defs>'+edges+labels+nodes+'</svg>';}
let fmCo="당사",fmCase="신규",fmMode="diagram";
function fmChips(){var _e=document.getElementById('fmchips');if(!_e)return;_e.innerHTML=COMPS.map(function(c){return '<span class="chip'+(c===fmCo?' on':'')+'" data-v="'+c+'">'+c+(c==='당사'?' (자사)':'')+'</span>';}).join('');}
function fmCaseChips(){var _e=document.getElementById('fmcase');if(!_e)return;_e.innerHTML='<span class="chip'+(fmCase==='신규'?' on':'')+'" data-v="신규">신규 (3종 분기)</span><span class="chip'+(fmCase==='갱신'?' on':'')+'" data-v="갱신">당사 갱신</span>';}
function fmHint(){var _e=document.getElementById('fmhint');if(!_e)return;var t=(fmMode!=='diagram')?'순차 흐름':(fmCase==='신규'?'신규 3종(최초신규·타사만기 도래/미도래) 분기 → 공통 단계로 재수렴':'분기 다이어그램');_e.textContent=t;}
document.getElementById('fmchips')&&document.getElementById('fmchips').addEventListener('click',function(e){if(!e.target.dataset.v)return;fmCo=e.target.dataset.v;fmChips();flowmapRender();fmHint();});
document.getElementById('fmcase')&&document.getElementById('fmcase').addEventListener('click',function(e){if(!e.target.dataset.v)return;fmCase=e.target.dataset.v;fmCaseChips();flowmapRender();fmHint();});
document.getElementById('fmmode')&&document.getElementById('fmmode').addEventListener('click',function(e){if(!e.target.dataset.v)return;fmMode=e.target.dataset.v;this.querySelectorAll('button').forEach(function(b){b.classList.remove('on');});e.target.classList.add('on');flowmapRender();fmHint();});

/* ── 플로우 보기: 실제 캡쳐 swim-lane 비교 ── */
/* 분기 자동 도출 + 마스터 플로우(회사 고정): 정규단계 번호로 케이스를 정렬해 공통/전용/생략 표시 */
/* SVG 다이어그램 문자열 생성(공용) — fm={nodes,edges} */
function fmSVG(fm){var byId={};fm.nodes.forEach(function(n){byId[n.id]=n;});var maxCol=Math.max.apply(null,fm.nodes.map(function(n){return n.col;})),maxRow=Math.max.apply(null,fm.nodes.map(function(n){return n.row;}));var W=PAD*2+(maxCol+1)*COLW,H=PAD*2+(maxRow+1)*ROWH;function cx(n){return PAD+n.col*COLW+COLW/2;}function cy(n){return PAD+n.row*ROWH+ROWH/2;}function hw(n){return n.type==='circle'?38:(NSHAPE[n.type]||NSHAPE.rect).w/2;}var edges='',labels='';fm.edges.forEach(function(e){var a=byId[e.from],b=byId[e.to];if(!a||!b)return;var sx=cx(a)+hw(a),sy=cy(a),ex=cx(b)-hw(b),by=cy(b);var mx=sx+Math.max(18,(ex-sx)/2);edges+='<path d="M'+sx+','+sy+' H'+mx+' V'+by+' H'+ex+'" fill="none" stroke="#aab0c2" stroke-width="2" marker-end="url(#fmarr)"/>';if(e.label)labels+='<rect x="'+(mx-26)+'" y="'+((sy+by)/2-19)+'" width="52" height="15" rx="4" fill="#fff" opacity="0.92"/><text x="'+mx+'" y="'+((sy+by)/2-8)+'" text-anchor="middle" font-size="10" font-weight="700" fill="#b96b08">'+xmlEsc(e.label)+'</text>';});var nodes=fm.nodes.map(flowNodeSVG).join('');return '<svg width="'+W+'" height="'+H+'" viewBox="0 0 '+W+' '+H+'" font-family="-apple-system,Apple SD Gothic Neo,sans-serif"><defs><marker id="fmarr" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#aab0c2"/></marker></defs>'+edges+labels+nodes+'</svg>';}
function buildLinearDiagram(names){var nodes=[{id:'in',type:'circle',label:'진입',col:0,row:0}],edges=[],col=1;names.forEach(function(nm,i){nodes.push({id:'s'+i,type:'rect',label:nm,col:col++,row:0});});nodes.push({id:'end',type:'sticky',label:'완료',col:col,row:0});for(var i=0;i<nodes.length-1;i++)edges.push({from:nodes[i].id,to:nodes[i+1].id});return {nodes:nodes,edges:edges};}
/* 수렴형 분기도: 공통 진입 → ◆(차량입력 등) 분기 → 고객타입별 병렬 → 공통 재수렴 → 완료 */
function buildBranchDiagram(labels,seqs){
 if(seqs.length<2)return buildLinearDiagram(seqs[0]||[]);
 var minL=Math.min.apply(null,seqs.map(function(s){return s.length;}));
 /* 공통 흡수 안 함 — 각 분기에 정규단계 전체를 그대로 표시(차량입력만 ◆로 분기) */
 var pre=0,suf=0;
 var prefix=seqs[0].slice(0,pre),suffix=seqs[0].slice(seqs[0].length-suf);
 var mids=seqs.map(function(s){return s.slice(pre,s.length-suf);});
 var maxMid=Math.max.apply(null,mids.map(function(m){return m.length;}));
 var nB=labels.length,rowMap=[];if(nB===2){rowMap=[0,2];}else{for(var i=0;i<nB;i++)rowMap.push(i);}
 var bb=nB===2?1:Math.floor((nB-1)/2);
 var nodes=[],edges=[],col=0,prev='in';
 nodes.push({id:'in',type:'circle',label:'진입',col:col++,row:bb});
 prefix.forEach(function(nm,i){var id='p'+i;nodes.push({id:id,type:'rect',label:nm,col:col++,row:bb});edges.push({from:prev,to:id});prev=id;});
 nodes.push({id:'br',type:'diamond',label:'차량입력\\n분기',col:col++,row:bb});edges.push({from:prev,to:'br'});
 var midStartCol=col,lasts=[];
 labels.forEach(function(lab,bi){var p='br';mids[bi].forEach(function(nm,j){var id='b'+bi+'_'+j;nodes.push({id:id,type:'rect',label:nm,col:midStartCol+j,row:rowMap[bi]});edges.push({from:p,to:id,label:j===0?lab:''});p=id;});lasts.push({id:p,empty:mids[bi].length===0,label:lab});});
 var sufStartCol=midStartCol+Math.max(1,maxMid),reconvId,endCol;
 if(suffix.length){suffix.forEach(function(nm,j){var id='s'+j;nodes.push({id:id,type:'rect',label:nm,col:sufStartCol+j,row:bb});if(j>0)edges.push({from:'s'+(j-1),to:id});});reconvId='s0';endCol=sufStartCol+suffix.length;}
 else{reconvId='end';endCol=sufStartCol;}
 lasts.forEach(function(l){edges.push({from:l.id,to:reconvId,label:l.empty?l.label:''});});
 nodes.push({id:'end',type:'sticky',label:'완료',col:endCol,row:bb});
 if(suffix.length)edges.push({from:'s'+(suffix.length-1),to:'end'});
 return {nodes:nodes,edges:edges};
}
/* 정규단계(canon) 정렬 분기도: 같은 STEP은 공통 한 줄, 위계1이 다른 STEP(차량입력)만 분기 → 재합류 */
function buildBranchDiagram2(labels,seqs){
 if(labels.length<2)return buildLinearDiagram((seqs[0]||[]).map(function(st){return _variantBase(st[0]).replace(' › ','\n');}));
 function strip(s){return (''+s).replace(/^\s*STEP\s*0*\d+\s*/i,'').trim();}
 function nm1(st){return strip(_variantBase(st[0]).split(' › ')[0])||_variantBase(st[0]);}
 function lbl(st){var p=_variantBase(st[0]).split(' › '),m=strip(p[0])||p[0];return m+(p[1]?'\n'+p[1]:'');}
 var byCanon={},canons=[];
 labels.forEach(function(lab,ti){seqs[ti].forEach(function(st,i){var c=(st[2]!=null&&(''+st[2]).trim()!=='')?parseInt(st[2],10):(i+1);if(isNaN(c))c=i+1;if(!byCanon[c]){byCanon[c]={};canons.push(c);}byCanon[c][ti]=st;});});
 canons=canons.filter(function(v,i,a){return a.indexOf(v)===i;}).sort(function(a,b){return a-b;});
 var nB=labels.length,rowMap=nB===2?[0,2]:[0,1,2],bbRow=1;
 var nodes=[{id:'in',type:'circle',label:'진입',col:0,row:bbRow}],edges=[],col=1,lastOf={};
 labels.forEach(function(_x,ti){lastOf[ti]='in';});
 canons.forEach(function(cn){var m=byCanon[cn],tis=Object.keys(m).map(Number);
  var names=tis.map(function(ti){return _variantBase(m[ti][0]);});/* 공통 판정=전체 이름(위계1+위계2) 동일. 차량선택처럼 세부가 다르면 분기 */
  var common=(tis.length===nB)&&names.every(function(n){return n===names[0];});
  if(common){var id='c'+cn;nodes.push({id:id,type:'rect',label:lbl(m[tis[0]]),col:col,row:bbRow});var fr={};labels.forEach(function(_x,ti){fr[lastOf[ti]]=1;});Object.keys(fr).forEach(function(f){edges.push({from:f,to:id});});labels.forEach(function(_x,ti){lastOf[ti]=id;});}
  else{tis.forEach(function(ti){var st=m[ti],id='b'+cn+'_'+ti;nodes.push({id:id,type:'rect',label:lbl(st),col:col,row:rowMap[ti]});var f=lastOf[ti],dv=(f==='in'||f.charAt(0)==='c');edges.push({from:f,to:id,label:dv?labels[ti]:''});lastOf[ti]=id;});}
  col++;});
 nodes.push({id:'end',type:'sticky',label:'완료',col:col,row:bbRow});
 var fr={};labels.forEach(function(_x,ti){fr[lastOf[ti]]=1;});Object.keys(fr).forEach(function(f){edges.push({from:f,to:'end'});});
 return {nodes:nodes,edges:edges};
}
/* 노드 라벨: 위계1(STEP접두어 제거) + 위계2(2줄) */
function _stepLbl(st){var p=_variantBase(st[0]).split(' › '),m=(''+(p[0]||'')).replace(/^\s*STEP\s*0*\d+\s*/i,'').trim()||(p[0]||'');return m+(p[1]?'\n'+p[1]:'');}
/* 한 회사 전체 흐름: 진입 → 가입유형(신규/갱신) 분기, 신규는 차량입력에서 고객타입 분기→재합류, 갱신은 별도 줄 */
function buildCaseFlow(co){
 function stepsOf(cs){return (DATA[cs]&&DATA[cs][co]&&DATA[cs][co].steps&&DATA[cs][co].steps.length)?DATA[cs][co].steps:null;}
 var pref=['신규','타사만기도래','타사만기미도래'],blabels=[],bseqs=[];
 var dN=stepsOf('신규');
 if(dN){if(dN.some(function(s){return s[3];})){var grp={},ord=[];dN.forEach(function(s){var br=s[3]||'신규';if(!grp[br]){grp[br]=[];ord.push(br);}grp[br].push(s);});ord.sort(function(a,b){var ia=pref.indexOf(a),ib=pref.indexOf(b);return (ia<0?9:ia)-(ib<0?9:ib);});ord.forEach(function(br){blabels.push(br);bseqs.push(grp[br]);});}else{blabels.push('신규');bseqs.push(dN);}}
 if(stepsOf('만기도래')){blabels.push('타사만기도래');bseqs.push(stepsOf('만기도래'));}
 if(stepsOf('만기미도래')){blabels.push('타사만기미도래');bseqs.push(stepsOf('만기미도래'));}
 var renew=stepsOf('갱신');
 var fm=null;
 if(bseqs.length>=2)fm=buildBranchDiagram2(blabels,bseqs);
 else if(bseqs.length===1)fm=buildLinearDiagram(bseqs[0].map(_stepLbl));
 if(fm)fm.edges.forEach(function(e){if(e.from==='in'&&!e.label)e.label='신규';});
 if(!renew)return fm||{nodes:[{id:'in',type:'circle',label:'진입',col:0,row:0}],edges:[]};
 if(!fm){var lin=buildLinearDiagram(renew.map(_stepLbl));lin.edges.forEach(function(e){if(e.from==='in'&&!e.label)e.label='갱신';});return lin;}
 var maxRow=Math.max.apply(null,fm.nodes.map(function(n){return n.row;})),gRow=maxRow+1,prev='in';
 renew.forEach(function(st,k){var id='g'+k;fm.nodes.push({id:id,type:'rect',label:_stepLbl(st),col:k+1,row:gRow});fm.edges.push({from:prev,to:id,label:k===0?'갱신':''});prev=id;});
 fm.nodes.push({id:'gend',type:'sticky',label:'완료',col:renew.length+1,row:gRow});fm.edges.push({from:prev,to:'gend'});
 return fm;
}
function branchFlowRender(){
 var host=document.getElementById('flowpivot');if(!host)return;
 function nmP(st){var p=_variantBase(st[0]).split(' › ');return {n1:_stripStep(p[0])||p[0],n2:p[1]||''};}
 function thumbOf(co,st,h){if(!imgOn())return '';var url=SHOTS[shotKey(co,st[0])]||'';return url?'<div class="thumb" style="padding:0;overflow:hidden;border-style:solid;height:auto;margin-top:4px"><img src="'+esc(url)+'" loading="lazy" data-lb="1" style="'+imgCSS(h)+'"></div>':'<div class="thumb" style="margin-top:4px;height:36px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:10px">캡쳐 없음</div>';}
 function stepNode(co,st){var p=nmP(st),up=isUpStep(st[0]);return '<div class="node'+(up?' upnode':'')+'" style="flex:0 0 130px"><div style="font-size:11.5px;font-weight:700;line-height:1.3">'+esc(p.n1)+(up?' ★':'')+'</div>'+(p.n2?'<div style="font-size:10px;color:#888;font-weight:600">↳ '+esc(p.n2)+'</div>':'')+thumbOf(co,st,140)+'</div>';}
 var arrow='<span class="arrow">→</span>';
 /* 한 회사·가입유형 → 정규단계(canon)별 가로 백본. 분기 단계만 고객타입 세로 병렬 스택 → 재합류. */
 function buildLine(co,cs){var d=DATA[cs]&&DATA[cs][co],steps=(d&&d.steps&&d.steps.length)?d.steps:null;if(!steps)return null;
  var byCanon=[],ci={};steps.forEach(function(st,i){var cn=(st[2]!=null&&(''+st[2]).trim()!=='')?('c'+st[2]):('s'+i);if(ci[cn]==null){ci[cn]=byCanon.length;byCanon.push([]);}byCanon[ci[cn]].push(st);});
  return byCanon.map(function(group){var sp=_splitBranch(group);
   if(!sp.hasBranch)return group.map(function(st){return stepNode(co,st);}).join(arrow);
   var box=sp.boxes[0],hdr=nmP(box['신규']||box['타사만기도래']||box['타사만기미도래']).n1;
   var rws=_BR_PREF.filter(function(b){return box[b];}).map(function(b){var st=box[b],c=_BR_COL[b],p=nmP(st);
     return '<div style="border:1.5px solid '+c+';border-radius:8px;padding:5px 7px;background:#fff;display:flex;align-items:flex-start;gap:8px"><div style="flex:0 0 82px"><div style="font-size:10px;font-weight:800;color:'+c+'">'+esc(b)+'</div><div style="font-size:11px;font-weight:700;line-height:1.2;margin-top:1px">'+esc(p.n2||p.n1)+'</div></div><div style="flex:1;min-width:78px">'+_capThumb(co,st,108)+'</div></div>';}).join('');
   var branchNode='<div class="node" style="flex:0 0 auto;border-color:var(--brand);background:var(--brand-50);min-width:222px"><div style="font-size:11px;font-weight:800;color:var(--brand-600);text-align:center;border-bottom:2px solid var(--brand);padding-bottom:3px;margin-bottom:6px">◆ '+esc(hdr)+' 분기</div><div style="display:flex;flex-direction:column;gap:6px">'+rws+'</div></div>';
   return branchNode+(sp.common.length?arrow+sp.common.map(function(st){return stepNode(co,st);}).join(arrow):'');
  }).join(arrow);
 }
 function sec(label,color,bg,bd,inner){return '<div class="sec" style="background:'+bg+';border-color:'+bd+'"><div style="font-weight:800;font-size:13px;color:'+color+';margin-bottom:8px">'+label+'</div><div class="fline" style="overflow-x:auto;align-items:stretch">'+inner+'</div></div>';}
 var entry='<div class="node" style="flex:0 0 56px;align-self:center;background:#fff;border-color:var(--brand);text-align:center;font-weight:800;color:var(--brand-600)">진입</div>';
 var rows='',hint='';
 if(pmode==='comp'){/* 회사 고정 → 가입유형(신규/갱신) 비교 */
  var co=pcomp,lN=buildLine(co,'신규'),lR=buildLine(co,'갱신');
  if(lN)rows+=sec('🟠 신규','var(--brand-600)','#fffaf3','#f0dca0',lN);
  if(lR)rows+=(rows?'<div style="height:10px"></div>':'')+sec('🔵 갱신','#3b5bdb','#f5f7fb','#d8def0',lR);
  hint=esc(co)+' · 진입 → 가입유형(신규/갱신) · 신규는 공통 흐름 + 분기 단계(차량 등)만 고객타입 세로 병렬 → 재합류';
 } else {/* 가입유형 고정 → 회사 비교 */
  var cs=pcase;COMPS.forEach(function(co){var l=buildLine(co,cs);if(!l)return;var me=co==='당사';rows+=(rows?'<div style="height:10px"></div>':'')+sec((me?'🔴 ':'')+esc(co),me?'var(--bad)':'#333','#fff',me?'#f3c7c0':'#e6e6e6',l);});
  hint=esc(caseLabel(cs))+' · 회사별 플로우 비교'+(cs==='신규'?' · 차량 등에서 고객타입 세로 분기':'');
 }
 var html='<div class="caphint" style="margin:0 0 10px">'+hint+'. (썸네일 클릭=확대)</div>';
 if(rows)html+='<div style="display:flex;align-items:stretch;gap:12px"><div style="display:flex;align-items:center;flex:0 0 auto">'+entry+'</div><div style="flex:1;min-width:0">'+rows+'</div></div>';
 else html+='<div class="caphint">'+(liveMode()?'분석된 캡쳐가 없습니다.':'표시할 데이터가 없습니다.')+'</div>';
 host.innerHTML=html;
}
function flowPivotRender(){_variantStore={};_vid=0;branchFlowRender();}
document.getElementById('flowpivot')&&document.getElementById('flowpivot').addEventListener('click',function(e){var nav=e.target.closest('[data-vnav]');if(nav){var vkey=nav.getAttribute('data-vnav'),dd=+nav.getAttribute('data-d'),urls=_variantStore[vkey]||[];if(!urls.length)return;var im=this.querySelector('.vimg[data-vkey="'+vkey+'"]'),pg=this.querySelector('.vpage[data-vkey="'+vkey+'"]');if(!im)return;var idx=(+im.getAttribute('data-vidx')||0);idx=((idx+dd)%urls.length+urls.length)%urls.length;im.setAttribute('data-vidx',idx);if(urls[idx])im.src=urls[idx];if(pg)pg.textContent=(idx+1)+'/'+urls.length;e.stopPropagation();return;}var img=e.target.closest('img[data-lb]');if(!img)return;document.getElementById('lbimg').src=_fullOf[img.src]||img.src;document.getElementById('lightbox').classList.add('on');});
document.getElementById('flowdl')&&document.getElementById('flowdl').addEventListener('click',function(){window.print();});

/* ── 2) 벤치마크: 종합 스코어카드(자동 계산) ── */
function termScoreOf(c){let g=0,m=0,n=0;Object.keys(TERM).forEach(function(t){const x=TERM[t].comp[c];if(!x)return;n++;if(x.r==='good')g++;else if(x.r==='mid')m++;});return n?Math.round((g+0.5*m)/n*100):0;}
function stdRefRender(){var el=document.getElementById('stdref');if(!el||typeof STD_TERMS==='undefined')return;
 el.innerHTML='<div class="caphint" style="margin:0 0 8px"><b>📕 표준약관 용어 참고 ('+STD_TERMS.length+')</b> — 가입화면 용어를 표준 의미·소비자 권장 표현과 대조하세요. <span style="color:var(--muted)">의미 요약본 · 정본/최신 한도는 약관 원문 확인</span></div>'
  +'<table><tr><td class="lbl" style="width:150px">표준 용어</td><td class="lbl">표준 의미 (요약)</td><td class="lbl">소비자 권장 표현</td></tr>'
  +STD_TERMS.map(function(s){return '<tr><td style="font-weight:700;vertical-align:top">'+esc(s.t)+'</td><td style="color:var(--ink-2);vertical-align:top">'+esc(s.d)+'</td><td style="color:var(--good);vertical-align:top;font-weight:600">"'+esc(s.c)+'"</td></tr>';}).join('')
  +'</table>';}
/* 관리자 설정(가중치·필드사전) — 로컬 저장 */
function getWeights(){const s=localStorage.getItem('cap_weights');if(s!=null){try{const w=JSON.parse(s);if(w&&w.input!=null)return w;}catch(e){}}return WEIGHTS;}
function setWeights(w){localStorage.setItem('cap_weights',JSON.stringify(w));}
function getFields(){const s=localStorage.getItem('cap_fields');if(s!=null){try{const f=JSON.parse(s);if(Array.isArray(f))return f;}catch(e){}}return FIELDS;}
function setFields(a){localStorage.setItem('cap_fields',JSON.stringify(a));}
function splitCSVLine(line){const out=[];let cur='',q=false;for(var i=0;i<line.length;i++){const ch=line[i];if(q){if(ch==='"'){if(line[i+1]==='"'){cur+='"';i++;}else q=false;}else cur+=ch;}else{if(ch==='"')q=true;else if(ch===','){out.push(cur);cur='';}else cur+=ch;}}out.push(cur);return out.map(function(x){return x.trim();});}
function computeScores(){const W=getWeights();const inSum={};COMPS.forEach(function(c){var d=DATA["신규"]&&DATA["신규"][c];inSum[c]=d?d.steps.reduce(function(s,x){return s+x[1];},0):0;});const maxI=Math.max.apply(null,COMPS.map(function(c){return inSum[c];})),minI=Math.min.apply(null,COMPS.map(function(c){return inSum[c];}));return COMPS.map(function(c){const sIn=maxI===minI?100:Math.round((maxI-inSum[c])/(maxI-minI)*100);const sTerm=termScoreOf(c);const total=Math.round(sIn*W.input+sTerm*W.term);return {c:c,total:total,sIn:sIn,sTerm:sTerm,inSum:inSum[c]};});}
function scoreRender(){const rows=computeScores().sort(function(a,b){return b.total-a.total;});const myRank=rows.findIndex(function(r){return r.c==='당사';})+1;const my=rows.find(function(r){return r.c==='당사';});let html='<div class="summary'+(myRank>3?'':' info')+'">자사(당사) 종합 <b>'+(my?my.total:0)+'점</b> · '+COMPS.length+'개사 중 <b>'+myRank+'위</b>'+(myRank>3?' — 개선 여지 큼':'')+'</div>';html+=rows.map(function(r,i){const me=r.c==='당사';const subs=[["입력효율",r.sIn],["용어친화",r.sTerm]].map(function(s){var col=s[1]>=70?'var(--good)':(s[1]>=40?'var(--brand)':'var(--bad)');return '<div class="mini"><span class="ml">'+s[0]+'</span><span class="mt"><span class="mf" style="width:'+Math.max(s[1],3)+'%;background:'+col+'"></span></span><span class="mv" style="color:'+col+'">'+s[1]+'</span></div>';}).join('');return '<div class="score-row'+(me?' me':'')+'"><span class="score-rank">'+(i+1)+'</span><span class="score-co">'+r.c+(me?'<br><span style="font-size:10px;color:var(--bad)">자사</span>':'')+'</span><div class="score-bars">'+subs+'</div><span class="score-total">'+r.total+'</span></div>';}).join('');document.getElementById('scorecard').innerHTML=html;}

/* ── 방법론 (관리자 편집): 가중치 + 데이터 사전 + 스코어 로직 ── */
function methodRender(){const W=getWeights();
 document.getElementById('wedit').innerHTML='<div class="form-grid" style="grid-template-columns:repeat(2,1fr)"><label>입력효율 %<input id="w_input" type="number" min="0" value="'+Math.round(W.input*100)+'"></label><label>용어친화 %<input id="w_term" type="number" min="0" value="'+Math.round(W.term*100)+'"></label></div><div style="display:flex;gap:6px;margin-top:10px"><button class="btn" data-act="w_apply" style="width:auto;padding:9px 18px">적용</button><button class="btn" data-act="w_reset" style="width:auto;padding:9px 18px;background:#9aa0ab;box-shadow:none">기본값</button></div>';
 document.getElementById('scoredef').innerHTML='<div class="summary info" style="margin-top:0">종합점수 = '+SCORE_DEF.map(function(s){return s[0]+'×'+Math.round(W[s[1]]*100)+'%';}).join(' + ')+'</div>'+SCORE_DEF.map(function(s){return '<div class="mini" style="margin:9px 0 2px"><span class="ml" style="flex:0 0 70px">'+s[0]+'</span><span class="mt"><span class="mf" style="width:'+(W[s[1]]*100)+'%"></span></span><span class="mv">'+Math.round(W[s[1]]*100)+'%</span></div><div class="caphint" style="margin:0 0 8px 79px">'+s[2]+'</div>';}).join('');
 document.getElementById('scorelogic').innerHTML=computeScores().sort(function(a,b){return b.total-a.total;}).map(function(r){const me=r.c==='당사';return '<div class="stp"><span style="font-weight:600">'+r.c+(me?' (자사)':'')+'<br><span class="caphint" style="margin:0">입력효율 '+r.sIn+'×'+Math.round(W.input*100)+'% + 용어친화'+r.sTerm+'×'+Math.round(W.term*100)+'%</span></span><span class="badge" style="background:var(--brand-50);color:var(--brand-600);font-size:14px">'+r.total+'점</span></div>';}).join('');
 const F=getFields();document.getElementById('fielddict').innerHTML='<table>'+F.map(function(f,i){return '<tr><td style="width:148px;font-weight:700;vertical-align:top;">'+esc(f[0])+'</td><td style="color:var(--ink-2)">'+esc(f[1])+'</td><td style="width:36px;text-align:right;vertical-align:top"><button class="admin-only" data-act="f_del" data-fi="'+i+'" style="border:none;background:none;color:var(--bad);cursor:pointer;font-size:12px;font-weight:700">삭제</button></td></tr>';}).join('')+'</table><div class="admin-only"><div class="form-grid" style="grid-template-columns:1fr 2fr;margin-top:12px"><label>필드명<input id="f_name"></label><label>설명<input id="f_desc"></label></div><div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap"><button class="btn" data-act="f_add" style="width:auto;padding:9px 16px">필드 추가</button><label class="btn" style="width:auto;padding:9px 16px">CSV 가져오기<input type="file" id="f_import" accept=".csv,.txt" style="display:none"></label><button class="btn" data-act="f_export" style="width:auto;padding:9px 16px;background:#9aa0ab;box-shadow:none">CSV 내보내기</button></div></div>';
}
document.getElementById('t4').addEventListener('click',function(e){const act=e.target.dataset.act;if(!act)return;if(act==='w_apply'){const i=+document.getElementById('w_input').value||0,t=+document.getElementById('w_term').value||0,sum=i+t;if(!sum){alert('가중치를 입력하세요.');return;}setWeights({input:i/sum,term:t/sum});methodRender();scoreRender();if(sum!==100)alert('합계 '+sum+'% → 100% 기준으로 정규화해 적용했습니다.');}else if(act==='w_reset'){localStorage.removeItem('cap_weights');methodRender();scoreRender();}else if(act==='f_add'){const n=document.getElementById('f_name').value.trim(),d=document.getElementById('f_desc').value.trim();if(!n){alert('필드명을 입력하세요.');return;}const a=getFields().slice();a.push([n,d]);setFields(a);methodRender();}else if(act==='f_del'){const a=getFields().slice();a.splice(+e.target.dataset.fi,1);setFields(a);methodRender();}else if(act==='f_export'){dlCSV('데이터필드사전.csv',[['필드','설명']].concat(getFields()));}});
document.getElementById('t4').addEventListener('change',function(e){if(e.target.id!=='f_import')return;const file=e.target.files[0];if(!file)return;const rd=new FileReader();rd.onload=function(){const lines=rd.result.replace(/^﻿/,'').split(/\r?\n/).map(function(l){return l.trim();}).filter(Boolean);const a=[];lines.forEach(function(l){const p=splitCSVLine(l);if((p[0]||'')==='필드')return;if(p[0])a.push([p[0],p[1]||'']);});if(a.length){setFields(a);methodRender();alert(a.length+'개 필드를 가져왔습니다.');}else alert('가져올 필드가 없습니다. (CSV 형식: 필드,설명)');};rd.onerror=function(){alert('파일을 읽지 못했습니다. 다시 시도해주세요.');};rd.readAsText(file,'utf-8');e.target.value='';});

/* ── 측정 기록 + AI초안 + 검수 워크플로우 (로컬 저장) ── */
const RECST={draft:["AI 초안","st-ignore"],review:["검수중","st-todo"],confirmed:["확정","st-done"]};
const GRADELBL={good:"양호",mid:"보통",bad:"개선필요","-":"-",undefined:"-"};
function recGet(){try{return JSON.parse(localStorage.getItem('cap_records')||'[]');}catch(e){return [];}}
function recSave(a){localStorage.setItem('cap_records',JSON.stringify(a));}
var SAMPLE_RECORDS=[
 {co:'당사',screen:'담보선택',step:'STEP4',prefill:'부분',auto:'N',grade:'bad',fields:'대인,대물,자손,무보험,자차,특약12개',memo:'특약 과다·용어 미설명',status:'confirmed'},
 {co:'당사',screen:'정보입력',step:'STEP2',prefill:'N',auto:'N',grade:'bad',fields:'주민번호,면허번호,경력 등 9개',memo:'한 화면 입력 과다',status:'confirmed'},
 {co:'S사',screen:'차량확인',step:'STEP1',prefill:'Y',auto:'Y',grade:'good',fields:'차량번호,차명확인',memo:'현기차 자동조회',status:'confirmed'},
 {co:'K사',screen:'본인인증',step:'STEP1',prefill:'-',auto:'N',grade:'mid',fields:'휴대폰인증',memo:'선(先)인증 부담',status:'review'},
 {co:'S사',screen:'산출완료',step:'STEP7',prefill:'-',auto:'-',grade:'good',fields:'-',memo:'업셀링 팝업 노출',status:'draft'}
];
function recSeed(){if(liveMode())return;/* 실데이터 모드: 샘플 기록 시딩하지 않음 */if(!recGet().length){recSave(SAMPLE_RECORDS.map(function(r,i){var o={};for(var k in r)o[k]=r[k];o.id='rs'+i;return o;}));}}
/* 실데이터 모드 여부 (data.js의 LIVE_MODE) */
function liveMode(){return typeof LIVE_MODE!=='undefined'&&LIVE_MODE;}
/* 측정기록(관리자 도구에서 확인·기록한 실제 캡쳐 분석)으로 DATA/STEP을 재구성.
   - 실데이터 모드에서만 동작. 기록이 있으면 샘플 경쟁사 수치를 실데이터로 완전 교체.
   - 기록이 없으면 DATA/STEP을 비워 '캡쳐를 불러오세요' 빈 상태로 표시(샘플 미노출). */
/* 사용자가 매긴 STEP 번호(예: "STEP4") → 정렬 키. 없으면 null */
function stepNo(r){var s=(r&&r.step)||'';var m=/(\d+)/.exec(s);if(m)return parseInt(m[1],10);var sc=(r&&r.screen)||'';var m2=/STEP\s*(\d+)/i.exec(sc);return m2?parseInt(m2[1],10):null;}
/* 익명화 표기 정합: 과거 기록의 'KB' → 'K사' 1회 마이그레이션(저장본 갱신) */
function migrateCo(){try{var a=recGet(),ch=false;a.forEach(function(r){if(r.co==='KB'){r.co='K사';ch=true;}});if(ch)recSave(a);}catch(e){}}
/* 분기 자동 도출 — 기록에 branch 없으면 화면명·가입유형에서 추론(만기도래/미도래/갱신/신규) */
function deriveBranch(r){if(r&&r.branch)return r.branch;var s=((r&&r.screen)||'')+' '+((r&&r.step)||'');if(/만기미도래/.test(s))return '타사만기미도래';if(/만기도래/.test(s))return '타사만기도래';if(/갱신/.test(s)||(r&&r.case==='갱신'))return '갱신';return '신규';}
function applyLiveData(){
 if(!liveMode())return;
 migrateCo();
 Object.keys(DATA).forEach(function(k){delete DATA[k];});
 Object.keys(STEP).forEach(function(k){delete STEP[k];});
 var recs=recGet().filter(function(r){return r.status==='confirmed';});/* 검수 완료(confirmed)는 무조건 표시 — 가입유형 '미정'도 숨기지 않고 '신규'로 기본 분류(아래) */
 /* 회사 목록도 실제 기록 기준으로 재구성 (당사 먼저) — 캡쳐한 회사만 노출 */
 var cos=['당사'];recs.forEach(function(r){if(r.co&&r.co!=='당사'&&cos.indexOf(r.co)<0)cos.push(r.co);});
 COMPS.length=0;Array.prototype.push.apply(COMPS,cos);
 if(COMPS.indexOf(pcomp)<0)pcomp=COMPS[1]||COMPS[0];
 if(!recs.length)return;
 var ord={};STEP_ORDER.forEach(function(n,i){ord[n]=i;});
 var byCS={};
 recs.slice().reverse().forEach(function(r){var cs=(r.case&&r.case!=='미정')?r.case:'신규',co=r.co;if(!co)return;(byCS[cs]=byCS[cs]||{});(byCS[cs][co]=byCS[cs][co]||[]).push(r);});/* 미정=신규로 귀속(검수완료면 무조건 보이게) */
 /* 정렬 순서: 정규단계 숫자 우선 → 파일명 STEP번호 → 표준순서. (표시 이름과 분리) */
 var ordOf=function(r){var c=(r&&r.canon!=null)?(''+r.canon).trim():'';if(/^\d+$/.test(c))return parseInt(c,10);var n=stepNo(r);if(n!=null)return n;var k=ord[r.screen];return k!=null?k:99;};
 Object.keys(byCS).forEach(function(cs){DATA[cs]={};Object.keys(byCS[cs]).forEach(function(co){
  var arr=byCS[cs][co].slice().sort(function(a,b){var na=ordOf(a),nb=ordOf(b);if(na!==nb)return na-nb;var c=(''+(a.screen||'')).localeCompare(''+(b.screen||''),'ko',{numeric:true});if(c!==0)return c;return (a.ts||0)-(b.ts||0);});/* 정규단계 → 파일명 뒷자리(숫자 인식) 오름차순 → ts */
  /* 표시 이름=화면명(고유) — 정규단계 숫자를 이름으로 쓰면 충돌하므로 분리 */
  var steps=arr.map(function(r){var fields=(r.fields||'').split(',').map(function(x){return x.trim();}).filter(Boolean);var name=recDisp(r);STEP[name]=STEP[name]||{};STEP[name][co]={f:fields,r:(r.grade&&r.grade!=='-')?r.grade:'mid'};return [name,fields.length,ordOf(r),deriveBranch(r),(r.btn!=null&&r.btn!==''?r.btn:''),(r.substep||''),(r.upcover||''),(r.fee||'')];});/* [이름(화면명›세부단계),입력수,정규단계,분기,버튼수,세부단계,업셀담보,보험료] */
  DATA[cs][co]={steps:steps};
 });});
 /* 비교 기준 기본값을 실제 데이터 범위로 보정 */
 if(!DATA[pcase]){var ks=Object.keys(DATA);if(ks.length)pcase=ks[0];}
 if(!DATA[curCase2])curCase2=pcase;
 var sn=(typeof stepNamesFor==='function')?stepNamesFor(curCase2):[];
 if(sn.length&&sn.indexOf(curStep)<0)curStep=sn[0];
 /* 플로우 기본 회사: 자사(당사)는 실데이터가 없으므로, 단계가 기록된 회사를 우선 표시 */
 if(typeof fmCo!=='undefined'){var hasSteps=function(c){return Object.keys(DATA).some(function(k){return DATA[k][c]&&DATA[k][c].steps&&DATA[k][c].steps.length;});};if(!hasSteps(fmCo)){var alt=COMPS.filter(hasSteps)[0];if(alt)fmCo=alt;}if(typeof fmCase!=='undefined'&&!DATA[fmCase])fmCase=Object.keys(DATA)[0]||fmCase;}
}
/* 상단 '자동차보험 · N개사' 칩을 실제 회사 수로 갱신 */
function updateScope(){var el=document.getElementById('scopePill');if(el)el.textContent='자동차보험 · '+COMPS.length+'개사';}
/* 모든 데이터 의존 화면을 다시 그림(측정기록 변경/다른 탭 갱신 시)
   ※ 측정기록 입력·검수 UI는 관리자 도구(mask-tool.html)로 일원화 — 대시보드는 확정 기록을 읽어 렌더만 함 */
function renderAllLive(){applyLiveData();updateScope();try{renderFixed();pivotRender();stepCaseChips();stepSummary();stepChips();stepRender();scoreRender();rubricRender();insightsRender();designBriefRender();flowPivotRender();}catch(e){}}

/* ── 지능형 연동: 데이터 기반 자동 진단(개선·A/B·업셀링) ── */
function deriveInsights(){const co="당사",cs="신규";const improve=[],ab=[],upsell=[];const steps=(DATA[cs]&&DATA[cs][co]?DATA[cs][co].steps:[]);
 if(steps[0]&&steps[0][0]==='본인인증'){improve.push(["본인인증이 첫 단계","견적 전 인증 요구 → 견적 전 이탈 위험","본인인증을 견적 이후로 이동"]);ab.push(["본인인증 위치 변경","인증을 견적 후로 옮기면 견적 완료율↑"]);}
 Object.keys(STEP).forEach(function(s){const d=STEP[s][co];if(!d)return;if(d.f.length>=7||d.r==='bad'){improve.push([s+" 입력 과다 ("+d.f.length+"개)","경쟁사 최소 대비 많음 → 이탈 요인","핵심 항목만 + 자동조회·점진 입력"]);ab.push([s+" 입력 축소","핵심 항목만 받으면 단계 완료율↑"]);}});
 const badTerms=Object.keys(TERM).filter(function(t){return TERM[t].comp[co]&&TERM[t].comp[co].r==='bad';});
 if(badTerms.length){improve.push(["전문용어 노출 ("+badTerms.length+"개)","쉬운 설명 없이 용어만 → 이해도↓","권장 표현으로 쉬운 설명 인라인 노출"]);ab.push(["용어 쉬운 설명","쉽게 풀어쓰면 담보선택 이탈↓"]);} try{recGet().filter(function(r){return r.status==='confirmed'&&r.case!=='미정'&&r.grade==='bad'&&r.co===co;}).forEach(function(r){improve.push([(r.screen||'화면')+" (측정기록 확정 반영)","검수 확정된 개선필요 항목",(r.memo||'검수 메모 없음')]);});}catch(e){}
 const hasCover=steps.some(function(st){return st[0].indexOf('담보')>=0;});
 if(hasCover)upsell.push(["담보선택 화면","자기신체사고 → 자동차상해 업그레이드 카드 제안","보장 강화 · 특약 부착률↑","적합성 원칙 준수 · 디폴트 강제 금지(끼워팔기 방지)"]);
 upsell.push(["견적 확인 직후","마이크로 업셀: 긴급출동·운전자보험·자녀할인 특약 추천","객단가↑ · 가입 직전 전환 활용","필요성 기반 추천만 · 쉽게 끄기"]);
 upsell.push(["갱신·만기 케이스","변경점 하이라이트 + 상향 담보/신규 특약 제안","갱신 객단가↑ · 보장 공백 방지","기존 대비 변동 명확 고지"]);
 upsell.push(["자동조회(prefill) 도입 시","입력 시간 절감분만큼 추천 담보 설명 여력 확보","UX 개선 → 업셀 여력으로 연결",""]);
 return {improve:improve,ab:ab,upsell:upsell};}
function insightsRender(){if(!document.getElementById('insImprove'))return;const ins=deriveInsights();
 document.getElementById('insImprove').innerHTML=ins.improve.length?ins.improve.map(function(x){return '<div class="irow" style="align-items:flex-start"><span class="sq" style="background:#e5484d;margin-top:6px"></span><div><b>'+esc(x[0])+'</b><div class="caphint" style="margin:2px 0 0">'+esc(x[1])+' → <span style="color:#16a34a;font-weight:600">'+esc(x[2])+'</span></div></div></div>';}).join(''):'<div class="caphint">개선 포인트 없음</div>';
 var nx=document.getElementById('insNext');if(nx)nx.innerHTML='<div class="stp"><span><b>A/B 추천 '+ins.ab.length+'건</b> · <b>업셀 기회 '+ins.upsell.length+'건</b><br><span class="caphint" style="margin:0">아래 A/B 시나리오·업셀링 섹션에서 상세 확인 (적합성 준수·끼워팔기 금지)</span></span></div>';}

/* ── 루브릭 채점표 + 표준약관5 + 예시 채점(mock-up) ── */
function rubricRender(){if(typeof RUBRIC==='undefined'||!document.getElementById('rubric'))return;
 var tot=RUBRIC.reduce(function(s,r){return s+r.w;},0);
 /* 관리자 도구(mask-tool)에서 확인·기록/수기 채점한 결과를 우선 반영. 없으면 예시(mock-up). */
 var ls={};try{ls=JSON.parse(localStorage.getItem('cap_rubric')||'{}');}catch(e){}
 if(liveMode()&&!Object.keys(ls).length){document.getElementById('rubric').innerHTML='<div class="caphint" style="margin-top:0">아직 채점 데이터가 없습니다. <b>관리자 도구(mask-tool.html) → 측정 기록</b>에서 화면을 확인·기록하면 입력 항목·평가가 점수로 자동 환산되어 이 표가 채워집니다.</div>';if(document.getElementById('std5'))document.getElementById('std5').innerHTML='<table>'+STD5.map(function(s){return '<tr><td style="width:130px;font-weight:700;vertical-align:top">'+esc(s.term)+'</td><td style="color:var(--ink-2)">'+esc(s.def)+'</td></tr>';}).join('')+'</table>';return;}
 var MOCK=liveMode()?{}:{"당사":[18,8,10,0,8],"S사":[30,18,22,9,9]};
 var zero=RUBRIC.map(function(){return 0;});
 function arr(co){var o=ls[co];if(o)return RUBRIC.map(function(r,i){return o[i]!=null?+o[i]:0;});return MOCK[co]||null;}
 var keys=Object.keys(ls);
 var colA=ls['당사']?'당사':(keys[0]||'당사');
 var others=keys.filter(function(c){return c!==colA;});
 var colB=others.length?others[0]:(colA==='당사'?'S사':'당사');
 var A=arr(colA)||MOCK[colA]||zero,B=arr(colB)||MOCK[colB]||zero;
 var live=!!(ls[colA]||ls[colB]);
 var tag=function(co){return ls[co]?(ls[co]._manual?' <span style="color:var(--good);font-size:10px">수기</span>':' <span style="color:var(--brand);font-size:10px">자동</span>'):' <span style="color:var(--muted);font-size:10px">예시</span>';};
 var head='<table><tr><td class="lbl" style="width:120px">평가축</td><td class="lbl" style="width:54px">배점</td><td class="lbl">채점 기준</td><td class="lbl" style="width:84px;text-align:right">'+esc(colA)+tag(colA)+'</td><td class="lbl" style="width:84px;text-align:right">'+esc(colB)+tag(colB)+'</td></tr>';
 var rows=RUBRIC.map(function(r,i){return '<tr><td style="font-weight:700;vertical-align:top">'+esc(r.axis)+'</td><td style="vertical-align:top">'+r.w+'점</td><td style="color:var(--ink-2)">'+esc(r.crit)+'</td><td style="text-align:right;color:var(--bad);font-weight:700">'+(A[i]!=null?A[i]:'–')+'</td><td style="text-align:right;font-weight:700">'+(B[i]!=null?B[i]:'–')+'</td></tr>';}).join('');
 var sum=function(v){return v.reduce(function(s,x){return s+(x||0);},0);};
 var foot='<tr><td style="font-weight:800" colspan="2">합계 / '+tot+'점</td><td></td><td style="text-align:right;font-weight:800;color:var(--bad)">'+sum(A)+'</td><td style="text-align:right;font-weight:800">'+sum(B)+'</td></tr>';
 var hint=live?'관리자 도구(마스킹·데이터 준비)의 확인·기록/채점이 자동 반영됨 — '+esc(colA)+' '+sum(A)+'점 vs '+esc(colB)+' '+sum(B)+'점.':'예시 채점(mock-up): 관리자 도구에서 화면을 확인·기록하면 이 표에 자동 반영됩니다 — '+esc(colA)+' '+sum(A)+'점 vs '+esc(colB)+' '+sum(B)+'점.';
 document.getElementById('rubric').innerHTML='<div class="caphint" style="margin-top:0">'+hint+'</div>'+head+rows+foot+'</table>';
 if(document.getElementById('std5'))document.getElementById('std5').innerHTML='<table>'+STD5.map(function(s){return '<tr><td style="width:130px;font-weight:700;vertical-align:top">'+esc(s.term)+'</td><td style="color:var(--ink-2)">'+esc(s.def)+'</td></tr>';}).join('')+'</table>';}

/* ── 온보딩(#7): 3축 개요 패널 ── */
function onboardShow(){var o=document.getElementById('onboard');if(o)o.classList.add('on');}
function onboardHide(){var o=document.getElementById('onboard');if(o)o.classList.remove('on');try{localStorage.setItem('cap_onboard','1');}catch(e){}}
document.getElementById('onboardX')&&document.getElementById('onboardX').addEventListener('click',onboardHide);
document.getElementById('onboardGo')&&document.getElementById('onboardGo').addEventListener('click',onboardHide);
document.getElementById('helpBtn')&&document.getElementById('helpBtn').addEventListener('click',onboardShow);
document.getElementById('onboard')&&document.getElementById('onboard').addEventListener('click',function(e){if(e.target===this)onboardHide();});

/* ── 초기 렌더 ── */
recSeed();applyLiveData();updateScope();/* 실데이터 모드면 측정기록(mask-tool)으로 DATA/STEP 재구성 후 렌더 */
methodRender();insightsRender();applyAdmin();flowPivotRender();upsellRender();
rubricRender();newsCfgRender();
setPage('t1');
renderFixed();pivotRender();stepCaseChips();stepSummary();stepChips();stepRender();termChips();termRender();stdRefRender();shotsRender();newsKw();newsRender();abRender();designBriefRender();lsRender();scoreRender();
try{if(!localStorage.getItem('cap_onboard'))onboardShow();}catch(e){}
/* 관리자 도구(mask-tool)가 다른 탭에서 측정기록·루브릭을 갱신하면 대시보드도 즉시 반영 */
window.addEventListener('storage',function(e){if(e.key==='cap_rubric')rubricRender();else if(e.key==='cap_records'){renderAllLive();shotsRender();}else if(e.key==='cap_shots_ts')shotsRender();});
/* file:// 로 열면 데이터가 폴더(주소)별로 갈려 '사라진 것처럼' 보임 → 경고 배너 */
if(location.protocol==='file:'){try{var _fb=document.createElement('div');_fb.style.cssText='position:fixed;top:0;left:0;right:0;z-index:99999;background:#e5484d;color:#fff;font:700 13px/1.5 sans-serif;padding:10px 16px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.2)';_fb.innerHTML='⚠️ file:// 로 열렸습니다 — 저장한 기록·캡쳐가 유지되지 않고 폴더마다 따로 저장됩니다. 반드시 <b>실행기(실행-윈도우.bat / 실행-맥.command)</b>로 열어 <b>http://localhost:8000</b> 주소로 사용하세요.';document.body.appendChild(_fb);document.body.style.paddingTop='46px';}catch(e){}}
