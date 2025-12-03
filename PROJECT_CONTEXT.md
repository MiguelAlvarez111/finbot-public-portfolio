# PROJECT_CONTEXT.md

**Fuente Única de Verdad** - Documentación Técnica Completa de FinBot AI 2.0

---

## 🎯 Visión Ejecutiva (5 minutos)

**FinBot AI 2.0** es un bot de Telegram para gestión de finanzas personales con arquitectura **AI-First y Multimodal**. Los usuarios pueden registrar transacciones mediante **texto natural, voz o fotos de facturas**, y hacer **consultas analíticas en lenguaje natural** sobre sus finanzas.

### Identidad del Sistema
- **Nombre**: FinBot AI 2.0 (Multimodal)
- **Arquitectura**: AI-First con procesamiento multimodal nativo
- **Motor de IA**: Google Gemini 2.5 Flash (`google-generativeai>=0.8.0`)
- **Base de Datos**: PostgreSQL con Alembic para migraciones
- **Estado**: Producción/Staging - Desplegado y funcional

### Capacidades Principales
1. **Registro Multimodal**: Texto, voz (STT) y fotos (OCR) usando IA
2. **Análisis Inteligente**: Text-to-SQL seguro para consultas financieras
3. **Gestión Financiera**: Presupuestos, metas, categorías, reportes
4. **Dashboard Web**: Visualización temporal con métricas avanzadas

---

## 🏗️ Arquitectura del Sistema

### Stack Tecnológico

#### Core
- **Python**: 3.12.6
- **Framework Bot**: `python-telegram-bot[webhooks]==20.8`
- **Base de Datos**: PostgreSQL (`psycopg2-binary==2.9.9`)
- **ORM**: SQLAlchemy 2.0.34
- **Migraciones**: Alembic 1.13.2

#### IA y Multimodal
- **Motor de IA**: `google-generativeai>=0.8.0` (Gemini 2.5 Flash)
- **Procesamiento de Imágenes**: `Pillow>=10.0.0`
- **Procesamiento Nativo**: Gemini procesa imágenes (JPEG/PNG) y audio (OGG) directamente, sin librerías intermedias de OCR/STT

#### Web y Reportes
- **Framework Web**: Flask 3.0.3
- **Servidor WSGI**: gunicorn 22.0.0
- **Análisis de Datos**: pandas 2.2.3
- **Visualización**: matplotlib 3.9.2
- **Exportación**: openpyxl 3.1.5

#### Utilidades
- **Autenticación**: PyJWT 2.9.0
- **Fechas**: python-dateutil 2.9.0
- **Configuración**: python-dotenv 1.0.1
- **Testing**: pytest, pytest-mock, pytest-asyncio

### Estructura de Directorios

```
telegram_finbot/
├── bot/                          # Módulo principal del bot
│   ├── application.py           # ⭐ CORAZÓN: Builder de aplicación y registro de handlers
│   ├── common.py                # Utilidades compartidas (logging, debug)
│   ├── conversation_states.py  # Constantes de estados para ConversationHandlers
│   ├── keyboards.py             # Factories de teclados inline y reply
│   ├── handlers/                # Handlers de comandos y callbacks
│   │   ├── core.py             # Dashboard, settings, guía de usuario
│   │   ├── transactions.py     # Flujos de registro de gastos/ingresos
│   │   ├── categories.py        # Gestión de categorías (CRUD)
│   │   ├── budgets.py          # Creación y visualización de presupuestos
│   │   ├── goals.py            # Creación y aportes a metas
│   │   ├── reporting.py        # Reportes mensuales y exportación Excel
│   │   ├── onboarding.py       # Flujo de bienvenida para nuevos usuarios
│   │   ├── natural_language.py # ⭐ Router Inteligente: Clasificación REGISTER/QUERY y procesamiento de texto
│   │   └── media_handler.py    # ⭐ Procesamiento multimodal: Fotos (OCR) y voz (STT)
│   ├── services/               # ⭐ Servicios de IA y lógica de negocio
│   │   ├── ai_service.py       # ⭐ Cliente Gemini Multimodal: Parsing de transacciones y transcripción
│   │   ├── analytics_service.py # ⭐ Analista SQL: Text-to-SQL seguro para consultas financieras
│   │   └── categories.py       # Helpers para gestión de categorías
│   └── utils/                  # Utilidades generales
│       ├── amounts.py          # Parsing y formateo de montos monetarios
│       ├── callback_manager.py # Sistema robusto para manejo de callback_data (validación 64 bytes)
│       └── time_utils.py       # ⭐ Utilidades de timezone (UTC-aware, conversión a America/Bogota)
├── migrations/                  # Migraciones de base de datos (Alembic)
├── database.py                 # Configuración SQLAlchemy (engine, session, Base)
├── models.py                   # ⭐ CORAZÓN: Modelos ORM (User, Category, Transaction, Budget, Goal)
├── main.py                     # ⭐ ENTRY POINT: Inicialización y arranque del webhook
├── dashboard.py                # Aplicación Flask para dashboard web
└── requirements.txt            # Dependencias Python
```

