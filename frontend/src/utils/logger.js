/* eslint-disable no-console */
// src/utils/logger.js

const LEVELS = ["error", "warn", "info", "debug"];

const env =
  (typeof process !== "undefined" && process.env) ? process.env : {};
const isDev = env.NODE_ENV === "development";

// REACT_APP_LOG_LEVEL can be: error|warn|info|debug
const configuredLevel =
  (env.REACT_APP_LOG_LEVEL || (isDev ? "debug" : "warn")).toLowerCase();

const thresholdIndex = LEVELS.indexOf(configuredLevel);
const threshold = thresholdIndex === -1 ? LEVELS.indexOf("warn") : thresholdIndex;

function shouldLog(level) {
  const idx = LEVELS.indexOf(level);
  if (idx === -1) return false;
  // Allow logs at/above the configured threshold in ALL envs (prod included)
  return idx <= threshold;
}

function format(level, args) {
  const ts = new Date().toISOString();
  return [`[${ts}] [${level.toUpperCase()}]`, ...args];
}

export const logger = {
  error: (...args) => shouldLog("error") && console.error(...format("error", args)),
  warn:  (...args) => shouldLog("warn")  && console.warn (...format("warn",  args)),
  info:  (...args) => shouldLog("info")  && console.log  (...format("info",  args)),
  debug: (...args) => shouldLog("debug") && console.debug(...format("debug", args)),
};

// Default export so you can: import logger from './logger'
export default logger;