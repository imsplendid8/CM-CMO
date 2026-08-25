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
  "SPEC.image.imageSublinkMax",
  "downloadThumbnailPack",
  "ZIP_STORE.zipStore(files)",
  "manifest.json",
  "crypto.subtle.digest",
  "canvas[data-thumb-index]",
  "텍스트 없는 원본",
  'visual_style:"3d_animation"',
  "text_overlay:false",
];
const errors=[];
for(const token of requiredCode)if(!html.includes(token))errors.push(`이미지 연결 코드 누락: ${token}`);
for(const forbidden of ["generated=agent.candidates", "new FileReader()", "PNG 4장 받기", "ctx.fillText(", "-serp-v2.png"]){
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
console.log(`[OK] SERP 기반 3D 애니메이션 보험종목 이미지 ${unique.length}종 · 무문자 PNG·ZIP·메타데이터·업로드 경합 방지 연결 확인`);
