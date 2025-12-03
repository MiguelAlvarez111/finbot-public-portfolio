# Project Context

## 1. Overview

**FinBot** is a personal finance management Telegram bot that helps users track their income and expenses through natural, conversational interactions. The bot leverages AI to understand free-form text, voice messages, and even photos of receipts, making financial tracking as simple as chatting with a friend.

### Main Goal

The primary goal is to reduce friction in personal finance tracking by allowing users to record transactions using natural language (e.g., "Gasté 20k en comida ayer") instead of filling out forms or navigating complex menus. The bot also provides analytics, budgeting, and goal-setting features to help users understand and improve their financial habits.

### Type of Product

This is a **Telegram bot** with a complementary **web dashboard**. The bot handles all user interactions via Telegram, while the dashboard provides a more detailed view of financial data with charts and tables.

### User Experience

A typical user journey:

1. **Onboarding**: New users go through an interactive setup where they select default expense/income categories and try a demo transaction
2. **Transaction Recording**: Users can record transactions in multiple ways:
   - Text: "Gasté 50 lucas en mercado"
   - Voice: Record a voice message describing the transaction
   - Photo: Send a photo of a receipt/bill for OCR extraction
3. **Analytics**: Users can ask questions in natural language like "¿Cuánto gasté en comida este mes?" and receive AI-powered answers
4. **Management**: Users can create budgets, set savings goals, manage categories, view reports, and export data to Excel

The bot is designed to feel conversational and intelligent, minimizing the need for users to learn specific commands or navigate complex menus.

---

## 2. Main Features

### Transaction Capture (Text, Voice, Images)

**What it does**: Users can record transactions using natural language text, voice messages, or photos of receipts. The AI extracts amount, category, description, and date from any of these inputs.

**Implementation**:
- `bot/handlers/natural_language.py` - Handles text messages and classifies intent (register transaction vs. query analytics)
- `bot/handlers/media_handler.py` - Processes voice messages (speech-to-text) and photos (OCR)
- `bot/services/ai_service.py` - Core AI service using Google Gemini 2.5 Flash for parsing transactions from text, audio, or images

**Key capabilities**:
- Understands Colombian slang ("lucas", "palos", "k" for thousands)
- Handles relative dates ("ayer", "hoy", "antier")
- Automatically categorizes transactions based on context
- Supports both expenses and income

### AI-Assisted Parsing and Categorization

**What it does**: Uses Google Gemini AI to extract structured transaction data (amount, category, description, date) from unstructured input. The AI understands context, monetary expressions, and semantic categorization rules.

**Implementation**:
- `bot/services/ai_service.py` - `AIService.parse_transaction()` method
- Handles three input types: text, image (OCR), and audio (speech-to-text)
- Validates and normalizes AI responses before saving to database

**Key features**:
- Multimodal AI (text, vision, audio)
- Colombian Spanish context awareness
- Automatic category matching from user's available categories
- Date parsing with timezone handling (America/Bogota)

### Natural Language Analytics (Questions → SQL → Answers)

**What it does**: Users can ask questions in natural language about their finances, and the bot generates SQL queries, executes them safely, and interprets results into friendly responses.

**Implementation**:
- `bot/handlers/natural_language.py` - `_handle_query()` function routes analytics questions
- `bot/services/analytics_service.py` - `AnalyticsService.answer_question()` method
- Three-step process: (1) Generate SQL from question, (2) Validate and execute safely, (3) Interpret results with AI

**Key features**:
- Read-only SQL generation (only SELECT queries allowed)
- Multi-layer security (destructive intent detection, SQL validation, user_id filtering)
- Timezone-aware queries (converts UTC to Colombia timezone)
- Friendly responses in Colombian Spanish with proper currency formatting

### Personal Finance Dashboard

**What it does**: Web-based dashboard accessible via Telegram link that shows transaction history, income/expense totals, and balance. Uses JWT tokens for secure authentication.

**Implementation**:
- `dashboard.py` - Flask application with JWT-based authentication
- `templates/dashboard.html` - HTML template for displaying transactions
- Accessible via `/dashboard` command in Telegram, which generates a secure link