### Componentes Clave de la Arquitectura

#### 1. **Router de Lenguaje Natural** (`bot/handlers/natural_language.py`)
- **Función**: Clasifica intenciones (REGISTER vs QUERY) y enruta al handler apropiado
- **Clasificación**: Usa Gemini 2.5 Flash para determinar si el usuario quiere registrar una transacción o consultar datos
- **Unificación**: Compartido entre texto y voz (después de transcripción)

#### 2. **Servicio de IA Multimodal** (`bot/services/ai_service.py`)
- **Clase**: `AIService` (singleton)
- **Capacidades**:
  - **Parsing de Transacciones**: Extrae monto, categoría, descripción, tipo y fecha desde texto, imagen o audio
  - **Transcripción de Audio**: Convierte notas de voz a texto literal (sin interpretación)
- **Modelo**: Gemini 2.5 Flash con procesamiento nativo de imágenes y audio
- **Prompts Especializados**: Jerga colombiana, fechas relativas, categorización semántica

#### 3. **Analista SQL** (`bot/services/analytics_service.py`)
- **Clase**: `AnalyticsService` (singleton)
- **Arquitectura Segura**: Text-to-SQL con múltiples capas de seguridad
- **Flujo**:
  1. Generación SQL con Gemini (solo SELECT)
  2. Validación estricta de seguridad
  3. Ejecución en modo lectura
  4. Interpretación de resultados con IA
- **Guardrails**: 5 capas de protección contra intenciones destructivas

#### 4. **Procesador Multimodal** (`bot/handlers/media_handler.py`)
- **Fotos**: OCR automático de facturas/recibos usando visión de Gemini
- **Voz**: Transcripción a texto y reutilización de lógica de texto
- **UX**: ChatActions para mitigar percepción de latencia

---

## 🎨 Patrones de Diseño

### 1. **Global Menu Priority** (Prioridad Global del Menú)
**Ubicación**: `bot/application.py:351-356`

Los botones del menú principal se registran **ANTES** de los ConversationHandlers para que actúen como "comandos globales" que cancelan cualquier flujo activo.

```python
# CRÍTICO: Handlers de botones del menú principal DEBEN estar ANTES
application.add_handler(MessageHandler(filters.Regex(r"^📈 Dashboard$"), dashboard))
application.add_handler(MessageHandler(filters.Regex(r"^📊 Reporte$"), monthly_report))
application.add_handler(MessageHandler(filters.Regex(r"^🎯 Metas$"), goals_menu))
application.add_handler(MessageHandler(filters.Regex(r"^⚙️ Ajustes$"), settings_menu))
# Luego ConversationHandlers
```

**Comportamiento Crítico**: Los botones del menú interrumpen y cancelan cualquier flujo activo (`ConversationHandler`). Esto significa que si un usuario está en medio de un flujo de registro de transacción, presupuesto o cualquier otro `ConversationHandler`, presionar cualquier botón del menú principal (📊 Reporte, 📈 Dashboard, 🎯 Metas, ⚙️ Ajustes) cancelará inmediatamente ese flujo y ejecutará la acción del botón.

**Regla UX de Limpieza de Contexto**:
- **Para flujos cortos**: Se limpia el `context.user_data` al cancelar (reset completo)
- **Para flujos largos (onboarding)**: Se evalúa si guardar progreso antes de cancelar, o permitir reanudar desde el último punto guardado

**Beneficio**: Los usuarios pueden cancelar flujos activos presionando cualquier botón del menú principal, proporcionando una forma intuitiva de "escapar" de cualquier flujo conversacional.

### 2. **Invisible UI / AI-First** (UI Invisible / IA Primero)
**Filosofía**: Menos botones, más chat natural. La interfaz visual se minimiza para priorizar la interacción por lenguaje natural.

