
# Contributing to DHK Align

This guide explains how to propose changes to DHK Align. Keep privacy, performance, and cultural fidelity at the core. Translation stays client‑side by default.

**Quick Nav:** Getting Started · Making Changes · Code Style · Testing · Submitting PRs · Security · Code of Conduct

Thank you for your interest in making DHK Align better! Every contribution helps the Bengali community worldwide access better translation tools. 🌍

## 🎯 Ways to Contribute

### For Everyone

- **🐛 Report bugs**: Help us identify and fix issues
- **💡 Suggest features**: Share your ideas for improvements
- **📝 Improve translations**: Add phrases, fix errors, suggest better translations
- **📢 Spread the word**: Tell friends, write reviews, share on social media
- **📚 Improve documentation**: Fix typos, add examples, clarify instructions
- **🌐 Localization**: Help translate the interface to other languages

### For Developers

- **🔧 Fix bugs**: Pick from issues labeled `good-first-issue`
- **✨ Add features**: Check our roadmap for priority items
- **⚡ Improve performance**: Optimize the translation engine
- **🧪 Write tests**: Increase test coverage and reliability
- **📊 Add analytics**: Help us understand usage patterns (privacy-preserving)
- **🔒 Enhance security**: Improve our security measures

### For Designers

- **🎨 UI/UX improvements**: Make the interface more intuitive
- **♿ Accessibility**: Improve support for screen readers and disabilities
- **📱 Mobile experience**: Enhance responsive design
- **🌙 Dark mode**: Perfect the dark theme experience
- **🎭 Animations**: Add subtle, meaningful animations

### For Linguists

- **📖 Translation accuracy**: Review and improve existing translations
- **🗣️ Regional dialects**: Add support for Sylheti, Chittagonian variants
- **📚 Cultural context**: Help preserve cultural nuances in translations
- **🔤 Phonetic improvements**: Enhance fuzzy matching algorithms

## 🚀 Getting Started

### ⏱️ 10-Minute Quickstart (Frontend-only)

```bash
cd frontend
npm install
cp .env.example .env
npm start   # http://localhost:3000
```

This is the fastest way to contribute. Most contributions start with the React app.

> **Public vs Private**  
> Do not commit datasets, engine weights, or private .env files.  
> Only commit frontend code, docs, and public backend notes.

### 1. Fork & Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/dhkalign.git
cd dhkalign

# Add upstream remote for syncing (official repo)
git remote add upstream https://github.com/sartu01/dhkalign.git

# Verify remotes
git remote -v
```

### 2. Development Setup

#### Prerequisites

- Node.js 18.19.x (see .nvmrc)
- Python 3.10.12 (see pyproject.toml)
- Git 2.40+
- macOS/Linux/WSL recommended

#### Frontend Development

```bash
# Install dependencies
cd frontend
npm install

# Lint code
npm run lint

# Copy environment file
cp .env.example .env

# Start development server
npm start
```

Visit http://localhost:3000 to see your changes.

#### Backend Development (Optional)

```bash
# Setup Python environment
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt  # or requirements.private.txt if using private features

# Copy environment file
cp .env.example .env

# Start development server
python main.py
```

Visit http://localhost:8000/docs for API documentation.

#### Optional: Docker Dev

```bash
# Start only the public backend (if needed for feedback/health)
docker compose -f docker-compose.public.yml up -d backend
```

### 3. Create a Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a new branch for your contribution
git checkout -b feature/your-feature-name
# Examples:
# - feature/voice-input
# - fix/translation-accuracy
# - docs/setup-instructions
# - ui/mobile-improvements
```

## 📝 Making Changes

**General Rules**
- Do not commit secrets, API keys, or datasets
- Do not log or upload raw user input; anonymize at source
- Keep translations client-side; backend must remain optional
- Follow performance budgets: <50ms cached translate, bundle ~150KB
- Update docs when behavior/flags change

### Adding Translations

Use lowercase keys, include common variants, and keep values in simple, clear English.

The most impactful way to contribute! Edit the translation data:

```json
// frontend/src/utils/dhk_align_data_client.json
{
  "t": {
    // Add your translations here
    "apni kemon achen": "how are you (formal)",
    "tomar bari kothay": "where is your home",
    "ami thik achi": "i am okay",
    "onek dhonnobad": "thank you very much"
  }
}
```

#### JSON Schema for Translation Entries

```json
{
  "type": "object",
  "patternProperties": {
    "^[a-z0-9\\s]+$": { "type": "string" }
  },
  "additionalProperties": false
}
```

*Keys must be lowercase Banglish, values must be simple English.*

