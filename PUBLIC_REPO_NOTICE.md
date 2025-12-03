# ⚠️ Public Repository Notice

This is a **sanitized version** of the FinBot AI 2.0 repository prepared for portfolio purposes.

## What Was Removed/Sanitized

1. **Credential Files**: `.env`, `google_credentials.json`, database files
2. **Production Scripts**: `scripts/seed_prod_direct.py` (contains production credentials)
3. **AI Prompts**: Proprietary prompts in `bot/services/ai_service.py` and `bot/services/analytics_service.py` have been replaced with generic versions or environment variable placeholders.

## Proprietary Content

The following proprietary content has been redacted:
- **Colombian slang and monetary expressions** ("k", "lucas", "barras", "palos")
- **Semantic categorization rules** for transactions
- **Detailed security guardrails** for SQL generation
- **Timezone handling logic** specific to Colombia
- **Complete AI prompts** for OCR, STT, and text parsing

## Setup

1. Copy `.env.example` to `.env` and fill in your credentials
2. Install dependencies: `pip install -r requirements.txt`
3. Set up database and run migrations: `alembic upgrade head`
4. Run the bot: `python main.py`

## Note

The actual production prompts and business logic are kept in a private repository. This public version demonstrates the architecture, patterns, and structure of the project.