**Características**:
- Los usuarios pueden escribir libremente: "Gaste 20k en comida"
- El bot clasifica automáticamente la intención
- No requiere navegar por menús para tareas comunes
- El menú principal tiene solo 4 botones esenciales: Reporte, Dashboard, Metas, Ajustes
- Los comandos de registro (`/gasto`, `/ingreso`) existen pero están "ocultos" (no aparecen en el menú)
- El onboarding enseña a usar lenguaje natural desde el inicio
- Los botones son atajos opcionales, no requisitos

**Ubicación**: `bot/keyboards.py:118-121`, `bot/handlers/onboarding.py:38-46`

**Beneficio**: Reduce la fricción cognitiva y promueve una experiencia más conversacional y natural.

### 3. **Speech-to-Text Pipeline Unificado**
**Flujo**: Voz → Transcripción → Router Inteligente → Registro/Consulta

1. Usuario envía nota de voz
2. `AIService.transcribe_audio()` convierte a texto literal
3. `process_user_text_input()` procesa el texto (misma lógica que texto)
4. Router clasifica y enruta a registro o consulta

**Beneficio**: Las notas de voz funcionan tanto para registro como para consultas analíticas.

### 4. **Service Layer Pattern**
- `AIService`: Encapsula interacción con Gemini (multimodal)
- `AnalyticsService`: Encapsula generación SQL segura y análisis
- `categories.py`: Lógica de negocio reutilizable para categorías

### 5. **State Machine Pattern**
- `conversation_states.py`: Define estados para `ConversationHandler`
- Permite flujos conversacionales guiados (onboarding, transacciones, presupuestos)

### 6. **Robust Callback Handling Pattern**
- `CallbackManager`: Generación y parsing seguro de `callback_data`
- Validación automática de límite de 64 bytes de Telegram
- Prefijos cortos para ahorrar bytes

### 7. **Educational Error Handling** (Manejo Educativo de Errores)
**Filosofía**: Los errores no solo informan, sino que enseñan al usuario cómo usar la IA.

**Implementación**:
- Cuando el usuario usa comandos legacy (`/gasto`, `/ingreso`), después de completar la transacción se muestra un "Tip" educativo:
  - `"💡 **Tip:** La próxima vez no necesitas comandos. Solo escríbeme 'Gaste 50k' y yo hago el resto."`
- Los mensajes de error incluyen ejemplos de uso correcto:
  - `"😅 No entendí bien ese gasto.\n\nIntenta así:\n• _'Gaste 20k en taxi'_\n• _'Recibí 500k de nómina'_"`

**Ubicación**: `bot/handlers/transactions.py:252, 327, 414, 472`, `bot/handlers/natural_language.py:257-263`

**Beneficio**: Los usuarios aprenden progresivamente a usar el bot de forma más natural, migrando de comandos a lenguaje natural.

### 8. **Modo Degradado (AI Fallback)**
**Filosofía**: Si los servicios de IA fallan, el bot debe degradarse elegantemente sin bloquear al usuario.

**Implementación**:
- Detección de fallos repetidos (3+ intentos fallidos en < 1 minuto)
- Informar al usuario: "⚠️ Mi motor de IA tiene problemas"
- Habilitar/sugerir explícitamente los flujos manuales (`/gasto`, `/ingreso`) como respaldo temporal
- Desactivar funcionalidades avanzadas (lenguaje natural, OCR, STT) mientras se mantienen activos los comandos manuales

**Ubicación**: `bot/services/ai_service.py`, `bot/application.py`

**Beneficio**: El usuario nunca queda completamente bloqueado. Siempre hay una forma de registrar transacciones, aunque sea menos elegante.

---

## 🔐 Reglas de Oro (Golden Rules)

### 1. **Timezones: Conversión Explícita a `America/Bogota`**

#### En SQL (Queries Analíticas)
**SIEMPRE** convertir `transaction_date` a hora Colombia antes de comparar:

```sql
WHERE (transaction_date AT TIME ZONE 'UTC' AT TIME ZONE 'America/Bogota')::date = '2025-12-02'
```

**Razón**: Previene problemas donde después de las 7 PM en Colombia el bot busca gastos del día siguiente.

**Ubicación**: `bot/services/analytics_service.py:189-193`

#### En Python (Procesamiento de Fechas)
- **Almacenamiento**: Todas las fechas en UTC (timezone-aware)
- **Contexto de IA**: Convertir a hora Colombia antes de pasarla a prompts
- **Fechas de "hoy"**: Usar hora exacta UTC para preservar orden cronológico
- **Otras fechas**: Usar mediodía UTC para evitar problemas de timezone

