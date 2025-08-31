# Privacy Policy

*Last Updated: August 2025*
*This policy explains exactly what data we (don’t) collect, why, and how you stay in control.*
See also: **[Security Policy](./SECURITY.md)** for threat model and infrastructure controls.

## 🎯 Our Privacy Commitment

At DHK Align, **privacy is not a feature, it's our foundation**. We built this service specifically for users who value their privacy above convenience.

### Privacy-First Principles

1. **Free‑first local processing**: Core transliteration runs in your browser. Free requests may call the private backend for availability/rate‑limit checks; content is not stored.
2. **Minimal Collection**: We only collect what's absolutely necessary
3. **User Control**: You decide what to share with us
4. **Full Transparency**: Our code is open source and auditable
5. **No Surveillance**: We don't track or profile users
6. **No Data Sales**: We'll never sell your data to anyone
7. **Right to Forget**: Full delete-on-demand capability

## 📊 Information We Collect

### What We DON'T Collect (By Default)

- ❌ **Translation content**: Your text never leaves your device
- ❌ **Device identifiers**: No fingerprinting
- ❌ **Browser details**: No user agent logging
- ❌ **Location data**: No geolocation tracking
- ❌ **Third-party cookies**: No advertising trackers
- ❌ **Analytics pixels**: No behavior tracking
- ❌ **Social media widgets**: No external integrations
- ❌ **Session recordings**: No heatmaps, click tracking, or screen recording

### What We Collect (Minimal)

#### Security Events (All Tiers)
For abuse prevention and availability, the edge (Cloudflare Worker) and the private backend write **tamper‑evident security audit logs**:
- **What**: event type (e.g., bad request, rate‑limited, auth fail), **IP address**, timestamp, route.
- **What not**: **no translation text**, **no user identifiers**.
- **Where**: local only, in `private/audit/security.jsonl` (HMAC‑signed, append‑only).
- **Retention**: up to **90 days**, then rotated; kept offline unless needed for security investigations.

#### Free Tier Users (Default)
- **No translation content collected; security events as described above**
- **Usage counter**: Stored locally in your browser only
- **Preferences**: Theme and language settings (local storage)
- **Cache**: Recent translations (for speed, stored locally)
- **Error logs**: Only in your browser console, never uploaded

#### Pro/Lifetime Users (Optional Account)
If you choose to create an account for Pro features:

| Data Type | Purpose | Storage | Retention |
|-----------|---------|---------|-----------|
| **Email address** | Login, password reset, support communication | Encrypted database | While account is active + 30 days |
| **Payment reference** | Subscription management | Tokenized via Stripe/BTCPay | 7 years (legal requirement) |
| **Subscription status** | Feature access control | Internal database | While active + 30 days |
| **Account creation date** | Security and analytics | Internal database | While active + 30 days |
| **Last login timestamp** | Security monitoring | Internal database | While active + 30 days |

#### Optional Analytics (Disabled by Default)
Analytics are **off by default** and require explicit opt-in in Settings. We do not use any third-party analytics.
If you explicitly enable analytics in settings:

| Data Type | Purpose | Processing | Retention |
|-----------|---------|------------|-----------|
| **Translation method used** | Improve engine performance | Anonymous aggregation | 90 days |
| **Translation confidence score** | Quality improvement | Statistical analysis | 90 days |
| **Processing time** | Performance optimization | Anonymous metrics | 90 days |
| **Success/failure rate** | Error reduction | Anonymous statistics | 90 days |

#### Optional Feedback (User-Initiated)
If you submit feedback to improve translations:

| Data Type | Purpose | Storage | Retention |
|-----------|---------|---------|-----------|
| **Original phrase** | Translation improvement | Encrypted database | 5 years (manual review + improvement) |
| **Suggested translation** | Quality enhancement | Encrypted database | 5 years (manual review + improvement) |
| **Feedback rating** | Performance metrics | Anonymous aggregation | 5 years (manual review + improvement) |
| **Comments** | Context understanding | Encrypted database | 5 years (manual review + improvement) |
| **Submission timestamp** | Data management | Internal logs | 1 year |

## 💾 How We Store Data

### Browser Storage (Your Device)

```javascript
// Example of what's stored locally (you control this)
{
  "dhk_align_preferences": {
    "theme": "dark",
    "language": "en",
    "analytics_enabled": false,
    "error_reporting_enabled": false
  },
  "dhk_align_cache": {
    "kemon_acho": {
      "translation": "how are you",
      "timestamp": 1641234567890,
      "confidence": 1.0
    }
  },
  "dhk_align_usage": {
    "daily_count": 3,
    "last_reset": "2024-01-27"
  }
}
```

