// Logger mínimo com níveis (substitui console.log espalhado).
const LEVELS = { error: 0, warn: 1, info: 2, debug: 3 };

function createLogger(level = 'info') {
    const threshold = LEVELS[level] ?? LEVELS.info;
    const log = (lvl, method) => (message) => {
        if (LEVELS[lvl] <= threshold) {
            console[method](`${new Date().toISOString()} [${lvl.toUpperCase()}] ${message}`);
        }
    };
    return {
        error: log('error', 'error'),
        warn: log('warn', 'warn'),
        info: log('info', 'log'),
        debug: log('debug', 'log'),
    };
}

module.exports = { createLogger };
