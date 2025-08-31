# DHK Align - Frontend (React, Transliterator-tion UI)

*Privacy-first, culturally tuned Banglish ⇄ English Transliterator-tion UI. Runs 100% in-browser with offline-first design.*

**Repo:** [github.com/sartu01/dhkalign](https://github.com/sartu01/dhkalign)  
**Support:** [info@dhkalign.com](mailto:info@dhkalign.com) • **Admin:** [admin@dhkalign.com](mailto:admin@dhkalign.com)

[![React](https://img.shields.io/badge/React-18.x-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-Ready-blue.svg)](https://www.typescriptlang.org/)
[![Bundle Size](https://img.shields.io/badge/bundle-~150KB-green.svg)](https://bundlephobia.com/)

Privacy-first, culturally aware Banglish ⇄ English Transliterator-tion UI. Runs **entirely in-browser** for privacy and speed. Connects to hidden backend for Pro API.

## 🚀 Quick Start

Development server defaults to http://localhost:3000 — no backend required.

```bash
npm install
npm start   # http://localhost:3000
npm test
npm run build
```

## 🏗️ Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/      # Transliterator-tion UI
│   ├── utils/           # Engine, cache, logger
│   ├── api/             # Optional backend hooks
│   └── hooks/           # useTranslator
├── package.json
└── README.md
```

## 🧠 Engine Features

- Exact + slang + fuzzy matching
- Compound word handler
- Contextual + n-gram parsing
- Weighted word-by-word fallback

### Usage

```javascript
import { useTranslation } from '../hooks/useTranslator';

const { translate } = useTranslation();
const result = translate("kemon acho");
console.log(result.translation); // "how are you"
```

## 🎨 Components

### Core Components

| Component | Purpose | Props |
|-----------|---------|-------|
| `Translator.jsx` | Main transliterator-tion interface | `onTranslate`, `maxLength` |
| `TranslateResult.jsx` | Display transliterator-tion output | `result`, `onFeedback` |
| `ConfidenceIndicator.jsx` | Show transliterator-tion confidence | `confidence`, `method` |
| `ExampleButtons.jsx` | Quick example transliterator-tions | `examples`, `onSelect` |

### Example Usage

```javascript
// Main Transliterator-tion Component
import { useState } from 'react';
import { useTranslation } from '../hooks/useTranslator';

export function Translator() {
  const { translate, isTranslating } = useTranslation();
  const [input, setInput] = useState('');
  const [result, setResult] = useState(null);

  const handleTranslate = async () => {
    const translation = await translate(input);
    setResult(translation);
  };

  return (
    <div className="translator-container">
      <textarea 
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Enter Banglish text..."
        maxLength={200}
      />
      <button onClick={handleTranslate} disabled={isTranslating}>
        Translate
      </button>
      {result && (
        <TranslateResult 
          translation={result.translation}
          confidence={result.confidence}
          method={result.method}
        />
      )}
    </div>
  );
}
```

## 🔧 Translation Engine

### 8-Layer Fallback System

```javascript
// src/utils/translation-engine.js
class TranslationEngine {
  constructor(data = clientData, config = {}) {
    this.translations = data.t || {};
    this.slangMap = this.buildSlangMap();
    this.patterns = this.buildPatterns();
    this.ngramIndex = this.buildNgramIndex();
    this.cache = new LRUCache(config.maxCacheSize || 100);
  }

  translate(input, options = {}) {
    const normalized = this.normalizeInput(input);
    
    // Check cache first
    const cached = this.cache.get(normalized);
    if (cached) return cached;
    
    // 8-layer fallback system
    const methods = [
      () => this.exactMatch(normalized),        // 1.0 confidence
      () => this.slangMatch(normalized),        // 0.95 confidence
      () => this.fuzzyMatch(normalized),        // 0.8-0.9 confidence
      () => this.compoundMatch(normalized),     // 0.85 confidence
      () => this.patternMatch(normalized),      // 0.8-0.95 confidence
      () => this.ngramMatch(normalized),        // 0.75 confidence
      () => this.contextualMatch(normalized),   // 0.85 confidence
      () => this.weightedWordByWord(normalized) // Variable confidence
    ];
    
    for (const method of methods) {
      const result = method();
      if (result) {
        this.cache.set(normalized, result);
        return result;
      }
    }
    
    return null;
  }

  // Exact phrase matching
  exactMatch(input) {
    const translation = this.translations[input];
    if (translation) {
      return {
        translation,
        confidence: 1.0,
        method: 'exact',
        cached: false
      };
    }
    return null;
  }

  // Fuzzy matching with phonetic similarity
  fuzzyMatch(input) {
    const threshold = 0.8;
    let bestMatch = null;
    let bestScore = 0;

    for (const [phrase, translation] of Object.entries(this.translations)) {
      const similarity = this.calculateSimilarity(input, phrase);
      if (similarity >= threshold && similarity > bestScore) {
        bestScore = similarity;
        bestMatch = {
          translation,
          confidence: similarity,
          method: 'fuzzy',
          cached: false
        };
      }
    }

    return bestMatch;
  }
}
```

### Hooks

```javascript
// src/hooks/useTranslator.js
import { useState, useCallback } from 'react';
import { TranslationEngine } from '../utils/translation-engine';
import translationData from '../utils/dhk_align_data_client.json';

export function useTranslation() {
  const [engine] = useState(() => new TranslationEngine(translationData));
  const [isTranslating, setIsTranslating] = useState(false);
  const [stats, setStats] = useState({
    totalTranslations: 0,
    cacheHits: 0,
    averageConfidence: 0
  });

  const translate = useCallback(async (input) => {
    if (!input?.trim()) return null;
    
    setIsTranslating(true);
    const startTime = performance.now();

    try {
      const result = engine.translate(input.trim());
      const duration = performance.now() - startTime;

      // Update statistics
      setStats(prev => ({
        ...prev,
        totalTranslations: prev.totalTranslations + 1,
        cacheHits: prev.cacheHits + (result?.cached ? 1 : 0)
      }));

      // Log performance (if enabled)
      if (duration > 50) {
        console.warn(`Slow translation: ${duration}ms`);
      }

      return result;
    } finally {
      setIsTranslating(false);
    }
  }, [engine]);

  return {
    translate,
    isTranslating,
    stats
  };
}
```

## ⚙️ Configuration

### Environment Variables

```bash
# .env.example
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_LOG_LEVEL=info
REACT_APP_CACHE_TTL=300000
REACT_APP_MAX_INPUT_LENGTH=200
REACT_APP_ENABLE_ANALYTICS=false
REACT_APP_ENABLE_VOICE=false
```

### Engine Configuration

```javascript
// src/utils/config.js
export const ENGINE_CONFIG = {
  maxCacheSize: 100,
  maxInputLength: 200,
  fuzzyThreshold: 0.8,
  enablePhonetic: true,
  enableSlang: true,
  enableCompounds: true,
  cacheStrategy: 'lru',
  persistCache: true
};
```

## 🎨 Styling & Themes

### CSS Structure

```css
/* src/App.css */
.translator-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

.translation-input {
  width: 100%;
  min-height: 120px;
  padding: 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 1rem;
  resize: vertical;
}

.translation-result {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 8px;
  border-left: 4px solid #3b82f6;
}

.confidence-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.confidence-bar {
  height: 4px;
  background: currentColor;
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .translation-input {
    background: #1f2937;
    border-color: #374151;
    color: #f9fafb;
  }
  
  .translation-result {
    background: #374151;
    color: #f9fafb;
  }
}
```

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
npm test

# Watch mode
npm test -- --watch

# Coverage report
npm test -- --coverage --watchAll=false
```

### Test Examples

```javascript
// src/utils/__tests__/translation-engine.test.js
import { TranslationEngine } from '../translation-engine';

describe('TranslationEngine', () => {
  let engine;

  beforeEach(() => {
    engine = new TranslationEngine();
  });

  describe('Exact Match', () => {
    it('should translate exact phrases', () => {
      const result = engine.translate('kemon acho');
      expect(result.translation).toBe('how are you');
      expect(result.confidence).toBe(1.0);
      expect(result.method).toBe('exact');
    });
  });

  describe('Fuzzy Match', () => {
    it('should handle typos', () => {
      const result = engine.translate('kemon aco');
      expect(result.translation).toBe('how are you');
      expect(result.confidence).toBeGreaterThan(0.8);
      expect(result.method).toBe('fuzzy');
    });
  });

  describe('Compound Words', () => {
    it('should handle compound words', () => {
      const result = engine.translate('ekhonei');
      expect(result.translation).toBe('right now');
      expect(result.method).toBe('compound');
    });
  });
});
```

## 📦 Build & Deployment

### Production Build

```bash
# Create optimized build
npm run build

# Analyze bundle size
npm run analyze

# Serve locally
npx serve -s build
```

### Bundle Optimization

```javascript
// webpack.config.js (if ejected)
const path = require('path');

module.exports = {
  // ... other config
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
        },
        translations: {
          test: /dhk_align_data_client\.json$/,
          name: 'translations',
          chunks: 'all',
        },
      },
    },
  },
};
```

## 🔍 Performance Monitoring

### Metrics Collection

```javascript
// src/utils/performance.js
export class PerformanceMonitor {
  static measureTranslation(fn) {
    return async (...args) => {
      const start = performance.now();
      const result = await fn(...args);
      const duration = performance.now() - start;
      
      // Log slow translations
      if (duration > 100) {
        console.warn(`Slow translation: ${duration}ms`);
      }
      
      // Track in analytics (if enabled)
      if (window.analytics?.track) {
        window.analytics.track('Translation Performance', {
          duration,
          method: result?.method,
          confidence: result?.confidence
        });
      }
      
      return result;
    };
  }
}
```

## 🌐 PWA Features

### Service Worker

```javascript
// public/sw.js
const CACHE_NAME = 'dhk-align-v1';
const urlsToCache = [
  '/',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        return response || fetch(event.request);
      }
    )
  );
});
```

### Manifest

```json
{
  "public/manifest.json": {
    "short_name": "DHK Align",
    "name": "DHK Align - Banglish Transliterator-tion",
    "icons": [
      {
        "src": "favicon.ico",
        "sizes": "64x64 32x32 24x24 16x16",
        "type": "image/x-icon"
      }
    ],
    "start_url": ".",
    "display": "standalone",
    "theme_color": "#000000",
    "background_color": "#ffffff"
  }
}
```

## 📱 Mobile Optimization

### Responsive Design

```css
/* Mobile-first responsive design */
@media (max-width: 768px) {
  .translator-container {
    padding: 1rem;
  }
  
  .translation-input {
    font-size: 16px; /* Prevents zoom on iOS */
  }
  
  .example-buttons {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.5rem;
  }
}

@media (max-width: 480px) {
  .confidence-indicator {
    flex-direction: column;
    align-items: flex-start;
  }
}
```

## 🆘 Support & Contact

- General: [info@dhkalign.com](mailto:info@dhkalign.com)
- Security: [admin@dhkalign.com](mailto:admin@dhkalign.com) (use subject "SECURITY")
- Admin/Abuse: [admin@dhkalign.com](mailto:admin@dhkalign.com)
- Bug reports & feature requests: open an issue at [github.com/sartu01/dhkalign/issues](https://github.com/sartu01/dhkalign/issues)

## 📚 Related Docs

- [Security Policy](../docs/SECURITY.md)
- [Privacy Policy](../docs/PRIVACY.md)
- [Backend README](../backend/README.md)
- [Project Overview](../README.md)

----

<div align="center">
  <p>Frontend documentation for DHK Align — the first Transliterator-tion engine.</p>
  <p>
    <a href="../README.md">← Back to main README</a> •
    <a href="mailto:info@dhkalign.com">Support</a> •
    <a href="mailto:admin@dhkalign.com?subject=SECURITY">Security</a> •
    <a href="mailto:admin@dhkalign.com">Admin</a>
  </p>
</div>