**Ubicación**: `bot/utils/time_utils.py`, `bot/handlers/natural_language.py:24-78`

### 2. **Seguridad: Guardrails Anti-Borrado y Validación de Solo SELECT**

#### Múltiples Capas de Protección
1. **Detección Temprana**: `_has_destructive_intent()` filtra palabras clave destructivas
2. **Prompt Read-Only**: Reglas explícitas en prompt para evitar alucinación de acciones
3. **Validación SQL**: Solo SELECT permitido, sin palabras peligrosas
4. **Verificación de Resultados**: Detección de `ACTION_NOT_ALLOWED` en resultados
5. **Respuesta Consistente**: Mensaje de rechazo predefinido

**Ubicación**: `bot/services/analytics_service.py:113-129, 322-362`

#### Validación de SQL
```python
# Debe empezar con SELECT
# No contiene: DROP, DELETE, INSERT, UPDATE, TRUNCATE, etc.
# No contiene punto y coma (múltiples queries)
# No contiene funciones del sistema PostgreSQL peligrosas
```

### 3. **UX: Uso de `ChatAction` para Latencia**

Las operaciones de IA pueden tomar 7-14 segundos. Los indicadores visuales reducen la ansiedad del usuario.

**Implementación**:
- `ChatAction.TYPING`: Para procesamiento de texto y consultas
- `ChatAction.UPLOAD_PHOTO`: Para procesamiento de fotos
- `ChatAction.RECORD_VOICE`: Para procesamiento de voz

**Ubicación**: 
- `bot/handlers/natural_language.py:171, 349`
- `bot/handlers/media_handler.py:50, 195`

### 4. **ENUMs en SQL: Valores en MAYÚSCULAS**

PostgreSQL requiere valores exactos del enum. En prompts SQL, especificar explícitamente:
- `'EXPENSE'` y `'INCOME'` (MAYÚSCULAS)
- **NUNCA** usar minúsculas (`'expense'`, `'income'`)

**Ubicación**: `bot/services/analytics_service.py:170, 221`

### 5. **Lógica Unificada: Texto y Voz Comparten Procesamiento**

El manejo de voz reutiliza la lógica de texto para permitir consultas verbales. No solo registra transacciones.

**Flujo**:
1. Voz → Transcripción (`AIService.transcribe_audio()`)
2. Texto transcrito → `process_user_text_input()`
3. Router clasifica → Registro o Consulta

**Ubicación**: `bot/handlers/media_handler.py:166-234`, `bot/handlers/natural_language.py:134-194`

### 6. **Modo Degradado (AI Fallback)**

Si los servicios de IA (Gemini) fallan repetidamente, el bot debe informar al usuario (`'⚠️ Mi motor de IA tiene problemas'`) y habilitar/sugerir explícitamente los flujos manuales (`/gasto`) como respaldo temporal.

**Implementación**:
- Detección de fallos repetidos (3+ intentos fallidos en < 1 minuto)
- Mensaje informativo al usuario sobre el problema
- Sugerencia explícita de usar comandos manuales como alternativa temporal
- Desactivación temporal de funcionalidades avanzadas (lenguaje natural, OCR, STT)

**Ubicación**: `bot/services/ai_service.py`, `bot/application.py`

**Beneficio**: El usuario nunca queda completamente bloqueado. Siempre hay una forma de registrar transacciones, aunque sea menos elegante.

---

## 🔄 Flujos Principales

### Flujo 1: Onboarding de Nuevo Usuario (Show, Don't Tell)

**Arquitectura**: Bienvenida → Demo Interactiva → Selección de Categorías → Menú Principal

**Filosofía**: "Show, Don't Tell" - El usuario aprende haciendo, no solo leyendo.

1. **Bienvenida** (`onboarding_start()`):
   - Usuario envía `/start` → `onboarding_start()`
   - Si `user.is_onboarded == False`:
     - Mensaje de bienvenida personalizado
     - Presenta opción: "🧪 Probar Demo" o "⚙️ Configurar"

