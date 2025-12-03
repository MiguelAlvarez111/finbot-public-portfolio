# 🔐 SECURITY_AUDIT.md

**Auditoría de Seguridad y Propiedad Intelectual para Publicación Pública**

Este documento clasifica todos los archivos del proyecto según su nivel de sensibilidad para preparar una versión pública del repositorio para portafolio.

---

## 🔴 CRÍTICO (Nunca Publicar)

Estos archivos contienen información sensible que **NUNCA** debe ser publicada en un repositorio público.
### Archivos de Configuración con Credenciales

- **`.env`** (si existe)
  - **Razón**: Contiene todas las variables de entorno sensibles (tokens de Telegram, API keys de Gemini, URLs de base de datos, secretos JWT)
  - **Estado**: Ya está en `.gitignore` ✅
  - **Acción**: Verificar que no esté en el historial de Git (`git log --all --full-history -- .env`)

- **`google_credentials.json`** (si existe)
  - **Razón**: Credenciales de Google Cloud/Gemini API
  - **Acción**: Verificar que no exista en el repositorio

### Scripts de Seeding con Datos Personales

- **`scripts/seed_prod_direct.py`** ⚠️ **CRÍTICO**
  - **Razón**: 
    - Contiene credenciales de base de datos de producción hardcodeadas (línea 29):
      ```python
      PROD_DATABASE_URL = "postgresql://postgres:PCxPCiSOehUwOnfOhcJGGUxfmRyqIgqh@shuttle.proxy.rlwy.net:54549/railway"
      ```
    - Contiene ID de usuario real de Telegram (línea 32):
      ```python
      TARGET_USER_ID = 5759131618
      ```
    - Este script conecta directamente a la base de datos de producción
  - **Acción**: 
    - **ELIMINAR** completamente del repositorio público
    - O crear una versión sanitizada con placeholders:
      ```python
      PROD_DATABASE_URL = os.getenv("PROD_DATABASE_URL")  # Placeholder
      TARGET_USER_ID = int(os.getenv("TARGET_USER_ID", "0"))  # Placeholder
      ```

### Bases de Datos Locales

- **`finbot.db`** ⚠️ **CRÍTICO**
  - **Razón**: Contiene datos reales de usuarios, transacciones, categorías, etc.
  - **Estado**: Ya está en `.gitignore` (patrón `*.db`) ✅
  - **Acción**: Verificar que no esté en el historial de Git

### Carpetas de Entorno Virtual y Archivos Compilados

- **`venv/`**
  - **Razón**: Entorno virtual con dependencias instaladas (puede contener información del sistema)
  - **Estado**: Ya está en `.gitignore` ✅

- **`__pycache__/`** (todas las instancias)
  - **Razón**: Archivos compilados de Python (bytecode)
  - **Acción**: Agregar a `.gitignore` si no está:
    ```
    __pycache__/
    *.py[cod]
    *$py.class
    ```

### Archivos de Backup

- **`init_db.py.save`**
  - **Razón**: Archivo de backup que puede contener configuraciones sensibles
  - **Acción**: Eliminar o revisar antes de publicar

---

## 🟡 SENSIBLE (Publicar con Censura/Sanitización)

Estos archivos contienen la "Salsa Secreta" (lógica de negocio y prompts de IA) que debe ser censurada o sanitizada antes de publicar.

### Servicios de IA (Prompts y Lógica de Negocio)

#### 1. **`bot/services/ai_service.py`** ⚠️ **MUY SENSIBLE**

**Razón**: Contiene los prompts completos y detallados de Gemini que son tu mayor activo de propiedad intelectual:

- **Prompts de Parsing de Transacciones** (líneas 183-475):
  - Prompt para imágenes (OCR de facturas) - líneas 183-258
  - Prompt para audio (STT con jerga colombiana) - líneas 260-366
  - Prompt para texto (parsing de lenguaje natural) - líneas 368-475
  
- **Lógica de Negocio Específica**:
  - Reglas de jerga monetaria colombiana ("k", "lucas", "barras", "palos")
  - Reglas de categorización semántica
  - Manejo de fechas relativas ("ayer", "antier", "hoy")
  - Conversión de timezone a Colombia

**Acción Recomendada**:
1. **Opción A (Recomendada)**: Crear versión sanitizada con prompts simplificados:
   ```python
   # Versión pública: prompts genéricos
   prompt = f"""Eres un asistente financiero. Extrae monto, categoría, descripción y fecha del siguiente texto: "{text}"
   
   Categorías disponibles: {categories_list}
   Fecha de referencia: {today_str}
   
   Responde en formato JSON: {{"amount": ..., "category_id": ..., ...}}"""
   ```

