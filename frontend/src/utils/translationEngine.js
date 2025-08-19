// Translation Engine for DHK Align - Iron Clad Version
import React from 'react';

// Configuration
const DEFAULT_CONFIG = {
  maxCacheSize: 50,
  maxInputLength: 200,
  fuzzyThreshold: 0.8,
  contextualConfidence: 0.85,
  patternConfidenceMultiplier: 0.95,
  patternFallbackConfidence: 0.8,
  enableCache: true,
  enablePersistence: false // Set to true when ready for persistent cache
};

// Safe import with fallback
let clientData;
try {
  clientData = require('./dhk_align_data_client.json');
} catch (error) {
  console.warn('Translation data not found, using fallback');
  clientData = {
    v: '1.0',
    t: {
      'kemon acho': 'how are you',
      'ami tomake bhalo bashi': 'I love you',
      'ki koro': 'what are you doing',
      'dhonnobad': 'thank you',
      'ki khaba': 'what will you eat',
      'kothay jachcho': 'where are you going',
      'bhalo achi': 'I am fine',
      'amar nam': 'my name is',
      'tomar nam ki': 'what is your name',
      'choto mach': 'small fish',
      'boro bari': 'big house'
    }
  };
}

// ===== WRAITH: public pack loader (JSONL) =====
const PUBLIC_PACK_PATH = '/data/expansion';
// keep names short
const DEFAULT_PACKS = ['greet', 'vend', 'slang', 'trans', 'food'];

// Parse a .jsonl string into an array of objects
function parseJSONL(text) {
  return (text || '')
    .split('\n')
    .map(l => l.trim())
    .filter(l => l && !l.startsWith('//'))
    .map(l => {
      try { return JSON.parse(l); } catch { return null; }
    })
    .filter(Boolean);
}

// Convert JSONL entries into a simple phrase map { banglish: english }
function entriesToMap(entries) {
  const out = {};
  for (const row of entries) {
    const key = (row.banglish || row.source || '').toLowerCase().trim();
    const val = (row.english || row.translation || '').toLowerCase().trim();
    if (key && val) out[key] = val;
    // also index variants if present
    if (Array.isArray(row.variants)) {
      row.variants.forEach(v => {
        const vk = String(v || '').toLowerCase().trim();
        if (vk && val) out[vk] = val;
      });
    }
  }
  return out;
}

// --- Helpers to support both .jsonl and .json pack formats ---
async function fetchTextIfExists(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  }
}

// Accepts JSON that can be: array of entries, {phrases:[...]}, or a {banglish: english} map
function parseJSONFlexible(text) {
  try {
    const data = JSON.parse(text);
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.phrases)) return data.phrases;
    if (data && typeof data === 'object') {
      // Convert { banglish: english } map into entry array
      const maybeMap = Object.entries(data)
        .filter(([k, v]) => typeof k === 'string' && (typeof v === 'string' || (v && typeof v.english === 'string')));
      if (maybeMap.length > 0) {
        return maybeMap.map(([banglish, value]) => {
          if (typeof value === 'string') return { banglish, english: value };
          return { banglish, english: value.english, variants: value.variants || [] };
        });
      }
    }
  } catch (e) {
    // ignore
  }
  return null;
}

// Load a pack by base name, trying .jsonl first, then .json
async function loadPackByBaseName(base) {
  // Prefer line-delimited JSONL (stream/append-friendly)
  const jsonlText = await fetchTextIfExists(`${PUBLIC_PACK_PATH}/${base}.jsonl`);
  if (jsonlText) {
    const entries = parseJSONL(jsonlText);
    return entriesToMap(entries);
  }
  // Fallback to classic JSON
  const jsonText = await fetchTextIfExists(`${PUBLIC_PACK_PATH}/${base}.json`);
  if (jsonText) {
    const entries = parseJSONFlexible(jsonText) || [];
    return entriesToMap(entries);
  }
  return {};
}

// Simple LRU Cache (can be swapped with PersistentLRUCache later)
class SimpleLRUCache {
  constructor(maxSize = 50) {
    this.maxSize = maxSize;
    this.cache = new Map();
  }

