# DHK Align - Private Banglish ⇄ English Translator

[![Version](https://img.shields.io/badge/version-1.0.0-black.svg)](#)
[![React](https://img.shields.io/badge/React-18.x-blue.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.1x-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Security](https://img.shields.io/badge/security-first-red.svg)](docs/SECURITY.md)
[![Privacy](https://img.shields.io/badge/privacy-100%25-purple.svg)](docs/PRIVACY.md)

A privacy-first, culturally-aware translation platform for Banglish (Bengali written in English) ⇄ English conversion. **All translations happen in your browser** – your data never leaves your device.

---

## 🌟 Key Features

- **🔒 100% Private**: Client-side translation engine – no server dependency  
- **⚡ Lightning Fast**: <50ms translation with intelligent caching  
- **🎯 Culturally Aware**: Preserves Bengali cultural context and nuances  
- **📱 Mobile First**: Responsive design, PWA-ready  
- **🌐 Offline Capable**: Works without internet after first load  
- **🧠 Smart Engine**: 8-layer fallback system with fuzzy matching  
- **💰 Fair Pricing**: Free demo + affordable Pro tier  

---

## 🏗️ Architecture

```
dhkalign/
├── frontend/              # React SPA with client-side engine
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── utils/         # Translation engine + helpers
│   │   └── api/           # Optional backend integration
│   └── public/            # Static assets
├── backend/               # Optional FastAPI for analytics
│   ├── main.py            # API routes
│   ├── utils/             # Logging & monitoring
│   └── logs/              # Structured logs (JSONL)
├── docs/                  # Documentation
│   └── ARCHITECTURE.md    # System design details
└── README.md              # This file
```

---

## 🚀 Quick Start

### Option 1: Frontend Only (Recommended)

```bash
git clone https://github.com/sartu01/dhkalign.git
cd dhkalign/frontend
npm install
npm start
```

Visit http://localhost:3000 and start translating!

### Option 2: With Backend (Analytics & Feedback)

```bash
# Terminal 1: Start backend
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
python main.py

# Terminal 2: Start frontend
cd frontend
npm install
npm start
```

---

## 🧠 Translation Engine

| Step | Method | Confidence | Example |
|------|--------|------------|---------|
| 1 | Exact Match | 1.0 | kemon acho → how are you |
| 2 | Slang Database | 0.95 | ki obostha → what's up |
| 3 | Fuzzy/Phonetic | 0.8–0.9 | kemon aco → how are you |
| 4 | Compound Words | 0.85 | ekhonei → right now |
| 5 | Pattern Matching | 0.8–0.95 | ami ki korbo → what will I do |
| 6 | N-gram Matching | 0.75 | Partial phrase matching |
| 7 | Contextual | 0.85 | Context-aware lookups |
| 8 | Weighted Word-by-Word | Variable | TF-IDF weighted fallback |

---

## 💰 Monetization

| Tier | Price | Features |
|------|-------|----------|
| **Free Demo** | $0 | 5 translations/day, No account needed |
| **Pro** | $4.99/month | Unlimited translations, Priority support |
| **Lifetime** | $29.99 | One-time payment, All Pro features forever |

Payments supported:  
- **Traditional**: Stripe (Credit/Debit, Apple Pay, Google Pay)  
- **Crypto**: BTCPay Server (Bitcoin, Monero)  
- **Regional**: bKash, Rocket (coming soon)  

---

## 📊 Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Translation Speed | <50ms | Average with caching |
| Bundle Size | ~150KB | Includes translation dataset |
| First Load | <1.5s | With CDN delivery |
| Cache Hit Rate | ~85% | In typical usage |
| Offline Ready | 100% | After first load |

---

## 🔒 Security & Privacy

- ✅ **Zero Server Calls**: All translations happen in-browser  
- ✅ **No Tracking**: No analytics or cookies by default  
- ✅ **No User Data**: No accounts required for free tier  
- ✅ **Open Source**: Fully auditable codebase  
- ✅ **E2E Encrypted**: Pro user preferences encrypted  

See [docs/SECURITY.md](docs/SECURITY.md) and [docs/PRIVACY.md](docs/PRIVACY.md).

---

## 📚 Documentation

- [📖 Architecture Overview](docs/ARCHITECTURE.md) – System design and data flow  
- [🔒 Security Policy](docs/SECURITY.md) – Threat model and security measures  
- [🛡️ Privacy Policy](docs/PRIVACY.md) – Data handling and user rights  
- [🤝 Contributing Guide](docs/CONTRIBUTING.md) – How to contribute  
- [⚙️ Frontend Setup](frontend/README.md) – React development guide  
- [🔧 Backend Setup](backend/README.md) – FastAPI development guide  

---

## 🛠️ Development

### Prerequisites
- Node.js 16+ (18+ recommended)  
- npm 8+  
- Python 3.10+ (for backend)  

### Setup

```bash
# Frontend
cd frontend
cp .env.example .env

# Backend
cd backend
cp .env.example .env
```

### Tests

```bash
cd frontend && npm test
cd backend && pytest
```

---

## 🚀 Deployment

### Frontend (Netlify/Vercel)

```bash
cd frontend
npm run build
# Deploy /build directory
```

### Backend (Optional)

```bash
docker-compose up -d
# or systemctl start dhkalign-backend
```

---

## 🗺️ Roadmap

- **v1.0 (Now)**: 8-layer engine, 450+ phrases, PWA support, Pro/Lifetime pricing  
- **v1.1 (Q3 2025)**: Voice input, 1k+ phrases, Chrome extension, accessibility polish  
- **v2.0 (Q4 2025)**: Regional dialects, API keys, mobile apps, curated packs  

---

## 🤝 Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). PRs welcome!

---

## 📄 License

MIT License – see [LICENSE](LICENSE).

---

## 📞 Support

- General: [info@dhkalign.com](mailto:info@dhkalign.com)  
- Admin: [admin@dhkalign.com](mailto:admin@dhkalign.com)  
- Security: [admin@dhkalign.com](mailto:admin@dhkalign.com) (subject "SECURITY")

---

<div align="center">
  <h3>Made with ❤️ for the Bengali community worldwide</h3>
  <p>
    <a href="https://dhkalign.com">Website</a> • 
    <a href="https://github.com/sartu01/dhkalign">GitHub</a> • 
    <a href="https://twitter.com/dhkalign">Twitter</a>
  </p>
</div>