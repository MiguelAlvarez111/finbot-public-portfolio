# 🤖 FinBot AI — El asistente financiero que no necesita tu disciplina (porque ya la perdimos todos)

> 🇬🇧 **TL;DR (English)**  
> FinBot is a multimodal personal finance Telegram bot built with Python, PostgreSQL and Google Gemini 2.5 Flash.  
> Users can record transactions via text, audio, or images, and ask natural-language questions that are translated into safe, read-only SQL analytics.

💼 **Highlights for reviewers**

- **Multimodal input**: text, voice, and receipt images, all funneled into structured transactions.
- **Natural language → SQL → interpreted answer** flow with safety checks.
- **Layered architecture**: bot handlers, services, DB layer, web dashboard.
- **Production-friendly setup**: Docker, Alembic migrations, webhook-based Telegram bot, JWT-protected dashboard.

---

Bienvenido a FinBot, un experimento serio en cómo usar IA para organizar la vida financiera de gente normal que no quiere abrir Excel cada vez que compra una empanada.

Construido con cariño, Python, PostgreSQL y Google Gemini 2.5 Flash — porque si ya existe multimodalidad, ¿por qué no usarla para dejar de ser pobres?

## 🚀 ¿Qué hace FinBot? (sin humo técnico)

FinBot convierte cualquier cosa que le envíes en una transacción financiera:

### Texto natural:
→ "Gasté 50 lucas en comida ayer."

✔ Entiende. ✔ Categoriza. ✔ Guarda.

### Audios:
→ Tú hablando mientras caminas o estás apurado.

✔ Transcribe. ✔ Interpreta. ✔ Registra.

### Fotos de facturas:
→ Le tiras una foto borrosa del Éxito.

✔ Extrae valores. ✔ Identifica categoría. ✔ Lista para reportes.

### Además:
- **Metas de ahorro** (sin motivación tóxica).
- **Presupuestos mensuales** (del tipo "no te gastes todo en Rappi, por favor").
- **Gráficos y reportes** (pandas + matplotlib).
- **Exportación a Excel** para los contadores del alma.
- **Dashboard web** en Flask.
- **Arquitectura sólida** con SQLAlchemy + Alembic + Docker.

## 🧠 Tecnologías usadas

### Backend/AI:
- Python 3.12
- Google Gemini 2.5 Flash
- python-telegram-bot (Webhooks)
- SQLAlchemy
- Alembic
- Pillow
- pandas & matplotlib

### Infraestructura:
- PostgreSQL
- Docker
- Webhooks en producción

### Frontend (light):
- Flask dashboard (modo minimalista, sin promesas)

## ⚙️ Cómo correrlo

### 1. Clonar repo
```bash
git clone <repository-url>
cd finbot-public-portfolio
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar .env
```bash
TELEGRAM_TOKEN=tu_token
DATABASE_URL=postgresql://usuario:password@localhost/finbot
GEMINI_API_KEY=tu_api_key
WEBHOOK_URL=https://tu-dominio.com
SECRET_KEY=clave_flask
```

### 4. Migraciones
```bash
alembic upgrade head
```

### 5. Iniciar
```bash
python main.py
```

## 🐳 Versión Docker

```bash
docker build -t finbot .
docker run -p 8000:8000 --env-file .env finbot
```

## 📘 Documentación interna

Toda la explicación del proyecto (arquitectura, capas, modelos de datos, flujo multimodal, servicios de IA, etc.) está en:

👉 **[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)**

## 🔍 Código clave para revisar

Si quieres ver lo interesante del código, empieza aquí:

- `bot/services/ai_service.py` → Integración multimodal con Gemini (texto, audio, imagen).
- `bot/services/analytics_service.py` → Preguntas en lenguaje natural → SQL seguro → respuesta amigable.
- `bot/handlers/natural_language.py` → Enrutamiento entre registrar transacciones y responder consultas.
- `dashboard.py` + `templates/dashboard.html` → Dashboard web con Flask + JWT.
- `models.py` + `migrations/` → Modelo de datos y migraciones con SQLAlchemy + Alembic.

## 🛡️ Licencia / Disclaimer

Este repo es la versión pública y sanitizada del proyecto real.

Prompts privados, seguridad avanzada y lógica sensible han sido removidos o reemplazados con placeholders.

🔒 **Para más detalles sobre qué se sanitizó exactamente:** ver [`PUBLIC_REPO_NOTICE.md`](PUBLIC_REPO_NOTICE.md).

## 🤝 ¿Por qué existe FinBot?

Porque la mayoría de apps de finanzas:

- Te hacen tocar 9 botones para registrar un gasto.
- Te piden disciplina que ninguno tenemos.
- Son más aburridas que leer PDF del SAT.

FinBot quiere ser lo contrario: **rápido, natural, cero fricción, IA-first**.

Si puedes hablarle o mandarle una foto, ya estás haciendo finanzas personales.