2. **Demo Interactiva** (`onboarding_demo_handler()`, `onboarding_demo_process()`):
   - Si elige "Probar Demo":
     - Se le pide que escriba o envíe un audio: `"Gaste 20k en almuerzo ayer"`
     - El bot procesa la transacción en tiempo real usando IA
     - Muestra el resultado completo: monto, categoría, fecha, descripción
     - Mensaje: `"¡Así de fácil es! Ahora configuremos tus categorías reales..."`
   - Si elige "Configurar":
     - Salta directamente a selección de categorías
   
   **Casos Borde**:
   - **Timeout de Demo**: Si el usuario no interactúa en la Demo (timeout), el bot sugiere suavemente continuar a la configuración.
   - **Fallo de IA en Primera Interacción**: Si la IA falla en la primera interacción de la Demo, el bot responde con un mensaje de apoyo guiado y ofrece saltar a configuración para no frustrar la primera impresión.

3. **Selección de Categorías** (`onboarding_category_choice()`):
   - Presenta categorías sugeridas con toggle (✅/⬜️)
   - Usuario activa/desactiva las que desea
   - Categorías bloqueadas ("General", "General Ingreso") no se pueden desmarcar
   - Opción de agregar categorías personalizadas

4. **Finalización** (`onboarding_finish()`):
   - Crea usuario si no existe
   - Crea categorías seleccionadas
   - Marca `user.is_onboarded = True`
   - Muestra mensaje educativo sobre uso de lenguaje natural
   - Muestra menú principal con 4 botones

**Archivos**: `bot/handlers/onboarding.py`, `bot/services/categories.py`

**Beneficio**: El usuario experimenta el poder de la IA antes de configurar, generando confianza y entendimiento inmediato.

### Flujo 2: Registro Multimodal Unificado

**Arquitectura**: Entrada (Texto/Voz/Foto) → Normalización → Router → IA → BD

#### Modo Texto
1. Usuario envía: "Gaste 20k en comida ayer"
2. `handle_text_message()` → `process_user_text_input()`
3. Router clasifica: `_classify_intent()` → "register"
4. `_handle_register()` → `AIService.parse_transaction()`
5. Gemini extrae: monto, categoría, descripción, tipo, fecha
6. Procesamiento de fecha con timezone Colombia
7. Creación de `Transaction` en BD

#### Modo Foto (OCR)
1. Usuario envía foto de factura
2. `handle_photo_message()` descarga foto
3. `AIService.parse_transaction()` con `image_data`
4. Gemini procesa imagen nativamente (visión)
5. Extrae: monto total, comercio, categoría, fecha
6. Creación de `Transaction` en BD

#### Modo Voz (STT Unificado)
1. Usuario envía nota de voz
2. `handle_voice_message()` descarga audio
3. `AIService.transcribe_audio()` → texto literal
4. `process_user_text_input()` con texto transcrito
5. Router clasifica → Registro o Consulta
6. Misma lógica que texto

**Archivos**: `bot/handlers/natural_language.py`, `bot/handlers/media_handler.py`, `bot/services/ai_service.py`

### Flujo 3: Análisis Inteligente (Text-to-SQL Seguro)

**Arquitectura**: Pregunta → Generación SQL → Validación → Ejecución → Interpretación

1. Usuario pregunta: "¿Cuánto gasté en comida este mes?"
2. Router clasifica: "query"
3. `_handle_query()` → `AnalyticsService.answer_question()`
4. **Paso A - Generación SQL**:
   - Construye prompt con esquema de BD, fecha Colombia, reglas de seguridad
   - Gemini genera SQL (solo SELECT)
5. **Paso B - Validación y Ejecución**:
   - Valida seguridad (solo SELECT, sin palabras peligrosas)
   - Ejecuta query con conversión explícita de timezone
   - Retorna resultados
6. **Paso C - Interpretación**:
   - Gemini interpreta resultados numéricos
   - Genera respuesta amigable en jerga colombiana

**Archivos**: `bot/services/analytics_service.py`, `bot/handlers/natural_language.py:330-375`

### Flujo 4: Registro de Gasto/Ingreso (Flujo Guiado)

1. Usuario presiona "💸 Registrar Gasto" o `/gasto`
2. Estado `EXPENSE_AMOUNT`: Usuario ingresa monto
3. Estado `EXPENSE_CATEGORY`: Muestra categorías
4. Estado `EXPENSE_DESCRIPTION_DECISION`: Pregunta por descripción (opcional)
5. Crea `Transaction` en BD
6. Muestra "Tip" educativo: `"💡 **Tip:** La próxima vez no necesitas comandos. Solo escríbeme 'Gaste 50k' y yo hago el resto."`

**Archivos**: `bot/handlers/transactions.py`

### Flujo 5: Multimodal Unificado (Texto y Voz Comparten Lógica)