2. **Opción B**: Mantener estructura pero reemplazar prompts detallados con comentarios:
   ```python
   # PROMPT DETALLADO REMOVIDO PARA PROPIEDAD INTELECTUAL
   # El prompt completo contiene reglas específicas de jerga colombiana,
   # categorización semántica, y manejo de timezones
   prompt = self._build_prompt_internal(text, categories, date)
   ```

3. **Opción C**: Mantener el archivo pero con una nota de que los prompts son confidenciales y están en un archivo separado no versionado.

#### 2. **`bot/services/analytics_service.py`** ⚠️ **MUY SENSIBLE**

**Razón**: Contiene la lógica de seguridad multi-capa y los prompts de Text-to-SQL:

- **Prompts de Generación SQL** (líneas 196-294):
  - Prompt completo para generar SQL desde lenguaje natural
  - Reglas de seguridad y guardrails
  - Ejemplos de queries SQL específicos
  - Lógica de detección de intenciones destructivas

- **Lógica de Seguridad** (líneas 113-362):
  - Validación multi-capa de SQL
  - Detección de palabras clave destructivas
  - Sistema de guardrails contra inyección SQL
  - Prompt de interpretación de resultados (líneas 445-487)

**Acción Recomendada**:
1. **Opción A**: Sanitizar prompts manteniendo estructura:
   ```python
   # PROMPT DE GENERACIÓN SQL - VERSIÓN SIMPLIFICADA
   # El prompt completo contiene reglas específicas de seguridad,
   # ejemplos de queries, y lógica de detección de intenciones destructivas
   prompt = f"""Genera una consulta SQL SELECT para: "{question}"
   Esquema: {schema_info}
   Reglas: Solo SELECT, filtrar por user_id={user_id}"""
   ```

2. **Opción B**: Mantener la lógica de validación pero simplificar los prompts con comentarios indicando que son confidenciales.

3. **Opción C**: Documentar la arquitectura de seguridad pero mantener los prompts en un archivo separado no versionado.

### Archivos de Configuración de Aplicación

#### 3. **`bot/application.py`**

**Razón**: Puede contener configuraciones específicas o IDs hardcodeados.

**Revisión**: ✅ **SEGURO** - No contiene IDs hardcodeados ni credenciales. Solo contiene la estructura de handlers y es seguro publicar.

### Documentación Técnica

#### 4. **`PROJECT_CONTEXT.md`**

**Razón**: Documentación completa que puede revelar estrategias de negocio o detalles de implementación confidenciales.

**Revisión**: 
- ✅ **Mayormente Seguro**: Contiene información técnica general
- ⚠️ **Revisar**: 
  - Verificar que no contenga datos personales
  - Las estrategias de negocio mencionadas son genéricas y apropiadas para portafolio
  - Los ejemplos de prompts mencionados son conceptuales, no completos

**Acción**: Revisar manualmente y eliminar cualquier referencia a:
- Datos de usuarios reales
- Estrategias de monetización específicas
- Roadmaps futuros confidenciales

---

## 🟢 SEGURO (Publicar Tal Cual)

Estos archivos son seguros para publicar sin modificaciones.

### Estructura y Configuración Base

- **`requirements.txt`** ✅
  - Lista de dependencias públicas

- **`Dockerfile`** ✅
  - Configuración de contenedor genérica

- **`alembic.ini`** ✅
  - Configuración de migraciones (sin credenciales)

- **`runtime.txt`** ✅ (si existe)
  - Versión de Python

- **`.gitignore`** ✅
  - Ya excluye archivos sensibles

### Modelos y Base de Datos

- **`models.py`** ✅
  - Modelos ORM genéricos (sin datos)

- **`database.py`** ✅
  - Configuración de conexión (usa variables de entorno)

- **`migrations/`** ✅
  - Migraciones de Alembic (estructura de BD, sin datos)

### Handlers y Lógica de Aplicación

- **`bot/handlers/*.py`** ✅
  - Todos los handlers son seguros (lógica de negocio genérica)
  - `natural_language.py`: Router genérico (sin prompts)
  - `media_handler.py`: Procesamiento multimodal genérico
  - `onboarding.py`, `transactions.py`, `categories.py`, etc.: Lógica de UI

- **`bot/application.py`** ✅
  - Builder de aplicación (estructura de handlers)

- **`bot/keyboards.py`** ✅
  - Factories de teclados

- **`bot/conversation_states.py`** ✅
  - Constantes de estados

### Utilidades

- **`bot/utils/*.py`** ✅
  - `time_utils.py`: Utilidades de timezone
  - `amounts.py`: Parsing de montos
  - `callback_manager.py`: Gestión de callbacks

