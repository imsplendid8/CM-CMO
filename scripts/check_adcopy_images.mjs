#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const html=fs.readFileSync(path.join(ROOT,"adcopy-tool.html"),"utf8");
const requiredCode=[
  "SERP 기반 보험종목 이미지 소재",
  "SERP 분석 반영",
  "INSURANCE_VISUALS",
  "monthlyAssetSet",
  "SPEC.image.imageSublinkMax",
  "downloadThumbnailPack",
  "ZIP_STORE.zipStore(files)",
  "manifest.json",
  "crypto.subtle.digest",
  "canvas[data-thumb-index]",
  "텍스트 없음",
  'visual_style:"3d_animation_monthly"',
  "text_overlay:false",
  "직전 월 미사용 원본 우선",
  "신규 제작 필요",
];
const errors=[];
for(const token of requiredCode)if(!html.includes(token))errors.push(`이미지 연결 코드 누락: ${token}`);
for(const forbidden of ["generated=agent.candidates", "new FileReader()", "PNG 4장 받기", "ctx.fillText(", "-serp-v2.png", "custom?.url||concept.asset"]){
  if(html.includes(forbidden))errors.push(`구형 이미지/SERP 코드 잔존: ${forbidden}`);
}

const assetNames=[...html.matchAll(/assets\/insurance\/([a-z0-9-]+\.png)/g)].map(x=>x[1]);
const unique=[...new Set(assetNames)];
if(unique.length<9)errors.push(`보험종목 이미지 수 부족: ${unique.length}/9`);
for(const name of unique){
  const file=path.join(ROOT,"assets","insurance",name);
  if(!fs.existsSync(file)){errors.push(`이미지 파일 누락: ${name}`);continue;}
  const data=fs.readFileSync(file);
  if(data.toString("hex",0,8)!=="89504e470d0a1a0a"){errors.push(`PNG 형식 오류: ${name}`);continue;}
  const width=data.readUInt32BE(16),height=data.readUInt32BE(20);
  if(width!==height||width<214)errors.push(`정사각형 214px 이상 필요: ${name} ${width}x${height}`);
  if(data.length>5*1024*1024)errors.push(`5MB 초과: ${name}`);
}

const plan=JSON.parse(fs.readFileSync(path.join(ROOT,"data","adcopy","serp-candidates.json"),"utf8"));
if(plan.image_refresh_cadence!=="monthly")errors.push("월간 이미지 갱신 주기 누락");
const archiveDir=path.join(ROOT,"data","adcopy","image-plans");
const archives=fs.existsSync(archiveDir)?fs.readdirSync(archiveDir).filter(name=>name.endsWith(".json")).sort().map(name=>JSON.parse(fs.readFileSync(path.join(archiveDir,name),"utf8"))):[];
for(const product of plan.products||[]){
  const rows=product.image_directions||[],sources=rows.map(row=>row.asset),distinct=[...new Set(sources)];
  if(rows.length!==4)errors.push(`${product.product_key}: 이미지 제안 ${rows.length}/4`);
  const seenSources=new Set();
  for(const row of rows){
    if(seenSources.has(row.asset)&&(row.generation_required!==true||row.repeated_reference_in_month!==true)){
      errors.push(`${product.product_key}: 반복 원본을 신규 제작 슬롯으로 분리하지 않음 ${row.asset}`);
    }
    seenSources.add(row.asset);
  }
  if(product.image_plan?.unique_asset_count!==distinct.length)errors.push(`${product.product_key}: image_plan 고유 원본 수 오류`);
  if(new Set(rows.map(row=>row.concept_id)).size!==4)errors.push(`${product.product_key}: 이미지 콘셉트 지문 중복`);
  if(rows.some(row=>row.style_family!=="premium_3d_animation_v4"))errors.push(`${product.product_key}: 3D 애니메이션 스타일 패밀리 불일치`);
  if(product.product_key==="driver"&&distinct.some(source=>!path.basename(source).startsWith("driver-")))errors.push("driver: 운전자보험과 무관한 이미지 원본 포함");
  if(product.product_key==="hrmf"&&distinct.some(source=>!/(home-|calculator-)/.test(path.basename(source))))errors.push("hrmf: 주택화재보험과 무관한 이미지 원본 포함");
  if(product.product_key==="golf"&&distinct.some(source=>!/(golf-|calculator-)/.test(path.basename(source))))errors.push("golf: 골프보험과 무관한 이미지 원본 포함");
  if(product.product_key==="cncr"&&distinct.some(source=>!/(health-|calculator-)/.test(path.basename(source))))errors.push("cncr: 암보험과 무관한 이미지 원본 포함");
  if(product.product_key==="chronic"&&distinct.some(source=>!/(health-|calculator-)/.test(path.basename(source))))errors.push("chronic: 유병자보험과 무관한 이미지 원본 포함");
  const prior=[...archives].reverse().find(archive=>(archive.products||[]).some(row=>row.product_key===product.product_key));
  const priorRow=(prior?.products||[]).find(row=>row.product_key===product.product_key),priorAssets=new Set((priorRow?.image_directions||[]).map(row=>row.asset));
  for(const row of rows)if(priorAssets.has(row.asset)&&row.generation_required!==true)errors.push(`${product.product_key}: 이전 원본을 신규 이미지처럼 재제안 ${row.asset}`);
  for(const source of distinct)if(!fs.existsSync(path.join(ROOT,source)))errors.push(`${product.product_key}: 제안 원본 누락 ${source}`);
}

const zipSource=fs.readFileSync(path.join(ROOT,"shared","zip-store.js"),"utf8");
const zipContext={Blob,TextEncoder,Uint8Array,Uint32Array,DataView,Object};
vm.runInNewContext(zipSource,zipContext);
const zipApi=zipContext.ModooZipStore;
if(!zipApi)errors.push("공유 ZIP 생성기 로드 실패");
else{
  const known=new TextEncoder().encode("123456789");
  if(zipApi.crc32(known)!==0xcbf43926)errors.push("ZIP CRC32 검증 실패");
  const probe=new Uint8Array(await zipApi.zipStore([{name:"테스트.txt",data:known}]).arrayBuffer());
  if(Buffer.from(probe.slice(0,4)).toString("hex")!=="504b0304")errors.push("ZIP local header 오류");
  if(Buffer.from(probe.slice(-22,-18)).toString("hex")!=="504b0506")errors.push("ZIP end header 오류");
}

if(errors.length){console.error(errors.join("\n"));process.exit(1);}
console.log(`[OK] 월간 SERP 기반 3D 애니메이션 보험종목 이미지 ${unique.length}종 · 슬롯 중복 방지·무문자 PNG·ZIP·메타데이터 연결 확인`);