**Arquitectura Unificada**: Texto y Voz comparten la misma lógica de decisión.

**Confirmación Técnica**:
- **Texto**: `handle_text_message()` → `process_user_text_input()`
- **Voz**: `handle_voice_message()` → `AIService.transcribe_audio()` → `process_user_text_input()`

**Función Central**: `process_user_text_input()` (`bot/handlers/natural_language.py:134-194`)
- Clasifica intención: `_classify_intent()` → "register" o "query"
- Enruta a: `_handle_register()` o `_handle_query()`
- Compartida entre texto y voz (después de transcripción)

**Beneficio**: Consistencia total entre modos de entrada. Las notas de voz funcionan tanto para registro como para consultas analíticas.

**Archivos**: `bot/handlers/natural_language.py:134-194`, `bot/handlers/media_handler.py:181-234`

---

## 📊 Modelos de Datos

### Esquema de Base de Datos

#### `users`
- `telegram_id` (PK, BigInteger)
- `chat_id` (BigInteger)
- `default_currency` (String, default="COP")
- `is_onboarded` (Boolean, default=False)

#### `categories`
- `id` (PK, Integer)
- `user_id` (FK -> users.telegram_id)
- `name` (String)
- `type` (Enum: 'INCOME' | 'EXPENSE')
- `is_default` (Boolean)

#### `transactions`
- `id` (PK, Integer)
- `user_id` (FK -> users.telegram_id)
- `category_id` (FK -> categories.id)
- `amount` (Numeric(10, 2))
- `transaction_date` (DateTime, UTC-aware, default=_get_utc_now)
- `description` (String, nullable)

#### `budgets`
- `id` (PK, Integer)
- `user_id` (FK -> users.telegram_id)
- `category_id` (FK -> categories.id)
- `amount` (Numeric(10, 2))
- `start_date` (Date)
- `end_date` (Date)

#### `goals`
- `id` (PK, Integer)
- `user_id` (FK -> users.telegram_id)
- `name` (String)
- `target_amount` (Numeric(10, 2))
- `current_amount` (Numeric(10, 2), default=0)
- `deadline` (Date, nullable)

**Archivo**: `models.py`

---

## 🛠️ Convenciones y Estándares

### Estilos de Código
- **Type Hints**: Uso extensivo en todas las funciones
- **Naming**: `snake_case` para funciones/variables, `PascalCase` para clases
- **Logging**: Sistema centralizado en `bot/common.py`
- **Async/Await**: Todos los handlers son async
- **Gestión de Sesiones**: `with SessionLocal() as session:` en cada handler

### Callback Data Patterns
- **SIEMPRE usar `CallbackManager`** para generar y parsear
- **Límite**: 64 bytes (validación automática)
- **Prefijos cortos**: `c:{id}` para categorías, `s:{action}` para settings, etc.

### Formato de Montos
- **Entrada**: Acepta `,` o `.` como separador decimal
- **Salida**: Formato colombiano: `$1.500,50` (punto para miles, coma para decimales)
- **Validación**: Debe ser positivo

### Manejo de Fechas y Timezones
- **Almacenamiento**: Siempre UTC (timezone-aware)
- **Función estándar**: `get_now_utc()` de `bot/utils/time_utils.py`
- **Conversión**: `convert_utc_to_local()` para visualización
- **En SQL**: Conversión explícita a `America/Bogota` antes de comparar

---

## ✅ Estado de Deuda Técnica

### ✅ RESUELTO: Manejo de Timezone Inconsistente
- **Estado**: ✅ COMPLETADO
- **Solución**: 
  - Estandarizado a `get_now_utc()` de `bot/utils/time_utils.py`
  - Conversión a hora Colombia para contexto de fechas en prompts
  - Manejo inteligente de fechas: hora exacta para "hoy", mediodía UTC para fechas pasadas
  - Conversión explícita de timezone en queries SQL analíticas
- **Ubicación**: `bot/utils/time_utils.py`, `bot/services/ai_service.py`, `bot/services/analytics_service.py`

### ✅ RESUELTO: Parsing de Callback Data Frágil
- **Estado**: ✅ COMPLETADO
- **Solución**: Implementado `CallbackManager` con validación robusta y parsing tipado
- **Ubicación**: `bot/utils/callback_manager.py`