  get(key) {
    if (!this.cache.has(key)) return null;
    
    // Move to end (most recently used)
    const value = this.cache.get(key);
    this.cache.delete(key);
    this.cache.set(key, value);
    return value;
  }

  set(key, value) {
    // Remove oldest if at capacity
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    
    // Add/update
    this.cache.delete(key);
    this.cache.set(key, value);
  }

  clear() {
    this.cache.clear();
  }

  get size() {
    return this.cache.size;
  }
}

class TranslationEngine {
  constructor(data = clientData, config = {}) {
    // Merge config with defaults
    this.config = { ...DEFAULT_CONFIG, ...config };
    
    // Validate data
    if (!data || typeof data !== 'object') {
      throw new Error('Invalid translation data');
    }
    
    // Normalize data structure
    this.translations = data.t || data.exact || {};
    this.words = data.words || {};
    this.version = data.v || data.version || '1.0';
    
    // Only create cache and indices if we have data
    if (Object.keys(this.translations).length > 0) {
      // Use SimpleLRUCache for now, can swap with PersistentLRUCache later
      this.cache = this.config.enableCache 
        ? new SimpleLRUCache(this.config.maxCacheSize)
        : null;
      this.wordIndex = this.buildWordIndex();
      this.patternMatchers = this.buildPatternMatchers();
      this.ngramIndex = this.buildNgramIndex();
      this.wordWeights = this.calculateWordWeights();
      this.adaptiveCache = new Map();
      this.feedbackData = this.loadFeedbackData();
      this.slangMap = this.buildSlangMap();
    } else {
      console.warn('No translations loaded');
      this.cache = null;
      this.wordIndex = new Map();
      this.patternMatchers = [];
      // Initialize new fields for no-data scenario
      this.ngramIndex = new Map();
      this.wordWeights = new Map();
      this.adaptiveCache = new Map();
      this.feedbackData = this.loadFeedbackData();
      this.slangMap = this.buildSlangMap();
    }
    // Track async pack loading status
    this._packsLoaded = false;
  }

  /**
   * Merge new phrase map into engine and rebuild indices
   */
  _mergeTranslations(map) {
    if (!map) return;
    this.translations = { ...(this.translations || {}), ...map };
    this._rebuildIndices();
  }

  /**
   * Rebuild all derived indices after data changes
   */
  _rebuildIndices() {
    // Recreate or refresh indices based on current translations
    this.wordIndex = this.buildWordIndex();
    this.patternMatchers = this.buildPatternMatchers();
    this.ngramIndex = this.buildNgramIndex();
    this.wordWeights = this.calculateWordWeights();
  }

  /**
   * Load packs from frontend/public/data/expansion at runtime.
   * Safe to call multiple times; subsequent calls are no-ops.
   */
  async ensurePacksLoaded(packNames = DEFAULT_PACKS) {
    if (this._packsLoaded) return;
    try {
      const loaded = {};
      for (const name of packNames) {
        const map = await loadPackByBaseName(name);
        Object.assign(loaded, map);
      }
      if (Object.keys(loaded).length) {
        this._mergeTranslations(loaded);
      }
      this._packsLoaded = true;
    } catch (e) {
      console.warn('Pack load failed:', e?.message || e);
      this._packsLoaded = true; // avoid retry loop during session
    }
  }

