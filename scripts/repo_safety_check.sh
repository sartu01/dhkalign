#!/usr/bin/env bash
echo "🔍 Running repo safety check..."

# Check for tracked sensitive files
git ls-files | egrep "(\.env$|logs/|node_modules/|data/|__pycache__|\.DS_Store|\.db$)" && echo "⚠️ Sensitive tracked files found!" || echo "✅ No tracked sensitive files."

# Check for secret-like strings in tracked code
git grep -n -i -E "api[_-]?key|secret|password|token" || echo "✅ No secret-like strings found."
#!/usr/bin/env bash
echo "🔍 Running repo safety check..."

# Check for tracked sensitive files
git ls-files | egrep "(\.env$|logs/|node_modules/|data/|__pycache__|\.DS_Store|\.db$)" && echo "⚠️ Sensitive tracked files found!" || echo "✅ No tracked sensitive files."

# Check for secret-like strings in tracked code
git grep -n -i -E "api[_-]?key|secret|password|token" || echo "✅ No secret-like strings found."