#### Translation Guidelines

1. **Use lowercase** for Banglish phrases
2. **Include variations** (formal/informal, regional)
3. **Preserve cultural context** in comments
4. **Test thoroughly** with the translation engine
5. **Add common phrases** that people actually use
6. **Consider phonetic variations** (different spellings)
7. **No personally identifiable information** in examples
8. **Run 'npm test'** to ensure data shape/JSON validity
9. **Romanization**: Use standard Banglish rules (a=আ, o=অ, ee=ই/ঈ, oo=উ, etc.) — accepted variants: kemon/kamne, bhalo/valo.

⚠️ All contributed phrases must be original or permissibly licensed — no scraping from proprietary sources.

#### Examples of Good Translations

```json
{
  // Common greetings
  "salam": "hello (islamic greeting)",
  "namaskar": "hello (hindu greeting)", 
  "adab": "hello (formal/respectful)",
  
  // Regional variations
  "kemon achen": "how are you (standard)",
  "kemon acen": "how are you (sylheti)",
  "kemne acen": "how are you (chittagong)",
  
  // Cultural context
  "eid mubarak": "blessed eid (islamic festival greeting)",
  "poila boishakh": "bengali new year",
  "durga puja": "durga puja (hindu festival)"
}
```

### Code Style Guidelines

Use ESLint + Prettier for React; use black + flake8 + mypy for Python.

#### JavaScript/React

```javascript
// Uses React hooks; no side effects in render
// ✅ Good: Clear, functional, well-documented
export const TranslationResult = ({ text, confidence, method }) => {
  const confidenceColor = useMemo(() => {
    if (confidence > 0.9) return 'text-green-600';
    if (confidence > 0.7) return 'text-yellow-600';
    return 'text-orange-600';
  }, [confidence]);

  return (
    <div className="translation-result bg-white rounded-lg shadow-sm p-4">
      <p className="text-lg font-medium text-gray-900">{text}</p>
      <div className="mt-2 flex items-center justify-between">
        <span className={`text-sm font-medium ${confidenceColor}`}>
          {Math.round(confidence * 100)}% confident
        </span>
        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
          {method}
        </span>
      </div>
    </div>
  );
};
```

#### Python (Backend)

```python
# ✅ Good: Typed, documented, clear error handling
from typing import Dict, Optional, List, Any
from fastapi import HTTPException
from pydantic import BaseModel, validator

class TranslationRequest(BaseModel):
    text: str
    session_id: Optional[str] = None
    
    @validator('text')
    def validate_text(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Text cannot be empty')
        if len(v) > 200:
            raise ValueError('Text too long (max 200 characters)')
        return v.strip()

async def process_translation(
    request: TranslationRequest
) -> Dict[str, Any]:
    """
    Process a translation request with comprehensive error handling.
    
    Args:
        request: Translation request with text and optional session ID
        
    Returns:
        Dictionary containing translation result and metadata
        
    Raises:
        HTTPException: If translation fails or input is invalid
    """
    try:
        # Process translation
        result = await translation_engine.translate(request.text)
        
        if not result:
            raise HTTPException(
                status_code=422, 
                detail="Unable to translate the provided text"
            )
        
        return {
            "translation": result.translation,
            "confidence": result.confidence,
            "method": result.method,
            "success": True
        }
        
    except Exception as e:
        logger.exception(f"Translation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Translation service temporarily unavailable"
        )
```

#### Commit Hooks

```bash
# Enable pre-commit hooks (recommended)
pip install pre-commit && pre-commit install
```

### Commit Messages

We follow Conventional Commits; scopes like (engine), (ui), (docs), (api) are encouraged.

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format: type(scope): description

# Examples:
feat(engine): add compound word detection algorithm
fix(ui): correct dark mode colors in translation results
docs(api): update authentication endpoint examples
perf(cache): optimize LRU eviction strategy
test(engine): add comprehensive fuzzy matching tests
chore(deps): update React to 18.2.0
style(frontend): fix ESLint warnings in components
refactor(backend): simplify user authentication logic
```

### Testing Your Changes

#### Frontend Tests

```bash
cd frontend

# Reproducible installs
npm ci  # reproducible installs

# Run linting
npm run lint

# Fix auto-fixable issues
npm run lint:fix

# Run tests
npm test

# Run tests with coverage
npm test -- --coverage --watchAll=false

# Test the build
npm run build
```

#### Backend Tests

```bash
cd backend

# Install dev dependencies
pip install -r requirements-dev.txt

# Format code
black .

# Run linting
flake8 .

