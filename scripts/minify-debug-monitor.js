#!/usr/bin/env node
/**
 * Minify debug-monitor.js for embedding in HTML tools
 * Usage: node scripts/minify-debug-monitor.js
 */

const fs = require('fs');
const path = require('path');

// Read source
const sourcePath = path.join(__dirname, 'debug-monitor.js');
const source = fs.readFileSync(sourcePath, 'utf8');

// Simple minification: remove comments, excess whitespace
const minified = source
  .split('\n')
  .filter(line => !line.trim().startsWith('//') && !line.trim().startsWith('/*'))
  .join('\n')
  .replace(/\/\*[\s\S]*?\*\//g, '')  // Remove block comments
  .replace(/\s+/g, ' ')               // Collapse whitespace
  .replace(/\s*([{}();:,])\s*/g, '$1') // Remove spaces around punctuation
  .trim();

const output = `class DebugMonitor{${minified.split('class DebugMonitor{')[1]}`;

console.log('Minified length:', output.length);
console.log('\n📋 Embed this in tools:\n');
console.log(`<script>${output}window.DEBUG=new DebugMonitor(document.querySelector("title")?.textContent||"tool-name");</script>`);

// Optionally save to file
const outPath = path.join(__dirname, 'debug-monitor.min.js');
fs.writeFileSync(outPath, output);
console.log(`\n✓ Saved to ${outPath}`);