**Key features**:
- JWT token authentication (tokens expire for security)
- Transaction list with category, amount, date, description
- Income/expense totals and balance calculation
- Session-based access control

### User Onboarding and Settings

**What it does**: Interactive onboarding flow for new users to set up default categories and try a demo transaction. Comprehensive settings menu for managing preferences, categories, budgets, and account.

**Implementation**:
- `bot/handlers/onboarding.py` - Multi-step conversation handler for new user setup
- `bot/handlers/core.py` - Settings menu handlers and navigation
- `bot/keyboards.py` - Inline keyboard builders for menus

**Key features**:
- Category selection during onboarding
- Demo transaction to show AI capabilities
- Settings menu with sub-menus (categories, budgets, export, stats, etc.)
- Currency selection (defaults to COP - Colombian Peso)
- Account reset functionality

### Category Management

**What it does**: Users can create, rename, and delete custom categories for expenses and income. Default categories are provided but can be customized.

**Implementation**:
- `bot/handlers/categories.py` - Conversation handler for category CRUD operations
- `bot/services/categories.py` - Business logic for category creation and management
- `models.py` - `Category` model with `CategoryType` enum (INCOME/EXPENSE)

**Key features**:
- Default categories created automatically (Comida, Transporte, Casa, etc.)
- Custom category creation
- Category renaming and deletion
- Type enforcement (expense vs. income categories)

### Budget Management

**What it does**: Users can set monthly budgets per category and track spending against those budgets.

**Implementation**:
- `bot/handlers/budgets.py` - Conversation handler for creating and viewing budgets
- `models.py` - `Budget` model with category association and date ranges

**Key features**:
- Budget creation per category
- Date range specification (start_date, end_date)
- Budget viewing and tracking

### Savings Goals

**What it does**: Users can create savings goals with target amounts and deadlines, then contribute to them over time.

**Implementation**:
- `bot/handlers/goals.py` - Conversation handlers for goal creation and contributions
- `models.py` - `Goal` model with target_amount, current_amount, and optional deadline

**Key features**:
- Goal creation with name, target amount, and optional deadline
- Contribution tracking (adds to current_amount)
- Progress tracking

### Reporting and Export

**What it does**: Generates monthly expense reports with pie charts and exports all transaction data to Excel files.

**Implementation**:
- `bot/handlers/reporting.py` - Handlers for monthly reports and Excel export
- Uses `matplotlib` for chart generation
- Uses `pandas` and `openpyxl` for Excel export

**Key features**:
- Monthly expense distribution pie chart
- Excel export with all transaction details
- Category-wise aggregation
- Timezone-aware date filtering

### Transaction Management

**What it does**: Users can view recent transactions, delete transactions, and manually register expenses/income through guided flows.

**Implementation**:
- `bot/handlers/transactions.py` - Handlers for manual transaction entry and viewing
- Conversation handlers for expense/income flows with amount → category → description steps

**Key features**:
- Manual transaction entry (alternative to natural language)
- Recent transactions view
- Transaction deletion
- Category selection from user's available categories

---

## 3. Tech Stack

### Programming Language

**Python 3.10+** (as specified in `Dockerfile`)

### Frameworks and Libraries

**Telegram Bot Framework**:
- `python-telegram-bot[webhooks]==20.8` - Modern async Telegram bot framework
  - Used in: `bot/application.py`, all handler files
  - Supports webhooks for production deployment

**Web Framework**:
- `Flask==3.0.3` - Lightweight web framework for dashboard
  - Used in: `dashboard.py`
  - Handles JWT authentication and session management

**Database ORM and Migrations**:
- `SQLAlchemy==2.0.34` - Modern ORM with async support
  - Used in: `models.py`, `database.py`, all service files
  - Declarative base model pattern
- `Alembic==1.13.2` - Database migration tool
  - Used in: `migrations/` directory
  - Version-controlled schema changes

**AI/LLM Services**:
- `google-generativeai>=0.8.0` - Google Gemini API client
  - Used in: `bot/services/ai_service.py`, `bot/services/analytics_service.py`
  - Model: `gemini-2.5-flash` for fast, cost-effective inference
  - Multimodal capabilities (text, vision, audio)