  /**
   * Main translation method
   */
  translate(input, options = {}) {
    // Input validation
    if (!input || typeof input !== 'string') {
      return null;
    }
    
    const trimmed = input.trim();
    if (!trimmed || trimmed.length > this.config.maxInputLength) {
      return null;
    }
    
    try {
      const { fuzzy = true } = options;
      const normalized = this.normalizeInput(trimmed);
      // Adaptive learning cache first
      const adaptive = this.adaptiveCache && this.adaptiveCache.get(normalized);
      if (adaptive && adaptive.confidence > 0.8) {
        return adaptive;
      }

      const cacheKey = normalized; // Simple cache key
      
      // Check cache
      if (this.cache && this.cache.get(cacheKey)) {
        return this.cache.get(cacheKey);
      }
      
      // Try translation methods in priority order
      const methods = [
        () => this.exactMatch(normalized),
        () => this.slangMatch(normalized),
        () => (fuzzy ? this.fuzzyMatch(normalized) : null),
        () => this.handleCompoundWords(normalized),
        () => this.patternMatch(normalized),
        () => this.ngramMatch(normalized),
        () => this.contextualMatch(normalized),
        () => this.wordByWordTranslation(normalized)
      ];
      
      let result = null;
      for (const method of methods) {
        result = method && method();
        if (result) break;
      }
      
      // Cache successful translations
      if (result && this.cache) {
        this.cache.set(cacheKey, result);
      }
      
      return result;
      
    } catch (error) {
      console.error('Translation error:', error);
      return null;
    }
  }

  /**
   * Normalize input text
   */
  normalizeInput(text) {
    return text
      .toLowerCase()
      .trim()
      .replace(/\s+/g, ' ')
      .replace(/[।॥]/g, '.') // Bengali punctuation
      .replace(/\?+/g, '?')
      .replace(/!+/g, '!')
      .replace(/^\W+|\W+$/g, ''); // Trim leading/trailing punctuation
  }

  /**
   * Exact match lookup
   */
  exactMatch(input) {
    if (this.translations && this.translations[input]) {
      return {
        translation: this.translations[input],
        confidence: 1.0,
        method: 'exact'
      };
    }
    return null;
  }

  /**
   * Fuzzy matching for typos and variations (phonetic-aware)
   */
  fuzzyMatch(input) {
    if (!this.translations || Object.keys(this.translations).length === 0 || input.length > 50) {
      return null;
    }
    const phoneticInput = this.phoneticNormalize(input);
    const candidates = [];
    const entries = Object.entries(this.translations);

    for (const [key, value] of entries) {
      if (Math.abs(key.length - input.length) > 3) continue;

      const sim1 = this.calculateSimilarity(input, key);
      const sim2 = this.calculateSimilarity(phoneticInput, this.phoneticNormalize(key));
      const similarity = Math.max(sim1, sim2);

      if (similarity > this.config.fuzzyThreshold) {
        candidates.push({ key, similarity, translation: value });
      }
    }

    if (candidates.length > 0) {
      candidates.sort((a, b) => b.similarity - a.similarity);
      return {
        translation: candidates[0].translation,
        confidence: Math.min(candidates[0].similarity * 0.9, 0.95),
        method: 'fuzzy',
        original: candidates[0].key
      };
    }
    return null;
  }

  /**
   * Pattern matching for common grammatical structures
   */
  patternMatch(input) {
    for (const matcher of this.patternMatchers) {
      const match = input.match(matcher.pattern);
      if (match) {
        try {
          let contextBoost = 0;
          if (matcher.contextWords) {
            const hasContext = matcher.contextWords.some(w => input.toLowerCase().includes(w));
            if (hasContext) contextBoost = matcher.boost || 0.1;
          }
          const base = match[1] || '';
          const baseResult = base ? this.wordByWordTranslation(base) : null;
          const baseTranslation = baseResult ? baseResult.translation : base;

          const translation = matcher.transform(match, baseTranslation);

          let confidence = baseResult
            ? Math.min(baseResult.confidence * this.config.patternConfidenceMultiplier, 0.95)
            : this.config.patternFallbackConfidence;

          confidence = Math.min(confidence + contextBoost, 0.98);

          return {
            translation,
            confidence,
            method: 'pattern',
            pattern: matcher.name,
            hasContext: contextBoost > 0
          };
        } catch (e) {
          continue;
        }
      }
    }
    return null;
  }

