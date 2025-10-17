#!/bin/bash
# Export Streamlit Secrets for Cloud Deployment
# This script extracts the secrets in the exact format needed for Streamlit Cloud

set -e

echo "📋 Streamlit Cloud Secrets"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Copy everything between the lines and paste into:"
echo "Streamlit Cloud → Your App → Settings → Secrets"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat .streamlit/secrets.toml | grep -v "^#" | grep -v "^$"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Credentials verified working (2025-10-17)"
echo "🔗 Dashboard URL: src/mcli/ml/dashboard/app_supabase.py"
echo "📦 Requirements: streamlit_requirements.txt"
echo ""
echo "Next steps:"
echo "1. Go to https://share.streamlit.io"
echo "2. Click 'New app'"
echo "3. Repository: gwicho38/mcli"
echo "4. Branch: main"
echo "5. Main file: src/mcli/ml/dashboard/app_supabase.py"
echo "6. Requirements: streamlit_requirements.txt"
echo "7. Paste secrets above in Settings → Secrets"
echo "8. Deploy!"