**Data Processing**:
- `pandas==2.2.3` - Data manipulation for reports and exports
  - Used in: `bot/handlers/reporting.py`
- `matplotlib==3.9.2` - Chart generation for monthly reports
  - Used in: `bot/handlers/reporting.py`
- `openpyxl==3.1.5` - Excel file generation
  - Used in: `bot/handlers/reporting.py`

**Image Processing**:
- `Pillow>=10.0.0` - Image manipulation for receipt OCR
  - Used in: `bot/services/ai_service.py` for processing photo bytes

**Authentication**:
- `PyJWT==2.9.0` - JWT token generation and validation
  - Used in: `dashboard.py` for secure dashboard access

**Utilities**:
- `python-dateutil==2.9.0` - Date parsing and manipulation
- `python-dotenv==1.0.1` - Environment variable management

**Database Driver**:
- `psycopg2-binary==2.9.9` - PostgreSQL adapter
  - Used in: `database.py` for database connections

**Server**:
- `gunicorn==22.0.0` - WSGI HTTP server for production deployment

**Testing**:
- `pytest`, `pytest-mock`, `pytest-asyncio` - Testing framework
  - Used in: `tests/` directory

### Database

**PostgreSQL** (inferred from `psycopg2-binary` dependency and `DATABASE_URL` environment variable)

- Connection configured in `database.py` via `DATABASE_URL` environment variable
- Uses SQLAlchemy ORM for all database operations
- Schema managed via Alembic migrations in `migrations/versions/`

### Deployment

**Docker**:
- `Dockerfile` - Containerizes the application
- Python 3.10 slim base image
- Production-ready setup with environment variables

**Webhooks**:
- Telegram webhook mode (not polling)
- Configured via `WEBHOOK_URL` and `WEBHOOK_PATH` environment variables
- Handles all update types (`Update.ALL_TYPES`)

### Other Tools

- **Alembic** - Database migrations (see `migrations/` directory)
- **Environment Variables** - Configuration via `.env` file (not committed)
- **Logging** - Structured logging throughout the application (see `bot/common.py`)

---

## 4. Architecture & Folder Structure

### High-Level Architecture

The application follows a **layered architecture**:

1. **Telegram Bot Layer** (`bot/application.py`, `bot/handlers/`) - Handles user interactions via Telegram
2. **Services Layer** (`bot/services/`) - Business logic and external integrations (AI, analytics, categories)
3. **Data Access Layer** (`models.py`, `database.py`) - ORM models and database session management
4. **Web Dashboard Layer** (`dashboard.py`, `templates/`) - Flask web application for detailed views
5. **Utilities Layer** (`bot/utils/`) - Shared helper functions

The bot uses **conversation handlers** for multi-step flows (onboarding, transaction entry, category management) and **message handlers** for natural language processing.

### Folder Structure

```
finbot-public-portfolio/
├── bot/                          # Telegram bot application
│   ├── __init__.py               # Bot package initialization
│   ├── application.py            # Main bot application builder and handler registration
│   ├── common.py                 # Shared utilities (logging, error handling)
│   ├── conversation_states.py    # State constants for conversation handlers
│   ├── keyboards.py               # Inline keyboard builders for menus
│   ├── handlers/                 # Telegram message/command handlers
│   │   ├── budgets.py            # Budget creation and viewing
│   │   ├── categories.py         # Category CRUD operations
│   │   ├── core.py               # Settings menu, dashboard, user guide
│   │   ├── goals.py              # Savings goals creation and contributions
│   │   ├── media_handler.py      # Voice messages and photo processing
│   │   ├── natural_language.py   # Text message processing (transactions + analytics)
│   │   ├── onboarding.py         # New user onboarding flow
│   │   ├── reporting.py          # Monthly reports and Excel export
│   │   └── transactions.py        # Manual transaction entry and viewing
│   ├── services/                 # Business logic and external services
│   │   ├── ai_service.py         # Google Gemini integration for transaction parsing
│   │   ├── analytics_service.py  # Natural language to SQL analytics
│   │   └── categories.py         # Category management business logic
│   └── utils/                    # Shared utilities
│       ├── amounts.py            # Currency formatting
│       ├── callback_manager.py   # Callback data encoding/decoding
│       └── time_utils.py         # Timezone conversion utilities
├── migrations/                   # Alembic database migrations
│   ├── env.py                   # Alembic environment configuration
│   ├── script.py.mako           # Migration template
│   └── versions/                # Migration versions
│       └── a418b1819e67_initial_schema.py  # Initial database schema
├── templates/                    # Flask templates
│   └── dashboard.html           # Dashboard HTML template
├── tests/                       # Test suite
│   ├── test_callback_manager.py
│   ├── test_integration_flows.py
│   └── test_main.py
├── database.py                  # Database connection and session management
├── dashboard.py                 # Flask web dashboard application
├── main.py                      # Application entry point (webhook server)
├── models.py                    # SQLAlchemy ORM models
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker container definition
├── alembic.ini                  # Alembic configuration
└── PROJECT_CONTEXT.md           # This file
```

