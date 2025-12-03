# 🤖 FinBot: Asistente Financiero con IA Multimodal

FinBot es un bot de Telegram para finanzas personales construido con Python, PostgreSQL y **Google Gemini 2.5 Flash**.

## 🚀 Características Principales

* **IA Multimodal:** Registra transacciones hablando (Audio), escribiendo (Texto Natural) o enviando una foto de la factura (Visión/OCR).
    * *Ejemplo:* "Gasté 50 lucas en comida ayer" → Transacción guardada y categorizada.

* **Gestión Completa:** Presupuestos mensuales, Metas de ahorro y Gestión de categorías.

* **Reportes:** Gráficos mensuales y exportación a Excel.

* **Arquitectura Robusta:** SQLAlchemy (ORM), Alembic (Migraciones), Docker y Webhooks.

## 🛠️ Tech Stack

**Python 3.12**, Flask, PostgreSQL, Google Gemini 2.5 Flash

### Principales Dependencias
- `python-telegram-bot[webhooks]` - Framework para bots de Telegram
- `SQLAlchemy` - ORM para gestión de base de datos
- `Alembic` - Sistema de migraciones
- `google-generativeai` - Integración con Gemini AI
- `Pillow` - Procesamiento de imágenes
- `Flask` - Dashboard web
- `pandas` & `matplotlib` - Reportes y gráficos

## 📋 Requisitos

- Python 3.12+
- PostgreSQL
- Token de Telegram Bot
- API Key de Google Gemini

## ⚙️ Configuración

1. Clona el repositorio:
```bash
git clone <repository-url>
cd telegram_finbot
```

2. Instala dependencias:
```bash
pip install -r requirements.txt
```

3. Configura variables de entorno (crea un archivo `.env`):
```bash
TELEGRAM_TOKEN=tu_token_de_telegram
DATABASE_URL=postgresql://usuario:password@localhost/finbot
GEMINI_API_KEY=tu_api_key_de_gemini
WEBHOOK_URL=https://tu-dominio.com
SECRET_KEY=clave_secreta_para_jwt
```

4. Ejecuta migraciones:
```bash
alembic upgrade head
```

5. Inicia el bot:
```bash
python main.py
```

## 🐳 Docker

```bash
docker build -t finbot .
docker run -p 8000:8000 --env-file .env finbot
```

## 📚 Documentación

Para documentación técnica completa, consulta [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).

## 📝 Licencia

[Especificar licencia si aplica]