### ✅ RESUELTO: Falta de Tests
- **Estado**: ✅ COMPLETADO (Parcial)
- **Solución**: 
  - Tests completos para `CallbackManager` (25 tests, todos pasando)
  - Tests de integración con mocking para flujos completos
  - Sistema de seguridad multi-capa en `AnalyticsService` actúa como test lógico
- **Ubicación**: `tests/test_callback_manager.py`, `tests/test_integration_flows.py`

### ⚠️ PENDIENTE: Soporte Multi-Moneda Incompleto
- **Problema**: `User.default_currency` existe pero `format_currency()` siempre muestra `$`
- **Impacto**: Usuarios no pueden usar otras monedas aunque la infraestructura existe

### ⚠️ PENDIENTE: Gamificación No Implementada
- **Problema**: `settings_gamification()` verifica campos que no existen en el modelo `User`
- **Estado**: Muestra mensaje "en desarrollo"

### ⚠️ PENDIENTE: Falta de Índices en Base de Datos
- **Problema**: No hay índices explícitos para consultas frecuentes
- **Impacto**: Consultas pueden ser lentas con muchos registros

---

## 🔧 Variables de Entorno

```bash
TELEGRAM_TOKEN=          # Token del bot de Telegram (obligatorio)
WEBHOOK_URL=             # URL base del webhook (obligatorio)
WEBHOOK_PATH=            # Path del webhook (opcional, default: "telegram-webhook")
PORT=                    # Puerto del servidor (opcional, default: 8000)
DATABASE_URL=            # Connection string de PostgreSQL (obligatorio)
SECRET_KEY=              # Clave secreta para JWT del dashboard (obligatorio)
DASHBOARD_URL=           # URL del dashboard web (opcional)
GEMINI_API_KEY=          # API Key de Google Gemini (obligatorio para funcionalidad de IA)
```

---

## 📝 Comandos del Bot

**Nota de UX**: Estos comandos se documentan con fines técnicos y para 'Power Users'. En la UX general, NO se promueve su uso; el flujo principal es siempre lenguaje natural.

### Menú Principal (4 Botones)

El menú principal se muestra como teclado persistente con 4 botones:

- **📊 Reporte** - Genera reporte mensual con gráfico
- **📈 Dashboard** - Genera enlace temporal al dashboard web
- **🎯 Metas** - Crea o aporta a metas de ahorro
- **⚙️ Ajustes** - Accede a herramientas avanzadas (categorías, presupuestos, exportación, reset)

**Ubicación**: `bot/keyboards.py:118-121`

**Nota**: Los botones del menú principal tienen prioridad global y cancelan cualquier flujo activo (`ConversationHandler`).

### Comandos Principales
- `/start` - Inicia el bot o reinicia onboarding
- `/categorias` - Gestiona categorías
- `/presupuesto` - Configura un presupuesto
- `/ver_presupuesto` - Visualiza presupuestos
- `/crear_meta` - Crea una meta de ahorro
- `/aportar_meta` - Aporta a una meta existente
- `/ultimos` - Muestra últimas 5 transacciones
- `/reporte_mes` - Genera reporte mensual con gráfico
- `/exportar` - Exporta transacciones a Excel
- `/dashboard` - Genera enlace temporal al dashboard web
- `/guia` o `/help` - Muestra guía de usuario

### Comandos Legacy (Ocultos con Mensajes Educativos)

Los siguientes comandos existen pero están "ocultos" (no aparecen en el menú principal). Cuando el usuario los usa, después de completar la transacción se muestra un mensaje educativo ("Tip") que enseña a usar lenguaje natural:

- **`/gasto`** - Registra un gasto (flujo guiado)
  - Después de completar: `"💡 **Tip:** La próxima vez no necesitas comandos. Solo escríbeme 'Gaste 50k' y yo hago el resto."`
  
- **`/ingreso`** - Registra un ingreso (flujo guiado)
  - Después de completar: `"💡 **Tip:** La próxima vez no necesitas comandos. Solo escríbeme 'Recibí 500k' y yo hago el resto."`

**Ubicación**: `bot/handlers/transactions.py:252, 327, 414, 472`

**Filosofía**: Los comandos legacy actúan como "puente educativo" para migrar usuarios de comandos a lenguaje natural.

### Entradas Multimodales
- **Texto Natural**: "Gaste 20k en comida" o "¿Cuánto gasté hoy?"
- **Imágenes**: Fotos de facturas/recibos para OCR automático
- **Audio**: Notas de voz describiendo gastos o haciendo preguntas
- **Consultas Analíticas**: "¿Cuánto gasté en comida este mes?", "¿Cuál fue mi mayor gasto?"