### Key Responsibilities

**`bot/handlers/`** - Telegram handlers for user interactions
- Each file handles a specific domain (budgets, categories, transactions, etc.)
- Uses conversation handlers for multi-step flows
- Message handlers for natural language processing
- Callback query handlers for inline button interactions

**`bot/services/`** - Business logic and external integrations
- `ai_service.py`: Wraps Google Gemini API for transaction parsing (text, image, audio)
- `analytics_service.py`: Natural language to SQL conversion with safety validation
- `categories.py`: Category creation and management logic

**`bot/utils/`** - Shared utilities
- `amounts.py`: Currency formatting (Colombian Peso format)
- `callback_manager.py`: Encodes/decodes callback data for inline buttons
- `time_utils.py`: Timezone conversion (UTC ↔ America/Bogota)

**`migrations/`** - Database schema version control
- Alembic migrations for schema changes
- Initial schema creates: users, categories, transactions, budgets, goals

**`models.py`** - Data models
- SQLAlchemy declarative models
- Defines relationships (User → Categories, Transactions, Budgets, Goals)

**`database.py`** - Database configuration
- Creates SQLAlchemy engine and session factory
- Handles `DATABASE_URL` environment variable parsing
- Connection pooling and session management

**`dashboard.py`** - Web dashboard
- Flask application for web-based transaction viewing
- JWT authentication for secure access
- Renders transaction list with income/expense totals

**`main.py`** - Application entry point
- Initializes database schema
- Configures logging
- Sets up Telegram webhook server
- Runs on configurable port (default 8000)

---

## 5. Data Model

The application uses a **relational database model** with five main entities:

### User

**Purpose**: Represents a Telegram user and stores their preferences.

**Key Fields**:
- `telegram_id` (BigInteger, PK) - Telegram user ID (unique identifier)
- `chat_id` (BigInteger) - Telegram chat ID for sending messages
- `default_currency` (String) - User's preferred currency (default: "COP")
- `is_onboarded` (Boolean) - Whether user has completed onboarding

**Relationships**:
- One-to-many with `Category` (cascade delete)
- One-to-many with `Transaction` (cascade delete)
- One-to-many with `Budget` (cascade delete)
- One-to-many with `Goal` (cascade delete)

**Usage**: Created automatically on first interaction. Stores user preferences and onboarding status.

### Category

**Purpose**: Categorizes transactions as either income or expense. Each user has their own set of categories.

**Key Fields**:
- `id` (Integer, PK) - Auto-incrementing primary key
- `user_id` (BigInteger, FK → users.telegram_id) - Owner of the category
- `name` (String) - Category name (e.g., "Comida", "Transporte")
- `type` (Enum: INCOME/EXPENSE) - Whether category is for income or expenses
- `is_default` (Boolean) - Whether this is a default category (cannot be deleted)

**Relationships**:
- Many-to-one with `User`
- One-to-many with `Transaction` (cascade delete)
- One-to-many with `Budget` (cascade delete)

**Usage**: Categories are used to classify transactions and set budgets. Default categories are created during onboarding, but users can create custom ones.

### Transaction

**Purpose**: Records individual income or expense transactions.