  /**
   * Contextual matching using word index
   */
  contextualMatch(input) {
    if (!this.wordIndex || this.wordIndex.size === 0) {
      return null;
    }
    
    const words = input.split(' ');
    if (words.length === 0) return null;
    
    const candidates = [];
    
    // Find all phrases containing any of the input words
    for (const word of words) {
      const entries = this.wordIndex.get(word) || [];
      
      for (const { input: phrase, output } of entries) {
        // Check if the input contains this phrase
        if (input.includes(phrase) && phrase !== input) { // Avoid exact matches
          const overlapRatio = phrase.split(' ').length / words.length;
          
          candidates.push({
            phrase,
            output,
            confidence: this.config.contextualConfidence * overlapRatio
          });
        }
      }
    }
    
    // Sort by confidence and return best match
    if (candidates.length > 0) {
      candidates.sort((a, b) => b.confidence - a.confidence);
      
      return {
        translation: candidates[0].output,
        confidence: candidates[0].confidence,
        method: 'contextual',
        matchedPhrase: candidates[0].phrase
      };
    }
    
    return null;
  }

  /**
   * Calculate string similarity (Levenshtein distance based)
   */
  calculateSimilarity(str1, str2) {
    const len1 = str1.length;
    const len2 = str2.length;
    
    // Quick checks
    if (str1 === str2) return 1;
    if (len1 === 0 || len2 === 0) return 0;
    if (Math.abs(len1 - len2) > Math.max(len1, len2) * 0.3) return 0;
    
    // Calculate edit distance
    const matrix = Array(len2 + 1).fill(null).map(() => Array(len1 + 1).fill(null));
    
    for (let i = 0; i <= len1; i++) matrix[0][i] = i;
    for (let j = 0; j <= len2; j++) matrix[j][0] = j;
    
    for (let j = 1; j <= len2; j++) {
      for (let i = 1; i <= len1; i++) {
        const cost = str1[i - 1] === str2[j - 1] ? 0 : 1;
        matrix[j][i] = Math.min(
          matrix[j][i - 1] + 1,      // deletion
          matrix[j - 1][i] + 1,      // insertion
          matrix[j - 1][i - 1] + cost // substitution
        );
      }
    }
    
    const distance = matrix[len2][len1];
    const maxLen = Math.max(len1, len2);
    
    return 1 - (distance / maxLen);
  }

  /**
   * Phonetic normalization for slang/variant handling
   */
  phoneticNormalize(text) {
    const phoneticMap = {
      'ph': 'f', 'gh': 'g', 'kh': 'k', 'th': 't', 'dh': 'd',
      'aa': 'a', 'ee': 'i', 'oo': 'u', 'ou': 'o',
      'z': 'j', 'sh': 's', 'ch': 's',
      // Common slang variations
      'luv': 'love', 'gud': 'good', 'frnd': 'friend',
      'plz': 'please', 'thnx': 'thanks', 'ur': 'your',
      '2': 'to', '4': 'for', 'u': 'you', 'r': 'are'
    };
    let normalized = (text || '').toLowerCase();
    Object.entries(phoneticMap).forEach(([from, to]) => {
      normalized = normalized.replace(new RegExp(from, 'g'), to);
    });
    return normalized;
  }

  /**
   * Load feedback data (stub; can be wired to localStorage or API later)
   */
  loadFeedbackData() {
    return new Map();
  }

  recordFeedback(input, output, isCorrect) {
    const key = this.normalizeInput(input || '');
    const feedback = this.feedbackData.get(key) || { correct: 0, incorrect: 0 };
    if (isCorrect) feedback.correct++; else feedback.incorrect++;
    this.feedbackData.set(key, feedback);

    const total = feedback.correct + feedback.incorrect;
    if (total > 5) {
      const accuracy = feedback.correct / total;
      this.adaptiveCache.set(key, {
        translation: output,
        confidence: accuracy,
        method: 'adaptive'
      });
    }
  }

  /**
   * Build slang/colloquial map
   */
  buildSlangMap() {
    return {
      'ki obostha': "what's up",
      'ki khobor': "what's new",
      'fatafati': 'awesome',
      'jhakas': 'cool',
      'bokachoda': '[censored]',
      'dhur': 'oh come on',
      'ufff': 'ugh',
      'areh': 'hey',
      'accha': 'okay',
      'thik ache': 'alright',
      'chole ashchi': 'coming',
      'ghum': 'sleep',
      'kharap': 'bad',
      'bhalo na': 'not good',
      'pera': 'problem',
      'jhamelar': 'troublesome',
      'mama': 'dude',
      'dada': 'sir',
      'apu': 'sister',
      'vai': 'brother'
    };
  }

