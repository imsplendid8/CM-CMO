#!/usr/bin/env node
/**
 * AST 기반 도구 임베딩 스크립트
 * sed 패턴 대신 정규식과 안정적인 문자열 조작 사용
 * 모든 HTML 도구에 DebugMonitor 클래스를 임베드
 */

const fs = require('fs');
const path = require('path');

// DebugMonitor 소스 코드 읽기
const debugMonitorPath = path.join(__dirname, 'debug-monitor.js');
const debugMonitorSource = fs.readFileSync(debugMonitorPath, 'utf8');

// 미니파이: 주석 제거, 공백 축약, 구두점 주변 공백 제거
function minify(code) {
  return code
    .replace(/\/\*[\s\S]*?\*\//g, '')           // 블록 주석 제거
    .replace(/\/\/.*$/gm, '')                   // 라인 주석 제거
    .split('\n')
    .filter(line => line.trim())
    .join('\n')
    .replace(/\s+/g, ' ')                       // 공백 축약
    .replace(/\s*([{}();:,<>=&|+\-*/%!?\[\]])\s*/g, '$1') // 구두점 주변 공백 제거
    .trim();
}

const minified = minify(debugMonitorSource);

// 도구 파일 목록
const toolFiles = [
  'seo-audit.html',
  'keyword-tool.html',
  'news-tool.html',
  'serp-tool.html',
  'seasonal-tool.html',
  'adcopy-tool.html',
  'powercontent-tool.html'
];

let successCount = 0;
let failCount = 0;

toolFiles.forEach(file => {
  const filePath = path.join(__dirname, '..', file);

  if (!fs.existsSync(filePath)) {
    console.warn(`⚠️ ${file}: 파일 없음`);
    failCount++;
    return;
  }

  try {
    let content = fs.readFileSync(filePath, 'utf8');

    // 이미 임베드됨 확인
    if (content.includes('class DebugMonitor')) {
      console.log(`✓ ${file}: 이미 임베드됨`);
      return;
    }

    // <head> 닫기 태그 찾기
    const headCloseMatch = content.match(/<\/head>/i);
    if (!headCloseMatch) {
      console.warn(`⚠️ ${file}: </head> 태그 없음`);
      failCount++;
      return;
    }

    // </head> 직전에 DebugMonitor 스크립트 삽입
    const insertPoint = headCloseMatch.index;
    const debugScript = `<script>${minified}if(typeof window!=='undefined'){const toolName=document.querySelector('title')?.textContent||'unknown';window.DEBUG=new DebugMonitor(toolName);}</script>\n`;

    content = content.slice(0, insertPoint) + debugScript + content.slice(insertPoint);

    fs.writeFileSync(filePath, content, 'utf8');
    console.log(`✓ ${file}: 임베드 완료 (${debugScript.length} bytes)`);
    successCount++;
  } catch (err) {
    console.error(`✗ ${file}: ${err.message}`);
    failCount++;
  }
});

console.log(`\n📊 결과: ${successCount}개 도구 임베드, ${failCount}개 실패`);
process.exit(failCount > 0 ? 1 : 0);
