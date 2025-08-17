// src/utils/cache.js
// Simple localStorage cache with TTL

import logger from './logger';

const CACHE_PREFIX = 'wraith_';
const DEFAULT_TTL = 5 * 60 * 1000; // 5 minutes

// Simple cache implementation
export const cache = {
  set(key, value, ttl = DEFAULT_TTL) {
    try {
      const item = {
        value,
        expires: Date.now() + ttl,
        timestamp: Date.now()
      };
      localStorage.setItem(CACHE_PREFIX + key, JSON.stringify(item));
      logger.debug('cache:set', { key: CACHE_PREFIX + key, ttl, expiresAt: item.expires });
    } catch (error) {
      logger.warn('cache:write_failed', { key: CACHE_PREFIX + key, error: String(error) });
    }
  },

  get(key) {
    try {
      const item = localStorage.getItem(CACHE_PREFIX + key);
      if (!item) return null;

      const { value, expires } = JSON.parse(item);
      
      if (Date.now() > expires) {
        localStorage.removeItem(CACHE_PREFIX + key);
        logger.debug('cache:get_expired', { key: CACHE_PREFIX + key });
        return null;
      }
      
      logger.debug('cache:get_hit', { key: CACHE_PREFIX + key });
      return value;
    } catch (error) {
      logger.warn('cache:read_failed', { key: CACHE_PREFIX + key, error: String(error) });
      return null;
    }
  },

  remove(key) {
    try {
      localStorage.removeItem(CACHE_PREFIX + key);
      logger.debug('cache:remove', { key: CACHE_PREFIX + key });
    } catch (error) {
      logger.warn('cache:remove_failed', { key: CACHE_PREFIX + key, error: String(error) });
    }
  },

  clear() {
    try {
      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        if (key.startsWith(CACHE_PREFIX)) {
          localStorage.removeItem(key);
        }
      });
      logger.info('cache:clear_namespace', { prefix: CACHE_PREFIX });
    } catch (error) {
      logger.warn('cache:clear_failed', { error: String(error) });
    }
  },

  getStats() {
    try {
      const keys = Object.keys(localStorage);
      const cacheKeys = keys.filter(key => key.startsWith(CACHE_PREFIX));
      
      let validEntries = 0;
      let expiredEntries = 0;
      
      cacheKeys.forEach(key => {
        try {
          const item = JSON.parse(localStorage.getItem(key));
          if (Date.now() > item.expires) {
            expiredEntries++;
          } else {
            validEntries++;
          }
        } catch {
          expiredEntries++;
        }
      });
      logger.debug('cache:stats', { total: cacheKeys.length, validEntries, expiredEntries });
      return {
        totalEntries: cacheKeys.length,
        validEntries,
        expiredEntries
      };
    } catch (error) {
      return { totalEntries: 0, validEntries: 0, expiredEntries: 0 };
    }
  }
};

// Generate cache key for translation
export function generateCacheKey(query, direction) {
  return `translate_${direction}_${query.toLowerCase().trim()}`;
}

// Cleanup expired entries
export function cleanupCache() {
  try {
    const keys = Object.keys(localStorage);
    const cacheKeys = keys.filter(key => key.startsWith(CACHE_PREFIX));
    
    cacheKeys.forEach(key => {
      try {
        const item = JSON.parse(localStorage.getItem(key));
        if (Date.now() > item.expires) {
          localStorage.removeItem(key);
        }
      } catch {
        localStorage.removeItem(key);
      }
    });
    logger.info('cache:cleanup_completed', {});
  } catch (error) {
    logger.warn('cache:cleanup_failed', { error: String(error) });
  }
}