  /**
   * Slang matching (direct and partial)
   */
  slangMatch(input) {
    if (this.slangMap[input]) {
      return { translation: this.slangMap[input], confidence: 0.95, method: 'slang' };
    }
    for (const [slang, trans] of Object.entries(this.slangMap)) {
      if (input.includes(slang)) {
        const replaced = input.replace(slang, trans);
        return { translation: replaced, confidence: 0.85, method: 'slang_partial', matchedSlang: slang };
      }
    }
    return null;
  }

  /**
   * Handle common Banglish compound words by simple replacements
   */
  handleCompoundWords(input) {
    const compounds = {
      'ekhon': ['now'],
      'taratari': ['quickly', 'fast'],
      'dhiredhire': ['slowly'],
      'ektukhani': ['a little bit'],
      'onekokhon': ['for a long time'],
      'shobshomoy': ['always'],
      'kokhonoi': ['never'],
      'jekono': ['any'],
      'shobai': ['everyone'],
      'kichui': ['nothing', 'anything']
    };

    let modified = input;
    let found = false;

    Object.entries(compounds).forEach(([c, repl]) => {
      if (modified.includes(c)) {
        modified = modified.replace(c, repl[0]);
        found = true;
      }
    });

    if (found) {
      const result = this.translate(modified, { fuzzy: false });
      if (result) {
        return { ...result, method: 'compound', originalInput: input };
      }
    }
    return null;
  }

  /**
   * Compute TF-IDF-like weights for words
   */
  calculateWordWeights() {
    const weights = new Map();
    const df = new Map();
    const keys = Object.keys(this.translations || {});
    keys.forEach(phrase => {
      const uniq = new Set((phrase || '').split(' ').filter(Boolean));
      uniq.forEach(w => df.set(w, (df.get(w) || 0) + 1));
    });
    const total = Math.max(keys.length, 1);
    df.forEach((freq, w) => {
      const idf = Math.log(total / freq);
      weights.set(w, isFinite(idf) ? Math.max(idf, 0.1) : 0.1);
    });
    return weights;
  }

  /**
   * Weighted word-by-word fallback
   */
  wordByWordTranslation(input) {
    const words = (input || '').split(' ').filter(Boolean);
    if (words.length === 0) return null;

    const translated = [];
    let totalWeight = 0;
    let translatedWeight = 0;

    for (const w of words) {
      const weight = (this.wordWeights && this.wordWeights.get(w)) || 1;
      totalWeight += weight;

      const trans = (this.words && this.words[w]) || this.translations[w];
      if (trans) {
        translated.push(trans);
        translatedWeight += weight;
      } else {
        translated.push(w);
      }
    }

    if (translatedWeight > 0) {
      return {
        translation: translated.join(' '),
        confidence: translatedWeight / totalWeight,
        method: 'weighted_word_by_word',
        importance: translatedWeight
      };
    }
    return null;
  }

  /**
   * Build word index for contextual lookups
   */
  buildWordIndex() {
    const index = new Map();
    
    if (!this.translations) return index;
    
    const entries = Object.entries(this.translations);
    
    for (const [input, output] of entries) {
      const words = input.split(' ');
      
      // Index each word in the phrase
      for (const word of words) {
        if (!index.has(word)) {
          index.set(word, []);
        }
        
        // Store the full phrase and its translation
        index.get(word).push({ 
          input, 
          output,
          wordCount: words.length
        });
      }
    }
    
    // Sort entries by phrase length (longer phrases first)
    for (const [word, entries] of index.entries()) {
      entries.sort((a, b) => b.wordCount - a.wordCount);
    }
    
    return index;
  }

  /**
   * Character-level n-gram index for partial matching
   */
  buildNgramIndex(n = 3) {
    const index = new Map();
    Object.entries(this.translations).forEach(([input, output]) => {
      const text = (input || '').toLowerCase();
      if (text.length < n) return;
      for (let i = 0; i <= text.length - n; i++) {
        const ngram = text.slice(i, i + n);
        if (!index.has(ngram)) index.set(ngram, []);
        index.get(ngram).push({ input, output, position: i });
      }
    });
    return index;
  }
  