**Key Fields**:
- `id` (Integer, PK) - Auto-incrementing primary key
- `user_id` (BigInteger, FK → users.telegram_id) - Owner of the transaction
- `category_id` (Integer, FK → categories.id) - Category classification
- `amount` (Numeric(10, 2)) - Transaction amount (always positive, type determined by category)
- `transaction_date` (DateTime) - When the transaction occurred (stored in UTC)
- `description` (String, nullable) - Optional description extracted from user input

**Relationships**:
- Many-to-one with `User`
- Many-to-one with `Category`

**Usage**: Core entity for tracking finances. Created via natural language parsing, manual entry, or OCR from photos. Amounts are stored as positive numbers; the category type determines if it's income or expense.

### Budget

**Purpose**: Defines spending limits per category for a specific time period.

**Key Fields**:
- `id` (Integer, PK) - Auto-incrementing primary key
- `user_id` (BigInteger, FK → users.telegram_id) - Owner of the budget
- `category_id` (Integer, FK → categories.id) - Category this budget applies to
- `amount` (Numeric(10, 2)) - Budget limit amount
- `start_date` (Date) - Budget period start
- `end_date` (Date) - Budget period end

**Relationships**:
- Many-to-one with `User`
- Many-to-one with `Category`

**Usage**: Users set monthly budgets per category. The application can compare actual spending (from transactions) against budget limits.

### Goal

**Purpose**: Represents savings goals with target amounts and progress tracking.

**Key Fields**:
- `id` (Integer, PK) - Auto-incrementing primary key
- `user_id` (BigInteger, FK → users.telegram_id) - Owner of the goal
- `name` (String) - Goal name (e.g., "Vacaciones", "Emergencia")
- `target_amount` (Numeric(10, 2)) - Target savings amount
- `current_amount` (Numeric(10, 2)) - Current progress (default: 0)
- `deadline` (Date, nullable) - Optional deadline for the goal

**Relationships**:
- Many-to-one with `User`

**Usage**: Users create savings goals and make contributions over time. The bot tracks progress toward the target amount.

### Design Decisions

- **Cascade Deletes**: When a user is deleted, all their categories, transactions, budgets, and goals are automatically deleted (data privacy)
- **UTC Timestamps**: All `transaction_date` values are stored in UTC and converted to Colombia timezone (America/Bogota) when displayed or queried
- **Positive Amounts**: Transaction amounts are always positive; the category type determines if it's income or expense
- **User-Scoped Categories**: Categories are per-user (not global), allowing customization
- **Default Categories**: Some categories are marked as `is_default=True` and cannot be deleted (e.g., "General", "General Ingreso")

---

## 6. AI & Analytics Layer (Sanitized Overview)

### AI Service Architecture

The application uses **Google Gemini 2.5 Flash** for multimodal AI processing. The AI service is implemented as a singleton pattern (`bot/services/ai_service.py`) to reuse the same model instance across requests.

### Transaction Parsing (Multimodal)

**How it works**:

1. **Input Processing**: The service accepts three input types:
   - Text: Natural language transaction description
   - Image: Photo bytes (typically receipts/bills)
   - Audio: Voice message bytes (OGG format from Telegram)

2. **AI Prompt Construction**: Different prompts are built based on input type:
   - Text prompt: Includes user's categories, date context, and extraction instructions
   - Image prompt: OCR-focused prompt for receipt analysis
   - Audio prompt: Speech-to-text transcription with transaction extraction

3. **AI Response Processing**:
   - Gemini API is called with the appropriate prompt and media
   - Response is parsed as JSON (handles markdown code blocks)
   - Response is validated and normalized:
     - Amount converted to Decimal with 2 decimal places
     - Category ID validated against user's available categories
     - Type validated (expense/income) and matched to category type
     - Date parsed and validated (YYYY-MM-DD format)

4. **Timezone Handling**: Dates are interpreted in Colombia timezone (America/Bogota) context, then stored as UTC in the database.

**Key Features**:
- Understands Colombian monetary slang ("lucas", "palos", "k" for thousands)
- Handles relative dates ("ayer", "hoy", "antier")
- Semantic categorization (matches transaction description to appropriate category)
- Multimodal support (text, vision, audio)