# Type checking
mypy .

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Test API endpoints
pytest tests/test_api.py -v
```
**Never log or upload raw user text. Verify anonymization in any debug output.**

#### Manual Testing

1. **Translation accuracy**: Test your changes with various inputs
2. **Mobile responsiveness**: Check on different screen sizes
3. **Browser compatibility**: Test on Chrome, Firefox, Safari
4. **Accessibility**: Use screen reader and keyboard navigation
5. **Performance**: Ensure no significant slowdowns

### Common Scripts

| Command          | Purpose                  |
|------------------|--------------------------|
| npm run lint:fix | Auto-fix lint issues     |
| npm run analyze  | Bundle analysis          |
| pytest -q        | Run all backend tests    |
| pytest tests/engine | Run only engine tests |

## 📤 Submitting Your Contribution

### Pull Request Checklist

Before submitting your PR, ensure:

- [ ] Tests pass
- [ ] Docs updated
- [ ] No secrets committed
- [ ] Conventional Commit message

We use a simple model: `main` is protected. Create branches as `feature/*` or `fix/*`.

All PRs run GitHub Actions: lint, test, and build. Fix issues locally before pushing.

### Pull Request Template

```markdown
## Description
Brief description of what this PR accomplishes.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Translation improvements

## How Has This Been Tested?
- [ ] Unit tests pass
- [ ] Manual testing completed
- [ ] Tested on mobile devices
- [ ] Tested with screen readers
- [ ] Cross-browser testing completed

## Translation Changes (if applicable)
- Number of translations added: [X]
- Number of translations improved: [X]
- Regional variants added: [list]
- Cultural context preserved: [yes/no]

## Screenshots (if UI changes)
[Add screenshots showing before/after]

## Additional Notes
Any additional information, concerns, or considerations.

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] I accept licensing under the MIT License

## DCO
By submitting this pull request, I certify that the contribution is my original work (or I have rights to submit it) and I agree to license it under the project's MIT License.
```
## 🔐 Security & Responsible Disclosure

- Please **do not file public issues** for security vulnerabilities
- Email **admin@dhkalign.com** with subject `SECURITY` and include reproduction steps
- We will acknowledge receipt within 72 hours and coordinate a fix and disclosure timeline
- Avoid sharing sensitive logs or user data; provide minimal proof-of-concept


### Review Process

1. **Automated checks**: CI/CD pipeline runs tests and linting
2. **Code review**: Maintainers review your changes
3. **Testing**: Additional testing on various devices/browsers
4. **Translation review**: Native speakers verify translation accuracy
5. **Merge**: Approved changes are merged to main branch

## 🏆 Recognition

Contributors are recognized in multiple ways:

### GitHub Recognition
- **Contributors section** in README.md
- **Release notes** mention significant contributions
- **GitHub badges** for consistent contributors

### Community Recognition
- **Website credits** page listing all contributors
- **Social media shoutouts** for major contributions
- **Community Discord** special contributor role (coming soon)

### Translation Contributors
Special recognition for translation work:
- Listed in translation credits
- Acknowledged for specific language/regional contributions
- Priority feedback on new translation features

## 💬 Getting Help

### Community Support

- **GitHub Discussions**: Ask questions and share ideas
- **GitHub Issues**: Report bugs and request features
- **Email**: info@dhkalign.com for general questions
- **Admin Contact**: admin@dhkalign.com for technical issues

### Development Help

- **Setup issues**: Check our troubleshooting guide
- **Code questions**: Ask in GitHub discussions
- **Translation help**: Connect with other linguists
- **Design feedback**: Share mockups and get input

### Response Times

- **Bug reports**: Acknowledged within 24 hours
- **Feature requests**: Reviewed within 1 week
- **Pull requests**: Initial review within 3 days
- **Questions**: Answered within 2 days

## 🎯 Priority Areas

We especially welcome contributions in these areas:

### High Priority 🔥

- **Translation accuracy**: More phrases, better quality
- **Regional dialects**: Sylheti, Chittagonian, other variants
- **Voice input**: Speech-to-text for Banglish
- **Mobile optimization**: Better mobile user experience
- **Performance**: Faster translation processing
- **Accessibility**: Screen reader and keyboard support

### Medium Priority 📊

- **Browser extension**: Quick translate functionality
- **API documentation**: Better developer experience
- **Offline capabilities**: Enhanced PWA features
- **Animation improvements**: Subtle, meaningful animations
- **Testing coverage**: More comprehensive test suite

### Nice to Have 💫

- **Collaborative features**: User-submitted translations
- **Translation history**: Personal phrasebook
- **Pronunciation guide**: Audio support for translations
- **Handwriting input**: Support for Bengali script
- **Advanced analytics**: Privacy-preserving usage insights

## 📚 Resources

### Documentation
- [Architecture Overview](./ARCHITECTURE.md) - System design
- [Security Policy](./SECURITY.md) - Security considerations
- [Translation Data File](../frontend/src/utils/dhk_align_data_client.json)
- [Translation Engine (JS)](../frontend/src/utils/translation-engine.js)
- [Security Policy](./SECURITY.md)
- [Privacy Policy](./PRIVACY.md)

### Development Tools
- [React Documentation](https://react.dev/) - Frontend framework
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Backend framework
- [Tailwind CSS](https://tailwindcss.com/) - Styling framework
- [Jest Testing](https://jestjs.io/) - Frontend testing

### Bengali Language Resources
- [Bengali Language Overview](https://en.wikipedia.org/wiki/Bengali_language)
- [Banglish Writing System](https://en.wikipedia.org/wiki/Bengali_language#Romanization)
- [Regional Dialects](https://en.wikipedia.org/wiki/Bengali_dialects)

### Design Resources
- [Design System](docs/design-system.md) - UI/UX guidelines
- [Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Mobile Design Principles](https://material.io/design)

## 🙏 Code of Conduct

### Our Commitment

We're committed to providing a welcoming and inclusive environment for all contributors, regardless of:
- Experience level (beginners welcome!)
- Gender identity and expression
- Sexual orientation
- Disability status
- Personal appearance
- Body size
- Race, ethnicity, or nationality
- Religion or belief system
- Age

### Expected Behavior

- **Be respectful**: Treat everyone with kindness and respect
- **Be inclusive**: Welcome newcomers and help them get started
- **Be patient**: Remember that everyone is learning
- **Be constructive**: Provide helpful feedback and suggestions
- **Be collaborative**: Work together towards common goals
- **Give credit**: Acknowledge others' contributions

### Unacceptable Behavior

- Harassment, discrimination, or personal attacks
- Trolling, insulting comments, or inflammatory language
- Public or private harassment
- Publishing others' private information without permission
- Any conduct that could reasonably be considered inappropriate

### Reporting Issues

If you experience or witness unacceptable behavior:
- **Email**: conduct@dhkalign.com
- **Direct contact**: admin@dhkalign.com
- **Anonymous reporting**: [Coming soon]

All reports are handled confidentially and taken seriously.

### Enforcement

Violations may result in:
1. **Warning**: Private message explaining the issue
2. **Temporary ban**: Suspension from project participation
3. **Permanent ban**: Removal from all project spaces

We follow a proportional response based on severity and intent.

## 📈 Contributor Journey

### Getting Started (First Contribution)
1. **Explore**: Browse issues labeled `good-first-issue`
2. **Ask questions**: Don't hesitate to ask for help
3. **Start small**: Fix typos, improve documentation
4. **Learn**: Understand the codebase and architecture

### Regular Contributor
1. **Pick larger issues**: Take on more complex features
2. **Help others**: Answer questions from newcomers
3. **Review code**: Participate in pull request reviews
4. **Shape direction**: Contribute to roadmap discussions

### Core Contributor
1. **Mentor newcomers**: Help onboard new contributors
2. **Lead initiatives**: Drive major features or improvements
3. **Maintain quality**: Help ensure code and translation quality
4. **Represent community**: Speak at events or write blog posts

### Maintainer
- **Commit access**: Direct push access to repository
- **Release management**: Help coordinate releases
- **Community leadership**: Guide project direction
- **Long-term vision**: Shape the future of DHK Align

## 🎉 Special Recognition

### Translation Heroes
Contributors who add 50+ translations or significantly improve accuracy:
- Special badge on GitHub profile
- Listed as "Translation Hero" on website
- Early access to new translation features

### Code Champions
Developers who make significant technical contributions:
- Recognition in release notes
- Invitation to technical architecture discussions
- Opportunity to lead major initiatives

### Community Builders
People who help grow and support the community:
- Special community role and privileges
- Opportunity to moderate discussions
- Input on community guidelines and events

> Optional: A CODEOWNERS file may route reviews (e.g., `engine/` → core maintainer).

<div align="center">
  <h3>Thank you for contributing! 🎉</h3>
  <p>Together we're making translation accessible for millions of Bengali speakers worldwide</p>
  <p>
    <a href="mailto:info@dhkalign.com">General Questions</a> •
    <a href="mailto:admin@dhkalign.com">Technical Support</a> •
    <a href="https://github.com/sartu01/dhkalign/discussions">Community Discussions</a>
  </p>
</div>