  /**
   * N-gram based partial matcher
   */
  ngramMatch(input) {
    const text = (input || '').toLowerCase();
    if (!this.ngramIndex || text.length < 3) return null;
  
    const candidates = new Map();
    const n = 3;
  
    for (let i = 0; i <= text.length - n; i++) {
      const ngram = text.slice(i, i + n);
      const matches = this.ngramIndex.get(ngram) || [];
      matches.forEach(({ input: phrase }) => {
        candidates.set(phrase, (candidates.get(phrase) || 0) + 1);
      });
    }
  
    let bestMatch = null;
    let bestScore = 0;
  
    for (const [phrase, score] of candidates.entries()) {
      const norm = score / Math.max(phrase.length, text.length);
      if (norm > 0.4 && norm > bestScore) {
        bestScore = norm;
        bestMatch = { phrase, output: this.translations[phrase] };
      }
    }
  
    if (bestMatch) {
      return {
        translation: bestMatch.output,
        confidence: Math.min(bestScore * 0.8, 0.75),
        method: 'ngram',
        matchedPhrase: bestMatch.phrase
      };
    }
    return null;
  }

  /**
   * Build pattern matchers for common structures
   */
  buildPatternMatchers() {
    return [
      {
        name: 'question_ki',
        pattern: /^(.+)\s*ki\s*\?*$/i,
        transform: (match, base) => `what ${base}?`,
        contextWords: ['bolte', 'chaichho', 'korchho'],
        boost: 0.1
      },
      { name: 'question_keno', pattern: /^(.+)\s+keno\s*\?*$/i, transform: (m, b) => `why ${b}?` },
      { name: 'question_kothay', pattern: /^(.+)\s+kothay\s*\?*$/i, transform: (m, b) => `where ${b}?` },
      { name: 'question_kokhon', pattern: /^(.+)\s+kokhon\s*\?*$/i, transform: (m, b) => `when ${b}?` },
      { name: 'amar_ache', pattern: /^amar\s+(.+)\s+ache$/i, transform: (m, b) => `I have ${b}` },
      { name: 'ami_korbo', pattern: /^ami\s+(.+)\s+korbo$/i, transform: (m, b) => `I will ${b}` },
      { name: 'tumi_korbe', pattern: /^tumi\s+(.+)\s+korbe$/i, transform: (m, b) => `you will ${b}` },
      {
        name: 'conditional_jodi',
        pattern: /^jodi\s+(.+)\s+tahole\s+(.+)$/i,
        transform: (match) => `if ${match[1]} then ${match[2]}`,
        contextWords: ['hoy', 'thake'],
        boost: 0.15
      },
      {
        name: 'continuous_korchhi',
        pattern: /^(.+)\s+korchhi$/i,
        transform: (m, b) => `${b} doing`,
        contextWords: ['ekhon', 'akhon'],
        boost: 0.1
      },
      {
        name: 'past_korechhi',
        pattern: /^(.+)\s+korechhi$/i,
        transform: (m, b) => `have ${b}`,
        contextWords: ['age', 'goto'],
        boost: 0.1
      }
    ];
  }

  /**
   * Get translation statistics
   */
  getStats() {
    const entries = this.translations ? Object.keys(this.translations).length : 0;
    const indexedWords = this.wordIndex ? this.wordIndex.size : 0;
    
    return {
      totalEntries: entries,
      cacheSize: this.cache ? this.cache.size : 0,
      cacheEnabled: this.config.enableCache,
      wordIndexSize: indexedWords,
      uniqueWords: indexedWords,
      patterns: this.patternMatchers.length,
      version: this.version,
      config: {
        maxInputLength: this.config.maxInputLength,
        fuzzyThreshold: this.config.fuzzyThreshold,
        contextualConfidence: this.config.contextualConfidence
      }
    };
  }

