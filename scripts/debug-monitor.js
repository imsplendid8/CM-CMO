/**
 * 글로벌 디버깅·모니터링 시스템
 * - 모든 도구에 임베드되어 에러·경고·성능 메트릭을 수집
 * - localStorage의 'mf-debug-log'에 저장
 * - 대시보드에서 조회 가능
 */

class DebugMonitor {
  constructor(toolName = 'unknown') {
    this.toolName = toolName;
    this.logs = [];
    this.startTime = Date.now();
    this.loadStartTime = {};
    this.init();
  }

  init() {
    window.addEventListener('error', (e) => {
      this.error(`[JS Error] ${e.message}`, {
        file: e.filename,
        line: e.lineno,
        col: e.colno,
        stack: e.error?.stack
      });
    });

    window.addEventListener('unhandledrejection', (e) => {
      this.error(`[Promise Rejection] ${e.reason}`, {
        reason: String(e.reason)
      });
    });

    this.wrapFetch();
  }

  wrapFetch() {
    const originalFetch = window.fetch;
    const self = this;

    window.fetch = function(...args) {
      const url = args[0];
      const method = (args[1]?.method || 'GET').toUpperCase();
      self.loadStartTime[url] = Date.now();
      self.debug(`[Fetch Start] ${method} ${url}`);

      return originalFetch.apply(this, args)
        .then(r => {
          const ms = Date.now() - self.loadStartTime[url];
          const context = { url, method, status: r.status, ms, retryable: r.status >= 500 };
          if (r.ok) {
            self.debug(`[Fetch OK] ${method} ${url} (${ms}ms)`, context);
          } else {
            self.warn(`[Fetch ${r.status}] ${method} ${url}`, context);
          }
          return r;
        })
        .catch(err => {
          const ms = Date.now() - self.loadStartTime[url];
          const context = {
            url,
            method,
            error: err.message,
            ms,
            retryable: err.message.includes('timeout') || err.message.includes('network')
          };
          self.error(`[Fetch Error] ${method} ${url}`, context);
          throw err;
        });
    };
  }

  log(msg, meta = {}, level = 'log') {
    const entry = {
      time: new Date().toISOString(),
      tool: this.toolName,
      msg,
      meta,
      level,
      elapsed: Date.now() - this.startTime
    };
    this.logs.push(entry);
    this.save();

    const prefix = `[${this.toolName}] ${level.toUpperCase()}`;
    console[level === 'error' ? 'error' : level === 'warn' ? 'warn' : 'log'](
      prefix, msg, meta
    );
  }

  debug(msg, meta) { this.log(msg, meta, 'debug'); }
  warn(msg, meta) { this.log(msg, meta, 'warn'); }
  error(msg, meta) { this.log(msg, meta, 'error'); }
  info(msg, meta) { this.log(msg, meta, 'info'); }

  startMeasure(label) {
    this.loadStartTime[label] = Date.now();
  }

  endMeasure(label, meta = {}) {
    const ms = Date.now() - (this.loadStartTime[label] || Date.now());
    this.info(`[Perf] ${label}: ${ms}ms`, { ...meta, ms });
  }

  checkRender(selector, label) {
    const el = document.querySelector(selector);
    if (!el) {
      this.error(`[Render Failed] ${label} - selector not found: ${selector}`);
      return false;
    }
    if (!el.textContent?.trim()) {
      this.warn(`[Render Warning] ${label} - empty content`, { selector });
      return false;
    }
    this.debug(`[Render OK] ${label}`);
    return true;
  }

  save() {
    try {
      const limit = 500;
      const toSave = this.logs.slice(-limit);
      localStorage.setItem('mf-debug-log', JSON.stringify(toSave));
    } catch (e) {
      console.warn('DebugMonitor: localStorage write failed', e.message);
    }
  }

  static load() {
    try {
      const data = localStorage.getItem('mf-debug-log');
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.warn('DebugMonitor: localStorage read failed', e.message);
      return [];
    }
  }

  static clear() {
    localStorage.removeItem('mf-debug-log');
  }

  static getStatus() {
    const logs = DebugMonitor.load();
    const toolLogs = {};

    logs.forEach(log => {
      if (!toolLogs[log.tool]) {
        toolLogs[log.tool] = { debug: 0, info: 0, warn: 0, error: 0, lastError: null };
      }
      toolLogs[log.tool][log.level]++;
      if (log.level === 'error' || log.level === 'warn') {
        toolLogs[log.tool].lastError = log;
      }
    });

    return {
      totalLogs: logs.length,
      by: toolLogs,
      recent: logs.slice(-20),
      errors: logs.filter(l => l.level === 'error'),
      warnings: logs.filter(l => l.level === 'warn')
    };
  }
}

if (typeof window !== 'undefined') {
  const toolName = document.querySelector('title')?.textContent || 'unknown';
  window.DEBUG = new DebugMonitor(toolName);
}
