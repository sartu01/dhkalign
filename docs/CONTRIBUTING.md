# Contributing to DHK Align (Transliterator‑tion)

This guide explains how to propose changes to **DHK Align — the first Banglish ⇄ English Transliterator‑tion engine**. Keep **privacy**, **security**, **performance**, and **cultural fidelity** at the core. 

> **Posture:** Free tier prefers local/browser processing. The backend origin is **private** and only reachable via the **Cloudflare Worker**. Pro features are **API‑key gated**. Do **not** commit private packs, `.env`, or the SQLite DB.

**Quick Nav:** Getting Started · Making Changes · Code Style · Testing · Submitting PRs · Security · Code of Conduct

Thank you for helping the Bengali community access better transliterator‑tion tooling. 🌍

---

## 🎯 Ways to Contribute

### For Everyone
- **🐛 Report bugs** and edge cases
- **💡 Suggest features** (see Roadmap in README)
- **📝 Improve dataset** (safe phrases, context, spelling variants)
- **📚 Improve docs** (clarify steps, fix typos, examples)
- **🌐 Localization** (interface copy)

### For Developers
- **🔧 Fix issues** (`good-first-issue`)
- **✨ Add features** (see Roadmap)
- **⚡ Performance** (client cache, server TTL cache)
- **🧪 Tests** (frontend + backend)
- **🔒 Security** (middleware hardening, Worker rules)

### For Linguists
- **📖 Transliteration accuracy** (standard forms + English gloss)
- **🗣️ Dialects** (Sylheti/Chittagonian modules)
- **📚 Cultural context** (usage notes)

---

## 🚀 Getting Started

### ⏱️ 10‑Minute Quickstart (frontend)
```bash
cd frontend
npm install
cp .env.example .env
npm start   # http://localhost:3000
```
Most contributions begin in the React app.

> **Public vs Private**  
> Do **not** commit datasets, private packs, `.env`, or the SQLite DB.  
> The backend origin remains **hidden** behind the Cloudflare Worker.

### 1) Fork & Clone
```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/dhkalign.git
cd dhkalign
# Upstream (official repo)
git remote add upstream https://github.com/sartu01/dhkalign.git
```

### 2) Development Setup

#### Frontend (React)
```bash
cd frontend
npm install
npm run lint
cp .env.example .env
npm start
```
Visit http://localhost:3000.

#### Backend (FastAPI, private origin)
From repo root:
```bash
./scripts/run_server.sh   # uvicorn on 127.0.0.1:8090
curl -s http://127.0.0.1:8090/health | jq .
```
**Env:** `backend/.env` (auto‑loaded via `python-dotenv`) — do not commit.

> **Note:** Production calls reach the backend only via the Cloudflare Worker. Direct origin access is disabled in prod.

---

## 📝 Making Changes

**General Rules**
- Do not commit secrets, API keys, datasets, DB dumps
- Do not log or upload raw user input; redact at source
- Keep free tier content **safety_level ≤ 1**; pro content **≥ 2**
- Update docs when behavior/flags change

### Adding Data (Safe Packs)

The public client cache is generated (do **not** edit it directly). To propose additions:
- Create a JSONL file under `docs/contrib/` with entries like:
```jsonl
{"banglish":"kemon acho","translation_en":"how are you","transliteration":"kemon acho","safety_level":1}
{"banglish":"onek dhonnobad","translation_en":"thank you very much","transliteration":"onek dhonnobad","safety_level":1}
```
- Keep **lowercase banglish**, include common **variants**, and simple **English** gloss.
- Maintainers will normalize/import and export the safe cache for the frontend.

**Schema (JSONL)**
- `banglish`: original input (lowercase)
- `transliteration`: normalized transliteration (if differs)
- `translation_en`: English gloss
- `safety_level`: `1` for safe; `≥2` reserved for pro packs
- Optional: `variants[]`, `context_tag`, `region`, `notes`

⚠️ Do not include PII. Only submit content you authored or that is permissibly licensed.

### Code Style
- **JS/TS:** ESLint + Prettier
- **Python:** black + flake8 + mypy

---

## 🧪 Testing

### Frontend
```bash
cd frontend
npm ci
npm run lint
npm test
npm test -- --coverage --watchAll=false
npm run build
```

### Backend
```bash
cd backend
# dev deps (if needed)
pip install -r requirements-dev.txt 2>/dev/null || true
black . && flake8 . && mypy .
pytest
```
**Manual API tests**
```bash
curl -s -X POST http://127.0.0.1:8090/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' | jq .

KEY=$(grep '^API_KEYS=' backend/.env | cut -d= -f2)
PHRASE=$(sed -n '1p' private/pro_packs/slang/dhk_align_slang_pack_002.CLEAN.jsonl | jq -r .banglish)
curl -s -X POST http://127.0.0.1:8090/translate/pro \
  -H 'Content-Type: application/json' -H "x-api-key: $KEY" \
  -d "{\"text\":\"$PHRASE\",\"pack\":\"slang\"}" | jq .
```

---

## 📤 Submitting Your Contribution

### Branch & Commit
```bash
# Sync main
git checkout main && git pull upstream main
# Feature branch
git checkout -b feature/your-feature-name
# Conventional Commits examples
feat(frontend): transliterator-tion UI polish
fix(backend): correct CORS allowlist handling
security(middleware): add HMAC audit logging on 429
```

### PR Checklist
- [ ] Tests pass
- [ ] Docs updated
- [ ] No secrets committed
- [ ] Conventional Commit message

All PRs run CI (lint/test/build). Fix locally before pushing.

---

## 🔐 Security & Responsible Disclosure
- Do **not** file public issues for vulnerabilities
- Email **admin@dhkalign.com** with subject `SECURITY` (include repro steps)
- We acknowledge within 72 hours and coordinate fixes & disclosure
- Avoid sharing sensitive logs or user data (HMAC audit logs contain no content)

---

## 🤝 Code of Conduct (Short)
- Be respectful, inclusive, and constructive
- No harassment or discrimination
- Report conduct issues to **conduct@dhkalign.com** (or **admin@dhkalign.com**)

---

## 📚 Useful Links
- [Root README](../README.md)
- [Backend README](../backend/README.md)
- [Security Policy](./SECURITY.md) · [Privacy](./PRIVACY.md)
- [Next To‑Do](./NEXT_TODO.md)

<div align="center">
  <h3>Thank you for contributing! 🎉</h3>
  <p>Together we’re building a secure Transliterator‑tion engine for the Bengali community.</p>
</div>