**Files**:
- `bot/services/ai_service.py` - `AIService.parse_transaction()`
- `bot/handlers/natural_language.py` - `_handle_register()` - Uses AI service for text
- `bot/handlers/media_handler.py` - `handle_photo_message()`, `handle_voice_message()` - Uses AI service for media

### Natural Language Analytics (Text-to-SQL)

**How it works**:

1. **Intent Classification**: First, the system classifies whether the user wants to:
   - **REGISTER** a transaction (e.g., "Gasté 20k")
   - **QUERY** financial data (e.g., "¿Cuánto gasté este mes?")

2. **SQL Generation** (for queries):
   - User's question is sent to Gemini with database schema information
   - AI generates a SQL SELECT query based on the question
   - Schema includes: table structures, relationships, timezone conversion rules
   - AI is instructed to only generate SELECT queries (read-only)

3. **SQL Safety Validation**:
   - Query is validated to ensure it starts with SELECT
   - Dangerous keywords are blocked (DROP, DELETE, INSERT, UPDATE, etc.)
   - Multiple statements are prevented (no semicolons)
   - System function calls are blocked
   - User ID filtering is encouraged (though not enforced at SQL level)

4. **Query Execution**:
   - Validated SQL is executed using SQLAlchemy's `text()` function
   - Results are returned as list of dictionaries

5. **Result Interpretation**:
   - Query results are sent back to Gemini for interpretation
   - AI generates a friendly response in Colombian Spanish
   - Currency is formatted in Colombian format (punto for thousands, coma for decimals)
   - Emojis are used when appropriate

**Security Measures**:
- **Multi-layer validation**: Intent classification → SQL generation → SQL validation → Result interpretation
- **Destructive intent detection**: Keywords like "borrar", "eliminar" trigger rejection
- **Read-only enforcement**: Only SELECT queries are allowed
- **User isolation**: All queries should filter by `user_id` (enforced in prompt, validated in code)

**Files**:
- `bot/services/analytics_service.py` - `AnalyticsService.answer_question()`
- `bot/handlers/natural_language.py` - `_handle_query()` - Routes analytics questions

### Prompt Sanitization

**Note**: The actual prompts used in production contain proprietary business logic including:
- Colombian slang and monetary expressions
- Semantic categorization rules
- Timezone handling specifics
- Detailed extraction instructions

For this public portfolio version, prompts are simplified and can be configured via environment variables:
- `AI_TEXT_PROMPT` - Text transaction parsing prompt
- `AI_IMAGE_PROMPT` - Image OCR prompt
- `AI_AUDIO_PROMPT` - Audio transcription prompt

The analytics service prompt is also simplified but maintains the core structure (schema info, safety rules, interpretation guidelines).

---

## 7. Key Design Patterns & Practices

### Conversation Handlers

The bot uses Telegram's `ConversationHandler` pattern for multi-step flows:
- **Onboarding**: Welcome → Demo → Category Selection → Complete
- **Transaction Entry**: Amount → Category → Description (optional)
- **Category Management**: Menu → Action (Add/Rename/Delete) → Input
- **Budget Creation**: Category Selection → Amount Input
- **Goal Creation**: Name Input → Target Amount Input

Each conversation handler has:
- Entry points (commands or callback queries)
- State definitions (what responses are expected at each step)
- Fallback handlers (cancel commands)

### Singleton Services

AI and analytics services use singleton pattern to avoid recreating model instances:
- `get_ai_service()` - Returns singleton `AIService` instance
- `get_analytics_service()` - Returns singleton `AnalyticsService` instance

### Session Management

Database sessions are managed using context managers:
```python
with SessionLocal() as session:
    # Database operations
    session.commit()
```

This ensures proper cleanup and transaction handling.

### Error Handling

- Centralized error logging in `bot/common.py` (`log_error()`)
- Handler-level error handling with user-friendly messages
- AI service errors are caught and converted to user-friendly responses

### Callback Data Management

Inline button callbacks use a structured encoding system (`bot/utils/callback_manager.py`):
- Format: `{type}:{action}:{id}`
- Types: `CATEGORY`, `BUDGETS`, `GOALS`, `SETTINGS`, etc.
- Prevents callback data conflicts and makes debugging easier

### Timezone Handling

