# DHK Align — Frontend (React)

Privacy‑first, culturally tuned **Banglish ⇄ English** translation UI.  
Runs 100% in‑browser for the Free tier and talks to the **Cloudflare Edge** for Pro requests.

**Repo root:** https://github.com/sartu01/dhkalign  
**Support:** info@dhkalign.com • **Security:** admin@dhkalign.com

---

## ✨ Features

- React 18 UI with clean, accessible components
- Client‑side engine (Free tier) with cache and fuzzy matching
- Pro mode via Edge API (no direct backend exposure)
- Offline‑friendly; no PII stored
- TypeScript‑ready structure (opt‑in)

---

## 🚀 Quick Start (one‑command)

Starts the app at **http://localhost:3000** and assumes you’re hitting a running Edge Worker (dev or prod).

```bash
# from repo root
cd frontend
cp -n .env.example .env.local 2>/dev/null || true
npm ci && npm start
```

### Edge Worker (optional, for full local flow)
If you want to test Pro calls locally against your dev Worker:

```bash
# separate terminal, from repo root
cd infra/edge
BROWSER=false wrangler dev --local --ip 127.0.0.1 --port 8789 --config wrangler.toml
```

Set your API base URL accordingly (see **Environment**).

---

## 🔧 Environment

Create `frontend/.env.local` (or copy `.env.example`) and set:

```ini
# Dev: local Worker
REACT_APP_API_BASE_URL=http://127.0.0.1:8789
# Prod: Edge domain
# REACT_APP_API_BASE_URL=https://edge.dhkalign.com

REACT_APP_LOG_LEVEL=info
REACT_APP_CACHE_TTL=300000
REACT_APP_MAX_INPUT_LENGTH=200
REACT_APP_ENABLE_ANALYTICS=false
REACT_APP_ENABLE_VOICE=false
```

---

## 🏗️ Project Structure

```
frontend/
├─ public/
│  └─ index.html
├─ src/
│  ├─ api/             # Edge API hooks (Pro)
│  ├─ components/      # UI components
│  ├─ hooks/           # useTranslation, etc.
│  ├─ utils/           # engine, cache, logger
│  └─ App.jsx / App.tsx
├─ package.json
└─ README.md
```

---

## 🧠 Client Engine (Free tier)

- Exact + slang + fuzzy matching  
- Compound handling & n‑gram index  
- LRU cache with TTL  
- Returns `{ translation, confidence, method, cached }`

Example:
```js
import { useTranslation } from './hooks/useTranslator'
const { translate } = useTranslation()
const res = translate('kemon acho')
console.log(res.translation) // "how are you"
```

---

## 🧪 Scripts

```bash
# install deps
npm ci

# dev server (http://localhost:3000)
npm start

# tests
npm test

# production build (CRA, emits frontend/build)
npm run build

# serve a build locally
npx serve -s build
```

> **Note**: We are migrating to **Vite**. Until that PR lands, `npm start` uses the existing CRA setup. After Vite, the build output will be `frontend/dist/`.

---

## 🌐 API contracts (Edge)
- `GET /api/translate?q=...` → `{ translation, ... }` (free)
- `POST /translate` with JSON `{ \"q\":\"...\" }` → `{ translation, ... }` (free, alternate)
- `POST /translate/pro` (header `x-api-key`) → `{ translation, ... }` (pro)

- `GET /api/translate?q=...` → `{ translation, ... }` (free)
- `POST /translate/pro` (header `x-api-key`) → `{ translation, ... }`

All Pro calls go through the Edge Worker; the browser never talks to the origin directly.

---

## 🎨 Components (core)

| Component                    | Purpose                              |
|-----------------------------|--------------------------------------|
| `Translator.jsx/tsx`        | Main translation interface           |
| `TranslateResult.jsx/tsx`   | Renders output + confidence          |
| `ConfidenceIndicator.jsx`   | Visual confidence meter              |
| `ExampleButtons.jsx`        | Quick example inputs                 |

---

## 📦 Bundle & Performance

- Code‑split by route and heavy components  
- Lazy‑load optional features (voice, analytics)  
- Keep Free engine data minimal for fast TTI

---

## 🤝 Contributing

1. Fork + branch (`feat/...`)  
2. `npm ci && npm start`  
3. Add tests for changes  
4. Open PR (CI runs **smoke** + Pages)

---

## 🛡️ License & Support

- Code: MIT  
- Data packs: proprietary (do not redistribute)  
- Support: info@dhkalign.com • Security: admin@dhkalign.com