- **`bot/common.py`** ✅
  - Utilidades compartidas (logging, debug)

### Servicios (Estructura)

- **`bot/services/categories.py`** ✅
  - Helpers para categorías (lógica genérica)

### Entry Points

- **`main.py`** ✅
  - Entry point del webhook (usa variables de entorno)

- **`dashboard.py`** ✅
  - Aplicación Flask (genérica)

- **`init_db.py`** ✅
  - Inicialización de BD (genérica)

### Tests

- **`tests/*.py`** ✅
  - Tests con mocking (sin datos reales)

### Documentación

- **`README.md`** ✅
  - Documentación pública

- **`UX_DESIGN_LOG.md`** ✅
  - Log de diseño UX (genérico)

- **Otros archivos `.md`** ⚠️
  - Revisar manualmente para datos personales o información confidencial

---

## 📋 Checklist Pre-Publicación

Antes de hacer el repositorio público, ejecuta este checklist:

### 1. Eliminar Archivos Críticos
- [ ] Eliminar `scripts/seed_prod_direct.py` o sanitizarlo completamente
- [ ] Verificar que `finbot.db` no esté en el historial de Git
- [ ] Eliminar `init_db.py.save` o revisar su contenido
- [ ] Verificar que `.env` no esté en el historial de Git

### 2. Sanitizar Archivos Sensibles
- [ ] Sanitizar `bot/services/ai_service.py` (prompts)
- [ ] Sanitizar `bot/services/analytics_service.py` (prompts SQL)
- [ ] Revisar `PROJECT_CONTEXT.md` para datos personales

### 3. Actualizar .gitignore
- [ ] Agregar `__pycache__/` y `*.py[cod]` si no están
- [ ] Agregar `*.save` para archivos de backup
- [ ] Verificar que todos los archivos críticos estén excluidos

### 4. Verificar Historial de Git
```bash
# Buscar credenciales en el historial
git log --all --full-history -p | grep -i "password\|secret\|api_key\|token" > sensitive_data.txt

# Buscar archivos .env en historial
git log --all --full-history -- .env

# Buscar base de datos en historial
git log --all --full-history -- "*.db"
```

### 5. Crear Archivo de Ejemplo
- [ ] Crear `.env.example` con placeholders:
  ```
  TELEGRAM_TOKEN=your_telegram_token_here
  GEMINI_API_KEY=your_gemini_api_key_here
  DATABASE_URL=postgresql://user:password@host:port/dbname
  SECRET_KEY=your_secret_key_here
  WEBHOOK_URL=https://your-domain.com
  ```

### 6. Documentación de Seguridad
- [ ] Agregar sección en `README.md` sobre variables de entorno requeridas
- [ ] Documentar que los prompts de IA son confidenciales (si decides mantenerlos privados)

---

## 🎯 Recomendaciones Finales

### Para Proteger tu Propiedad Intelectual:

1. **Prompts de IA**: Considera mantener los prompts completos en un repositorio privado separado y solo publicar versiones simplificadas en el repositorio público.

2. **Lógica de Seguridad**: La arquitectura de seguridad multi-capa puede ser documentada, pero los prompts específicos de detección de intenciones destructivas pueden mantenerse privados.

3. **Jerga y Localización**: Las reglas específicas de jerga colombiana y localización son parte de tu diferenciador. Considera mantenerlas privadas o documentarlas de forma genérica.

4. **Scripts de Producción**: Nunca publiques scripts que se conecten a producción, incluso si están sanitizados. Crea versiones de ejemplo con datos ficticios.

### Para el Portafolio:

1. **Muestra la Arquitectura**: La estructura del código, patrones de diseño, y arquitectura general son excelentes para mostrar tus habilidades.

2. **Documenta el Proceso**: El `PROJECT_CONTEXT.md` es valioso para mostrar tu capacidad de documentación técnica.

3. **Tests y Calidad**: Los tests muestran buenas prácticas de desarrollo.

4. **Multimodalidad**: La capacidad de procesar texto, voz e imágenes es impresionante y puede destacarse sin revelar los prompts específicos.

---

## 📝 Notas Adicionales

- **Fecha de Auditoría**: Diciembre 2024
- **Versión del Código**: Staging branch
- **Auditor**: Análisis automatizado de estructura y contenido

---

**⚠️ IMPORTANTE**: Este documento es una guía. Revisa manualmente cada archivo antes de publicar, especialmente los marcados como 🟡 SENSIBLE. Cuando dudes, es mejor ser conservador y no publicar información que pueda comprometer tu propiedad intelectual o seguridad.

