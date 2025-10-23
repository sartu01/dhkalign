export const __DEV__ = Boolean(import.meta?.env?.DEV ?? false);

// Logs only in development mode to avoid noisy console output in production.
export const log = (...args) => {
  if (__DEV__) {
    // eslint-disable-next-line no-console -- dev-only logging helper uses console directly
    console.log(...args);
  }
};
