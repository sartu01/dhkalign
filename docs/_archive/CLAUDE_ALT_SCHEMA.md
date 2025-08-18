### JSONL Schema (data/schema.jsonl)
```json
{
  "id": "street_001",
  "source": "assalamu alaikum",
  "variant": ["salam", "salamualaikum"],
  "translit": "assalamu alaikum",
  "translation": "peace be upon you",
  "context_tag": "greeting_religious",
  "region": "dhk_general",
  "confidence": 0.95,
  "frequency": "high",
  "formality": "polite",
  "phonetic_fidelity": "high",
  "pack": "street",
  "added_by": "manual_seed",
  "reviewed_by": "curator",
  "created_at": "2025-01-15T00:00:00Z",
  "updated_at": "2025-01-15T00:00:00Z",
  "version": "0.1.0"
}
```

### Version Structure
```
data/
├── VERSION                 # Current: 0.1.0
├── LICENSE.md             # CC-BY-SA-4.0 + attribution
├── SCHEMA.md              # Field definitions
├── releases/
│   ├── v0.1.0-street.jsonl    # 150 phrases
│   ├── v0.1.0-vendor.jsonl    # 80 phrases  
│   └── v0.1.0-meta.json       # Release metadata
└── contrib/
    ├── pending.jsonl          # Unreviewed submissions
    └── rejected.jsonl         # Failed review with reasons
```