  /**
   * Clear cache
   */
  clearCache() {
    if (this.cache) {
      this.cache.clear();
    }
  }

  /**
   * Update configuration
   */
  updateConfig(newConfig) {
    this.config = { ...this.config, ...newConfig };
    
    // Recreate cache if size changed
    if (newConfig.maxCacheSize && this.cache) {
      const oldCache = this.cache;
      this.cache = new SimpleLRUCache(newConfig.maxCacheSize);
      
      // Transfer entries up to new limit
      let count = 0;
      for (const [key, value] of oldCache.cache.entries()) {
        if (count >= newConfig.maxCacheSize) break;
        this.cache.set(key, value);
        count++;
      }
    }
  }

  /**
   * Batch translate multiple inputs
   */
  batchTranslate(inputs, options = {}) {
    if (!Array.isArray(inputs)) {
      return [];
    }
    
    return inputs.map(input => ({
      input,
      result: this.translate(input, options)
    }));
  }

  /**
   * Get suggestions for partial input
   */
  getSuggestions(partial, limit = 5) {
    if (!partial || typeof partial !== 'string') {
      return [];
    }
    
    const normalized = this.normalizeInput(partial);
    if (!normalized) return [];
    
    const suggestions = [];
    const entries = this.translations ? Object.entries(this.translations) : [];
    
    for (const [key, value] of entries) {
      if (key.startsWith(normalized)) {
        suggestions.push({
          input: key,
          translation: value
        });
        
        if (suggestions.length >= limit) break;
      }
    }
    
    return suggestions;
  }
}

// Singleton instance
let engineInstance = null;

export function useTranslation(config = {}) {
  const engine = React.useMemo(() => {
    if (!engineInstance) {
      engineInstance = new TranslationEngine(clientData, config);
    } else if (Object.keys(config).length > 0) {
      // Update config if provided
      engineInstance.updateConfig(config);
    }
    // Fire-and-forget: load public packs into the engine
    engineInstance.ensurePacksLoaded?.();
    return engineInstance;
  }, []);
  
  const translate = React.useCallback((input, options) => {
    return engine.translate(input, options);
  }, [engine]);
  
  const batchTranslate = React.useCallback((inputs, options) => {
    return engine.batchTranslate(inputs, options);
  }, [engine]);
  
  const getSuggestions = React.useCallback((partial, limit) => {
    return engine.getSuggestions(partial, limit);
  }, [engine]);
  
  const clearCache = React.useCallback(() => {
    engine.clearCache();
  }, [engine]);
  
  const updateConfig = React.useCallback((newConfig) => {
    engine.updateConfig(newConfig);
  }, [engine]);
  
  const stats = engine.getStats();
  
  return { 
    translate, 
    batchTranslate, 
    getSuggestions, 
    clearCache,
    updateConfig,
    stats 
  };
}

// Enhanced hook with loading states
export function useEnhancedTranslation(config = {}) {
  const { translate } = useTranslation(config);
  const [isTranslating, setIsTranslating] = React.useState(false);
  const [error, setError] = React.useState(null);
  
  const performTranslation = React.useCallback(async (input, options = {}) => {
    setIsTranslating(true);
    setError(null);
    
    try {
      // Try local translation first
      const localResult = translate(input, options);
      
      if (localResult && localResult.confidence > 0.7) {
        // Good enough local result
        setIsTranslating(false);
        return {
          success: true,
          translation: localResult.translation,
          confidence: localResult.confidence,
          method: localResult.method,
          source: 'local'
        };
      }
      
      // If no good local result, simulate API delay for UX
      if (options.allowApi !== false) {
        await new Promise(resolve => setTimeout(resolve, 300));
        
        setIsTranslating(false);
        
        // Return local result if available, even with lower confidence
        if (localResult) {
          return {
            success: true,
            translation: localResult.translation,
            confidence: localResult.confidence,
            method: localResult.method,
            source: 'local_fallback'
          };
        }
        
        // No translation found
        return {
          success: false,
          error: 'Translation not available',
          suggestions: translate(input, { ...options, fuzzy: true })
        };
      }
      
      setIsTranslating(false);
      return localResult ? { success: true, ...localResult } : { success: false };
      
    } catch (err) {
      setError(err.message);
      setIsTranslating(false);
      
      return {
        success: false,
        error: err.message
      };
    }
  }, [translate]);
  
  return {
    performTranslation,
    isTranslating,
    error
  };
}