All dates are stored in UTC but displayed/queried in Colombia timezone:
- `bot/utils/time_utils.py` - Conversion utilities
- `convert_utc_to_local()` - Converts UTC to America/Bogota
- Used in AI date processing, analytics queries, and report generation

---

## 8. Security Considerations

### Authentication

- **Dashboard**: JWT tokens with expiration for secure web access
- **Telegram**: Uses Telegram's built-in authentication (users are identified by `telegram_id`)

### SQL Injection Prevention

- **Parameterized Queries**: SQLAlchemy ORM prevents SQL injection
- **Analytics Service**: Raw SQL is validated before execution, but user input is never directly interpolated into queries
- **Read-Only Enforcement**: Analytics service only allows SELECT queries

### Data Isolation

- All queries filter by `user_id` to ensure users only see their own data
- Cascade deletes ensure data cleanup when users are removed

### Environment Variables

- Sensitive data (API keys, database URLs, secrets) are stored in environment variables
- `.env` file is not committed to repository (see `.gitignore`)

### Input Validation

- AI responses are validated before saving to database
- Amounts are validated as positive numbers
- Dates are validated and normalized
- Category IDs are validated against user's available categories

---

## 9. Deployment & Configuration

### Environment Variables

Required environment variables:
- `TELEGRAM_TOKEN` - Telegram bot token
- `DATABASE_URL` - PostgreSQL connection string
- `GEMINI_API_KEY` - Google Gemini API key
- `WEBHOOK_URL` - Base URL for Telegram webhooks
- `WEBHOOK_PATH` - Webhook path (default: "telegram-webhook")
- `PORT` - Server port (default: 8000)
- `SECRET_KEY` - Secret key for JWT tokens (dashboard)

Optional environment variables:
- `AI_TEXT_PROMPT` - Custom text parsing prompt
- `AI_IMAGE_PROMPT` - Custom image OCR prompt
- `AI_AUDIO_PROMPT` - Custom audio transcription prompt

### Database Setup

1. Create PostgreSQL database
2. Set `DATABASE_URL` environment variable
3. Run migrations: `alembic upgrade head`

### Deployment

**Docker**:
```bash
docker build -t finbot .
docker run -p 8000:8000 --env-file .env finbot
```

**Manual**:
```bash
pip install -r requirements.txt
alembic upgrade head
python main.py
```

### Webhook Configuration

The bot runs in webhook mode (not polling) for production:
- Webhook URL: `{WEBHOOK_URL}/{WEBHOOK_PATH}`
- Handles all update types
- Drops pending updates on startup

---

## 10. Testing

Test files are located in `tests/`:
- `test_callback_manager.py` - Tests for callback data encoding/decoding
- `test_integration_flows.py` - Integration tests for user flows
- `test_main.py` - Tests for main application setup

Testing framework: `pytest` with async support (`pytest-asyncio`)

---

## 11. Future Enhancements (Potential)

Based on the codebase structure, potential enhancements could include:
- Multi-currency support (currently defaults to COP)
- Budget tracking alerts (notifications when approaching limits)
- Recurring transactions
- Transaction editing (currently only deletion is supported)
- More advanced analytics (trends, predictions)
- Export to other formats (CSV, PDF)
- Mobile app (currently Telegram + web dashboard)

---

## 12. Notes for Portfolio Reviewers

This is a **sanitized public portfolio version** of the project. Some proprietary elements have been removed or simplified:

1. **AI Prompts**: Full prompts containing business logic, Colombian slang patterns, and semantic rules are replaced with generic versions configurable via environment variables.

2. **Analytics Prompts**: The full Text-to-SQL prompt with detailed schema information and security rules is simplified but maintains core functionality.

3. **Configuration**: Sensitive configuration (API keys, database URLs) is not included. See environment variables section for required setup.

4. **Documentation**: Some internal documentation files (e.g., `AUDITORIA_TECNICA_COMPLETA.md`, `FEATURES_RESTORED.md`) may contain references to proprietary processes but are included for context.

The core architecture, data model, and feature set are accurately represented. The codebase demonstrates:
- Modern Python async patterns
- Clean separation of concerns
- Robust error handling
- Security-conscious design
- Multimodal AI integration
- Production-ready deployment setup