---

## 🧪 Testing

### Estrategia de QA

El proyecto utiliza una estrategia de testing híbrida que combina tests unitarios y tests de integración con mocking completo.

#### Tests de Integración con Mocking

**Archivo**: `tests/test_integration_flows.py`

**Filosofía**: Validar flujos completos de usuario sin tocar la base de datos real ni hacer llamadas a APIs externas (Gemini).

**Características**:
- **Mocking Completo**: 
  - `SessionLocal` es mockeado para evitar tocar la BD real
  - `AIService` y `AnalyticsService` son mockeados para evitar llamadas a Gemini
  - Todos los módulos externos (`google.generativeai`) son mockeados antes de importar

- **Flujos Validados**:
  - Onboarding: Toggle de categorías, selección múltiple
  - Navegación: Settings → Categorías, menú principal
  - Prioridad Global: Botones del menú cancelan flujos activos
  - Input Multimodal: Texto natural activa handlers correctos

- **Helpers Reutilizables**:
  - `_mock_session_factory()`: Mock de sesión de BD
  - `_mock_ai_service()`: Mock de servicio de IA
  - `_build_update_with_message()`: Construcción de Updates mock
  - `_build_update_with_callback()`: Construcción de CallbackQueries mock

**Ejemplo de Test**:
```python
async def test_onboarding_category_toggle_updates_state(self, mocker):
    # Setup con mocking
    session = mocker.MagicMock()
    _mock_session_factory(mocker, session)
    
    # Ejecución
    result = await onboarding_category_choice(update, context)
    
    # Verificación sin tocar BD real
    assert "Comida" not in context.user_data["onboarding"]["selected_defaults"]
```

**Beneficio**: Tests rápidos, aislados y sin dependencias externas. Permiten validar lógica de negocio sin costos de API ni riesgo de modificar datos reales.

#### Tests Unitarios

**Archivo**: `tests/test_callback_manager.py`

- 25 tests para `CallbackManager`
- Validación de límite de 64 bytes
- Parsing robusto de callback_data

### Política de Testing

**Regla Crítica**: Cualquier cambio futuro en el Router, Onboarding o Prioridad de Menú REQUIERE actualizar o añadir tests de integración (`tests/test_integration_flows.py`) antes de desplegar.

**Áreas que Requieren Tests Obligatorios**:
- Cambios en `bot/handlers/natural_language.py` (Router)
- Cambios en `bot/handlers/onboarding.py` (Onboarding)
- Cambios en `bot/application.py` relacionados con prioridad de handlers (Global Menu Priority)
- Nuevos flujos conversacionales (`ConversationHandler`)

**Beneficio**: Garantiza que cambios en flujos críticos de UX no rompan funcionalidad existente sin detección.

---

## 🚀 Despliegue

### Docker
- **Imagen base**: `python:3.12-slim`
- **Puerto**: Configurable vía `PORT` (default: 8000)
- **Comando**: `python main.py`

### Webhook Configuration
- El bot usa **webhooks** (no polling)
- `WEBHOOK_URL` debe ser HTTPS
- `drop_pending_updates=True` al iniciar

### Base de Datos
- **PostgreSQL** requerido
- **Alembic** configurado para gestión de migraciones
- **Aplicar migraciones**: `alembic upgrade head`

---

## 📚 Referencias Rápidas

### Archivos "Corazón"
- `bot/application.py`: Builder de aplicación y registro de handlers
- `models.py`: Modelos ORM
- `main.py`: Entry point del webhook
- `bot/services/ai_service.py`: Cliente Gemini Multimodal
- `bot/services/analytics_service.py`: Analista SQL seguro
- `bot/handlers/natural_language.py`: Router inteligente
- `bot/handlers/media_handler.py`: Procesador multimodal

### Funciones Clave
- `get_now_utc()`: Obtener fecha/hora actual en UTC
- `convert_utc_to_local()`: Convertir UTC a hora local
- `AIService.parse_transaction()`: Parsear transacción desde texto/imagen/audio
- `AIService.transcribe_audio()`: Transcribir audio a texto
- `AnalyticsService.answer_question()`: Responder pregunta financiera con SQL
- `process_user_text_input()`: Procesar texto (compartido entre texto y voz)

---

**Última actualización**: Diciembre 2024
**Versión del código analizado**: Staging branch
**Arquitectura**: FinBot AI 2.0 (Multimodal, AI-First)
