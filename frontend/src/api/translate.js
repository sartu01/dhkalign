// src/api/translate.js
import { request } from './client';
import { logger } from '../utils/logger';

/**
 * Translate text using backend API
 * @param {string} query - Input text to translate
 * @param {('banglish_to_english'|'english_to_banglish')} direction
 */
export async function translateText(query, direction = 'banglish_to_english') {
  if (!query || typeof query !== 'string') {
    const err = new Error('Invalid query');
    err.code = 'EVALIDATION';
    throw err;
  }

  const data = await request('/translate', {
    method: 'GET',
    params: { q: query, direction },
  });

  logger.info('translateText:success', {
    direction,
    querySample: String(query).slice(0, 40),
  });

  return data;
}

/**
 * Submit user feedback on a translation
 */
export async function submitFeedback(query, direction, suggestedTranslation, isCorrect) {
  if (!query || !suggestedTranslation || typeof isCorrect !== 'boolean') {
    const err = new Error('Invalid feedback payload');
    err.code = 'EVALIDATION';
    throw err;
  }

  const data = await request('/feedback', {
    method: 'POST',
    params: {
      query,
      direction,
      suggested_translation: suggestedTranslation,
      is_correct: isCorrect,
    },
  });

  logger.info('submitFeedback:success', {
    direction,
    isCorrect,
  });

  return data;
}