**Your Control**: You can clear this anytime via:
- Browser settings → Clear browsing data
- DHK Align settings → Clear cache
- Developer tools → Application → Storage

### Server Storage (Pro Users Only)

```json
// Example of server data (minimal, encrypted)
{
  "user_id": "usr_abc123",
  "email_hash": "sha256_hash_of_email",
  "subscription": {
    "tier": "pro",
    "status": "active", 
    "created_at": "2024-01-27T10:30:00Z",
    "expires_at": "2024-02-27T10:30:00Z"
  },
  "payment_reference": "stripe_cus_xyz789",
  "created_at": "2024-01-27T10:30:00Z",
  "last_active": "2024-01-27T15:45:00Z",
  "error_reports": []
}
// Security audit logs are separate, local-only, and contain no translation text.
```

**What's NOT stored**:
- No translation history
- No personal details beyond email
- No browsing patterns
- No device information

## 🔐 Data Security

### Encryption Standards

| Data Type | Encryption Method | Key Management |
|-----------|-------------------|----------------|
| **Emails** | AES-256 at rest | Rotating keys, separate key store |
| **Database** | TLS 1.3 in transit, AES-256 at rest | Hardware security modules |
| **Backups** | AES-256 with separate keys | Encrypted key storage |
| **Security audit logs (HMAC)** | Local filesystem; integrity via HMAC | Secret in .env (AUDIT_HMAC_SECRET) |
| **Local preferences** | AES encryption (optional) | Client-side key generation |

### Infrastructure Security

- **Hosting**: Privacy-respecting providers (no big tech)
- **Access**: Principle of least privilege
- **Monitoring**: No user behavior tracking
- **Backups**: Encrypted, automated deletion schedules
- **Networks**: Segmented, firewall-protected
- **Error Reporting**: Disabled by default; if enabled, scrubbed of sensitive data
- **Edge shield**: Cloudflare Worker restricts routes and rate‑limits before origin.

### Code Security

- **Open Source**: Fully auditable on GitHub
- **Regular Audits**: Security reviews and dependency scanning
- **Minimal Dependencies**: Reduced attack surface
- **Input Validation**: All user input sanitized
- **Output Encoding**: XSS prevention

## 🌍 Data Sharing & Third Parties

### Who We Share With

| Entity | What We Share | Why | Legal Basis |
|--------|---------------|-----|-------------|
| **Nobody** | Translation content | N/A - Never leaves your device | N/A |
| **Stripe** | Email, payment info | Payment processing only | Contractual necessity |
| **BTCPay** | Invoice ID only | Crypto payment processing | Contractual necessity |

### Who We DON'T Share With

- ❌ **Advertisers**: No data sales or sharing
- ❌ **Data brokers**: No third-party data sales
- ❌ **Analytics companies**: No external tracking
- ❌ **Social media**: No integration or sharing
- ❌ **AI companies**: No training data sharing
- ❌ **Government**: Only if legally compelled with warrant
- ❌ **Insurers/employers**: No sharing with health, life, or employment entities

### International Transfers

- **Primary processing**: Your browser (your country)
- **Server location**: EU/EEA for GDPR compliance
- **Payment processing**: Stripe (adequate protections)
- **Crypto payments**: Decentralized (no central authority)

## 🔄 Data Retention

| Data Type | Retention Period | Reason | Deletion Method |
|-----------|------------------|--------|-----------------|
| **Translation cache** | Session only | Performance | Automatic browser cleanup |
| **Free user data** | None collected | Privacy-first design | N/A |
| **Pro user emails** | Account lifetime + 30 days | Account recovery | Automated purging |
| **Payment records** | 7 years | Legal requirements | Secure deletion |
| **Feedback data** | 5 years | Service improvement | Manual review possible |
| **Analytics** | 90 days | Performance optimization | Automated deletion |
| **Error logs** | 30 days | Debugging | Automated rotation |
| **Security audit logs** | 90 days | Abuse prevention & forensics | Local rotation (append‑only JSONL) |

### Automated Deletion

```bash
# Automated data cleanup (runs daily)
# Delete expired sessions
DELETE FROM sessions WHERE expires_at < NOW() - INTERVAL '30 days';

# Delete old analytics
DELETE FROM analytics WHERE created_at < NOW() - INTERVAL '90 days';

# Delete deactivated accounts
DELETE FROM users WHERE deactivated_at < NOW() - INTERVAL '30 days';
```

## 👤 Your Privacy Rights

### Universal Rights (All Users)