// Unit tests
export function runTests() {
  const engine = new TranslationEngine();
  const testResults = [];
  
  const tests = [
    // Basic exact matches
    { name: 'Exact match', input: 'kemon acho', expected: { method: 'exact', confidence: 1.0 } },
    { name: 'Exact match with spaces', input: '  kemon acho  ', expected: { method: 'exact', confidence: 1.0 } },
    
    // Fuzzy matches
    { name: 'Fuzzy match (typo)', input: 'kemon aco', expected: { method: 'fuzzy', minConfidence: 0.7 } },
    { name: 'Fuzzy match (missing char)', input: 'dhonobad', expected: { method: 'fuzzy', minConfidence: 0.7 } },
    
    // Pattern matches
    { name: 'Pattern: question ki', input: 'tumi ki koro', expected: { method: 'pattern', pattern: 'question_ki' } },
    { name: 'Pattern: ami korbo', input: 'ami khela korbo', expected: { method: 'pattern', pattern: 'ami_korbo' } },
    { name: 'Pattern with punctuation', input: 'tumi ki koro?', expected: { method: 'pattern', pattern: 'question_ki' } },
    
    // Contextual matches
    { name: 'Contextual match', input: 'ami choto mach khabo', expected: { method: 'contextual' } },
    { name: 'Contextual partial', input: 'boro bari ache amar', expected: { method: 'contextual' } },
    
    // Word by word
    { name: 'Word by word', input: 'ami student', expected: { method: 'weighted_word_by_word' } },
    { name: 'Mixed known/unknown', input: 'ami good student', expected: { method: 'weighted_word_by_word', minConfidence: 0.3 } },
    
    // Edge cases
    { name: 'Empty input', input: '', expected: null },
    { name: 'Null input', input: null, expected: null },
    { name: 'Too long input', input: 'a'.repeat(300), expected: null },
    { name: 'Only punctuation', input: '???!!!', expected: null },
    { name: 'Mixed language', input: 'কেমন acho', expected: { method: 'word_by_word' } },
    { name: 'Empty array', input: '   ', expected: null },
    { name: 'Unknown phrase', input: 'xyz abc', expected: { method: 'word_by_word', confidence: 0 } }
  ];
  
  console.log('Running Translation Engine Tests...\n');
  
  tests.forEach((test, i) => {
    const result = engine.translate(test.input);
    let pass = false;
    
    if (test.expected === null) {
      pass = result === null;
    } else if (result) {
      pass = result.method === test.expected.method;
      
      if (test.expected.confidence !== undefined) {
        pass = pass && result.confidence === test.expected.confidence;
      }
      
      if (test.expected.minConfidence !== undefined) {
        pass = pass && result.confidence >= test.expected.minConfidence;
      }
      
      if (test.expected.pattern !== undefined) {
        pass = pass && result.pattern === test.expected.pattern;
      }
    }
    
    testResults.push({ test: test.name, pass });
    
    console.log(`Test ${i + 1}: ${pass ? '✅' : '❌'} ${test.name}`);
    if (result) {
      console.log(`  Result: "${result.translation}" (${result.method}, confidence: ${result.confidence.toFixed(2)})`);
    } else {
      console.log('  Result: null');
    }
  });
  
  const passed = testResults.filter(r => r.pass).length;
  const total = testResults.length;
  
  console.log(`\nTest Summary: ${passed}/${total} passed (${((passed/total)*100).toFixed(1)}%)`);
  console.log('\nEngine Stats:', engine.getStats());
  
  return testResults;
}

// Export the engine class for advanced usage
export { TranslationEngine, SimpleLRUCache, DEFAULT_CONFIG };

// Default export (singleton)
const _defaultEngine = engineInstance || (engineInstance = new TranslationEngine(clientData));
export default _defaultEngine;