// src/hooks/useTranslator.js
// Main translation hook with caching and error handling

import { useState, useCallback } from 'react';
import { translateText, submitFeedback } from '../api/translate';
import { cache, generateCacheKey } from '../utils/cache';
import { logger } from '../utils/logger';

export function useTranslator() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [metrics, setMetrics] = useState({
    totalRequests: 0,
    cacheHits: 0,
    errors: 0
  });

  const translate = useCallback(async (input, direction = "banglish_to_english", options = {}) => {
    if (!input || !input.trim()) {
      setError('Please enter text to translate');
      return null;
    }

    const { skipCache = false } = options;
    
    try {
      setLoading(true);
      setError(null);
      
      const query = input.trim();
      const cacheKey = generateCacheKey(query, direction);
      logger.debug('translate:start', { query, direction, skipCache });
      
      // Try cache first
      if (!skipCache) {
        const cachedResult = cache.get(cacheKey);
        if (cachedResult) {
          setResult({
            ...cachedResult,
            fromCache: true,
            timestamp: new Date().toISOString()
          });
          setMetrics(prev => ({
            ...prev,
            cacheHits: prev.cacheHits + 1
          }));
          logger.info('translate:cache_hit', { cacheKey, direction });
          return cachedResult;
        }
      }
      
      // Make API request
      const startTime = performance.now();
      const response = await translateText(query, direction);
      const duration = performance.now() - startTime;
      
      const translationResult = {
        ...response,
        fromCache: false,
        processingTime: Math.round(duration),
        timestamp: new Date().toISOString()
      };
      
      // Cache successful results
      if (response.success && response.confidence > 0.5) {
        cache.set(cacheKey, translationResult);
      }
      
      setResult(translationResult);
      setMetrics(prev => ({
        ...prev,
        totalRequests: prev.totalRequests + 1
      }));
      
      logger.info('translate:success', { direction, method: response?.method, confidence: response?.confidence, durationMs: Math.round(duration), fromCache: false });
      return translationResult;
      
    } catch (err) {
      const errorMessage = err.message || 'Translation failed';
      setError(errorMessage);
      setMetrics(prev => ({
        ...prev,
        totalRequests: prev.totalRequests + 1,
        errors: prev.errors + 1
      }));
      logger.error('translate:error', { message: errorMessage, stack: err?.stack });
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const provideFeedback = useCallback(async (query, direction, suggestedTranslation, isCorrect) => {
    try {
      setError(null);
      const response = await submitFeedback(query, direction, suggestedTranslation, isCorrect);
      logger.info('feedback:submitted', { query, direction, isCorrect });
      // If feedback is negative, remove from cache
      if (!isCorrect) {
        const cacheKey = generateCacheKey(query, direction);
        cache.remove(cacheKey);
        logger.warn('feedback:cache_invalidated', { cacheKey, query, direction });
      }
      return response;
    } catch (err) {
      const errorMessage = err.message || 'Feedback submission failed';
      setError(errorMessage);
      logger.error('feedback:error', { message: errorMessage, stack: err?.stack });
      return null;
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const clearCache = useCallback(() => {
    cache.clear();
    setMetrics(prev => ({
      ...prev,
      cacheHits: 0
    }));
  }, []);

  const getStats = useCallback(() => {
    const cacheStats = cache.getStats();
    const successRate = metrics.totalRequests > 0 
      ? ((metrics.totalRequests - metrics.errors) / metrics.totalRequests * 100).toFixed(1)
      : 0;
    
    return {
      requests: metrics,
      cache: cacheStats,
      successRate: parseFloat(successRate)
    };
  }, [metrics]);

  return {
    // Core functions
    translate,
    provideFeedback,
    
    // State
    loading,
    error,
    result,
    
    // Utilities
    clearError,
    clearCache,
    getStats
  };
}