| Right | How to Exercise | Response Time |
|-------|----------------|---------------|
| **Access** | Email privacy@dhkalign.com | 30 days |
| **Correction** | Settings page or email | 7 days |
| **Deletion** | Settings → Delete Account | 24 hours (payment records and security logs may be retained as required by law) |
| **Data Portability** | Settings → Export Data | 7 days |
| **Opt-out** | Settings → Disable Analytics | Immediate |
| **Right to Restrict** | Email privacy@dhkalign.com | 7 days |

### Regional Rights

- **Legal basis**: 
  - **Contract necessity**: Pro accounts, payments, and access control
  - **Consent**: Optional analytics and optional feedback submissions
  - **Legitimate interest**: Basic, client-side service operation (no personal data required)
- **Data controller**: DHK Align
- **DPO contact**: privacy@dhkalign.com
- **Supervisory authority**: Your local data protection authority
- **Right to object**: Full opt-out available
- **Automated decision making**: None
- **Right to restriction**: You may restrict processing instead of deletion

#### CCPA (California Users)
- **Personal information**: As defined in CCPA
- **Sale of data**: We don't sell personal information
- **Right to know**: Full transparency in this policy
- **Right to delete**: Available in account settings
- **Non-discrimination**: No penalties for exercising rights

#### PIPEDA (Canada Users)
- **Purpose limitation**: Data used only for stated purposes
- **Consent**: Explicit opt-in for any data collection
- **Access rights**: Full access to personal information
- **Retention limits**: Minimal retention periods

### How to Exercise Rights

```bash
# Via Email
To: privacy@dhkalign.com
Subject: Privacy Request - [Your Right]
Body: 
- Full name (if account holder)
- Email address
- Specific request
- Preferred response method

# Via API (Pro users)
curl -X POST https://api.dhkalign.com/privacy/request \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"type": "access", "email": "your@email.com"}'

# Via Settings (Account holders)
Account Settings → Privacy → Manage My Data
```

## 🍪 Cookies & Tracking

### What We Use

| Cookie | Purpose | Duration | Required |
|--------|---------|----------|----------|
| **None** | We don't use cookies by default | N/A | No |


### What We DON'T Use

- ❌ **Tracking cookies**: No user behavior tracking
- ❌ **Third-party cookies**: No external trackers
- ❌ **Advertising cookies**: No ad networks
- ❌ **Social media pixels**: No social tracking
- ❌ **Analytics cookies**: No Google Analytics
- ❌ **Fingerprinting**: No device identification
- ❌ **Session replay**: No FullStory, Hotjar, or equivalent

### Signals We Honor
- **Global Privacy Control (GPC)**: Treated as an opt-out for any optional features
- **Do Not Track (DNT)**: Honored; no tracking enabled by default

### Local Storage Only

We use browser localStorage and sessionStorage for:
- User preferences (theme, language)
- Translation cache (performance)
- Daily usage counter (rate limiting)

**Your control**: Clear anytime via browser settings.

## 📧 Communications

### When We Contact You

| Situation | Method | Frequency | Opt-out |
|-----------|--------|-----------|---------|
| **Security breaches** | Email | As needed | No (legal requirement) |
| **Service outages** | Email | As needed | No (service continuity) |
| **Policy changes** | Email + in-app | When changed | No (transparency requirement) |
| **Payment issues** | Email | As needed | No (account management) |
| **Product updates** | Email | Monthly max | Yes (unsubscribe link) |

### How to Unsubscribe

- **All emails**: email info@dhkalign.com with subject "UNSUBSCRIBE"
- **Marketing only**: Link in each email
- **Account settings**: Communications → Preferences
- **Complete opt-out**: Delete your account
- **Security-only opt-in**: Request at privacy@dhkalign.com

### Email Security

- **Encryption**: TLS in transit
- **Authentication**: SPF, DKIM, DMARC
- **Content**: No tracking pixels or beacons
- **Links**: Direct links only, no link tracking

## 👶 Children's Privacy

### Our Policy

- **Age requirement**: No minimum age for basic use
- **Data collection**: Zero data collection by default
- **Parental consent**: Not required (no data collection)
- **Educational use**: Safe for schools and students
- **COPPA compliance**: Full compliance through no data collection

### Special Protections

- No account creation under 13 for paid features
- No behavioral tracking of any age
- No marketing to children
- Open source code for institutional review
- Strict parental consent required for any optional account creation under 16

## 🌐 International Users

### Data Location

| Processing Type | Location | Legal Basis |
|----------------|----------|-------------|
| **Translation processing** | Your device | User control |
| **Account data** | EU/EEA servers | GDPR compliance |
| **Payment processing** | Stripe global infrastructure | Adequate protections |
| **Backup storage** | EU/EEA only | Data residency |

### Cross-Border Transfers

- **Adequacy decisions**: Only to adequate countries
- **Standard contractual clauses**: For essential services
- **User consent**: For any optional transfers
- **Local alternatives**: BTCPay for crypto payments

### Regional Compliance

- **GDPR**: Full compliance (EU/EEA)
- **CCPA**: Full compliance (California)
- **PIPEDA**: Full compliance (Canada)
- **LGPD**: Full compliance (Brazil)
- **Local laws**: Compliance where applicable

## 🔄 Policy Changes

### How We Handle Changes

1. **30-day notice**: Email notification to all users
2. **Website banner**: Prominent notice on homepage
3. **Version control**: All changes tracked in Git
4. **Comparison tool**: See what changed
5. **Opt-out period**: Delete account if you disagree

### Types of Changes

| Change Type | Notice Period | User Action Required |
|-------------|---------------|---------------------|
| **Clarifications** | None | No action needed |
| **Additional protections** | 7 days | No action needed |
| **New data collection** | 30 days | Explicit opt-in required |
| **Changed purposes** | 30 days | Re-consent required |
| **Legal updates** | As required | May require acceptance |
| **Error reporting toggle** | 7 days | Opt-in only |

### Change History

All privacy policy changes are tracked in our Git repository:
- View changes: `git log --oneline PRIVACY.md`
- Compare versions: GitHub compare view
- Download old versions: Git checkout specific commits

## 🔍 Privacy Monitoring

### Regular Audits

- **Monthly**: Internal privacy review
- **Quarterly**: External security audit
- **Annually**: Comprehensive privacy audit
- **Continuous**: Automated compliance monitoring

### Metrics We Track

- Zero data breaches (target and current status)
- User consent rates (for optional features)
- Data retention compliance (automated checks)
- Request response times (privacy rights)
- Policy clarity (user feedback)

### Transparency Reports

Annual transparency reports include:
- Government requests received: 0
- Data breaches: 0
- Privacy complaints: [Number]
- Rights requests processed: [Number]
- Policy violations: [Number]

## 📞 Privacy Contacts

### Primary Contact
- **Email**: privacy@dhkalign.com
- **Alias**: info@dhkalign.com
- **Response time**: Within 72 hours
- **Languages**: English, Bengali
- **Security issues**: admin@dhkalign.com (use subject "SECURITY")

### Data Protection Officer
- **Contact**: Same as above (small organization)
- **Role**: Privacy compliance and user rights
- **Availability**: Business hours (UTC)

### Complaints
- **Internal**: privacy@dhkalign.com
- **EU users**: Your local supervisory authority
- **California users**: California Attorney General
- **Other regions**: Local data protection authority

### Mailing Address
```
DHK Align Privacy Team
[Physical Address]
[City, State/Province, Postal Code]
[Country]
```

## 🎯 Privacy by Design

### Technical Measures

- **Client-side processing**: No server dependency for core function
- **Minimal data architecture**: Collect nothing by default
- **Encryption everywhere**: End-to-end where applicable
- **Open source**: Full transparency and auditability
- **Privacy defaults**: Most protective settings by default

### Organizational Measures

- **Privacy training**: All team members educated
- **Impact assessments**: For any new features
- **Vendor evaluation**: Privacy criteria for all services
- **Incident procedures**: Clear breach response plan
- **Regular reviews**: Continuous improvement process

### Legal Measures

- **Privacy-first contracts**: With all service providers
- **Data processing agreements**: Clear responsibilities
- **Retention schedules**: Automated enforcement
- **User rights procedures**: Efficient response systems
- **Compliance monitoring**: Regular legal review

---

## 📋 Privacy Summary

**TL;DR**: We protect your privacy by not collecting translation content. Transliteration runs in your browser; when the backend is used, it stores **no content**, only minimal security metadata (e.g., IP) for abuse prevention.

### Quick Facts
- ✅ **Zero tracking** by default
- ✅ **Client-side translation** engine
- ✅ **Open source** code
- ✅ **Minimal data** collection
- ✅ **Strong encryption** when needed
- ✅ **User control** over all data
- ✅ **No data sales** ever
- ✅ **GDPR compliant**

---

<div align="center">
  <p><strong>Your privacy is our priority</strong></p>
  <p>Questions? Contact us at <a href="mailto:privacy@dhkalign.com">privacy@dhkalign.com</a></p>
  <p>Alternative contact: <a href="mailto:info@dhkalign.com">info@dhkalign.com</a></p>
</div>