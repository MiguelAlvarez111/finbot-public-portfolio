# UX Design Log - FinBot AI

**Última actualización**: Diciembre 2024  
**Propósito**: Documentar la filosofía de diseño actual para evitar regresiones futuras y mantener coherencia en el desarrollo.

---

## 1. Filosofía "AI-First"

### Principio Fundamental

**"Si la IA puede hacerlo en 1 paso, no crees una UI de 5 pasos."**

Este principio guía todas las decisiones de diseño del bot. La experiencia debe ser conversacional y natural, no una serie de formularios.

### Eliminación de Botones de Registro Manual

**Decisión**: Se eliminaron los botones "💸 Registrar Gasto" y "💰 Registrar Ingreso" del menú principal.

**Razón**: **Fricción vs IA**

- **Antes (Alto Fricción)**: Usuario presiona botón → Selecciona categoría → Ingresa monto → Confirma → 4-5 pasos
- **Ahora (Bajo Fricción)**: Usuario escribe "Gaste 20k en almuerzo" → 1 paso, transacción registrada

**Impacto**:
- Reduce fricción cognitiva en ~70%
- Alinea la UI con el mensaje "Soy Inteligente! No necesitas botones"
- Fuerza al usuario a usar el flujo natural (texto/audio/foto)

**Regla de Oro**:
> Si una acción puede completarse con lenguaje natural en 1 mensaje, **NO** debe tener un botón dedicado en el menú principal.

**Excepciones** (funciones que requieren múltiples pasos o configuración):
- ✅ Reporte (genera visualización)
- ✅ Dashboard (abre panel web)
- ✅ Metas (flujo de creación/aporte)
- ✅ Ajustes (menú de configuración)

**Implementación**:
- Los comandos `/gasto` y `/ingreso` existen como **fallback** para usuarios avanzados, pero no se promocionan
- El handler de lenguaje natural tiene prioridad sobre flujos guiados
- Los mensajes educativos enfatizan el uso conversacional

### Estrategia de Fallo (Plan B)

**Regla de Oro**: Si la IA falla repetidamente o hay problemas de conexión, el bot debe degradarse elegantemente y ofrecer flujos manuales (`/gasto`) como último recurso, explicando la situación.

**Implementación**:
- **Detección de fallos repetidos**: Si la IA falla 2-3 veces consecutivas, el bot debe detectar el patrón
- **Degradación elegante**: Informar al usuario sobre el problema de forma transparente
- **Ofrecer alternativa manual**: Sugerir explícitamente usar `/gasto` o `/ingreso` como solución temporal
- **Mensaje de transición**: "Parece que hay problemas con la conexión a la IA. Mientras tanto, puedes usar `/gasto` para registrar manualmente."

**Beneficio**: El usuario nunca queda bloqueado. Siempre hay un camino alternativo, aunque sea menos elegante.

---

## 2. Mapa de Navegación Actual (Snapshot)

### Menú Principal (4 Botones)

```
┌─────────────────────────────────────┐
│  📊 Reporte    │  📈 Dashboard     │
│  🎯 Metas      │  ⚙️ Ajustes      │
└─────────────────────────────────────┘
```

**Justificación de 4 botones**:
- **Carga cognitiva óptima**: 4 opciones es el "sweet spot" para decisión rápida
- **Coherencia con mensaje AI-First**: Menos botones = más espacio para conversación
- **Funciones complementarias**: Reporte y Dashboard no compiten, sirven propósitos distintos

### Árbol de Navegación Completo

```
Menú Principal (4 botones)
│
├── 📊 Reporte
│   └── Genera gráfico del mes actual
│
├── 📈 Dashboard
│   └── Abre panel web temporal (1 minuto de validez)
│
├── 🎯 Metas
│   ├── ➕ Crear meta
│   └── 📥 Aportar a meta
│
└── ⚙️ Ajustes
    ├── ⚖️ Presupuestos          ← Función "oculta"
    │   ├── ➕ Configurar presupuesto
    │   └── 📋 Ver presupuestos
    │
    ├── 🗂️ Gestionar categorías
    │   ├── ➕ Agregar
    │   ├── ➖ Eliminar
    │   └── ✏️ Renombrar
    │
    ├── 📊 Estadísticas rápidas
    ├── 📥 Exportar datos (.xlsx)
    ├── ⏮️ Ver últimos gastos
    ├── 📚 Guía de Usuario
    ├── 🎮 Gamificación
    ├── 🔄 Resetear cuenta
    └── ⬅️ Volver al menú
```

### Funciones "Ocultas" (Diseño Intencional)

**Presupuestos dentro de Ajustes**:
- **Razón**: Uso menos frecuente que reportes o metas
- **Filosofía**: Funciones de configuración van en Ajustes, no en menú principal
- **Beneficio**: Mantiene el menú principal limpio y enfocado en acciones diarias

**Comandos Legacy (No Promocionados)**:
- `/gasto` - Flujo guiado de gasto (fallback)
- `/ingreso` - Flujo guiado de ingreso (fallback)
- `/categorias` - Gestión de categorías (accesible desde Ajustes)
- `/presupuesto` - Configuración de presupuesto (accesible desde Ajustes)

**Regla**: Los comandos existen para usuarios avanzados, pero **no se mencionan** en mensajes educativos. El bot debe ser autoexplicativo sin depender de comandos.

---

## 3. Estrategia de Onboarding "Show, Don't Tell"

### Concepto Fundamental

**"Show, Don't Tell"**: El usuario debe **experimentar** las capacidades antes de configurar.

### Flujo de Onboarding Actual

```
1. Bienvenida
   "¡Hola! Soy tu asistente financiero 🤖"

2. DEMO (Obligatorio antes de configurar)
   "Para empezar, quiero mostrarte lo que puedo hacer.
   
   Prueba decirme o mandarme un audio:
   'Gaste 20k en almuerzo ayer'
   
   ¿Te animas a probar ahora o configuramos primero?"
   
   [🧪 Probar Demo] [⚙️ Configurar]

3a. Si elige "Probar Demo":
    - Usuario escribe/envía audio
    - Bot procesa y registra transacción REAL
    - Muestra resultado: "¡Así de fácil es!"
    - Luego pasa a configuración de categorías

3b. Si elige "Configurar":
    - Salta directamente a selección de categorías

4. Selección de Categorías
   - Usuario activa/desactiva categorías sugeridas
   - Puede agregar categorías personalizadas

5. Finalización
   - Mensaje educativo sobre uso multimodal
   - Menú principal aparece
```

### Por Qué Recomendamos la Demo (Altamente Recomendada, No Bloqueante)

**Razón 1: Reducción de Fricción de Aprendizaje**
- El usuario **ve** el resultado antes de invertir tiempo en configuración
- Reduce ansiedad: "¿Funcionará esto?"
- Genera confianza inmediata

**Razón 2: Educación Activa vs Pasiva**
- **Pasiva (mala)**: "Puedes escribir o enviar audio" (solo texto)
- **Activa (buena)**: Usuario prueba → Ve resultado → Aprende

**Razón 3: Engagement Inmediato**
- El usuario registra su primera transacción en < 30 segundos
- Crea "momentum" para continuar con la configuración
- Reduce tasa de abandono en onboarding

**Regla del "Primer Fallo Suave"**:
- Si la demo falla (IA no responde, error de conexión, parsing fallido), la respuesta debe ser **ultra cuidadosa**
- **Nunca culpar al usuario**: "No pude procesar eso" (no "Escribiste mal")
- **Ofrecer salida inmediata**: "No te preocupes, podemos saltar a la configuración ahora y probar después"
- **Mensaje de consuelo**: "A veces la IA necesita un momento. Podemos configurar tus categorías y probar más tarde"
- **Objetivo**: No frustrar al usuario nuevo en su primer contacto. Un fallo en la demo puede ser la primera y última impresión.

---

### Implementación Técnica

**Ubicación**: `bot/handlers/onboarding.py`

**Estados clave**:
- `ONBOARDING_DEMO`: Estado donde el usuario puede probar antes de configurar
- `onboarding_demo_process()`: Procesa texto/audio durante demo y crea transacción REAL

**Características**:
- La transacción del demo se **guarda realmente** (no es simulada)
- Si el usuario elige "Configurar", puede saltar el demo
- El demo acepta texto y audio (multimodal desde el inicio)

---

## 4. Manejo de Errores: Patrón "Errores Empáticos"

### Principio Fundamental

**"Nunca decir 'Error', siempre decir 'No entendí, prueba X'"**

Los errores son oportunidades de educación, no fallos técnicos.

### Patrón de Mensajes de Error

#### ❌ **ANTES (Técnico, Frustrante)**

```
"Error: Invalid input"
"No pude procesar la solicitud"
"Error al procesar la selección"
```

#### ✅ **AHORA (Empático, Educativo)**

```
"😅 No entendí bien ese gasto.

Intenta así:
• 'Gaste 20k en taxi'
• 'Recibí 500k de nómina'"

"🤖 No pude leer bien esa foto.

💡 Consejos:
• Asegúrate de que la foto esté bien iluminada
• Enfoca el texto de la factura
• O simplemente escríbeme: 'Gaste 50k en supermercado'"

"🤖 No pude entender el audio. Intenta hablar más claro o enviar el gasto por texto."
```

### Reglas de Mensajes de Error

1. **Nunca usar la palabra "Error"**
   - ❌ "Error al procesar"
   - ✅ "No entendí bien eso"

2. **Siempre ofrecer alternativas**
   - ❌ "No pude procesar"
   - ✅ "No pude procesar. Intenta así: 'Gaste 20k en taxi'"

3. **Usar emojis para humanizar**
   - 😅 = Error leve, no crítico
   - 🤖 = Error de IA/procesamiento
   - ⚠️ = Advertencia/requisito previo

4. **Proporcionar ejemplos concretos**
   - No solo decir "intenta de nuevo"
   - Mostrar formato esperado: `'Gaste 20k en taxi'`

5. **Ofrecer múltiples caminos**
   - Si falla foto → sugerir texto
   - Si falla audio → sugerir texto
   - Si falla texto → sugerir formato específico

### Errores Progresivos

**Concepto**: Adaptar la verbosidad del mensaje de error según el número de intentos fallidos consecutivos.

**Implementación**:

**1er Error**: Mensaje completo con tips y ejemplos
```
"😅 No entendí bien ese gasto.

Intenta así:
• 'Gaste 20k en taxi'
• 'Recibí 500k de nómina'"
```

**2do Error consecutivo**: Versión corta y directa
```
"Sigo sin entender, ¿probamos escribiéndolo así: 'Gaste 20k en taxi'?"
```

**3er Error consecutivo**: Ofrecer alternativa manual
```
"Parece que hay un problema. ¿Quieres usar /gasto para registrarlo paso a paso?"
```

**Beneficio**: Reduce fricción en usuarios que están luchando. El mensaje se vuelve más directo y menos verboso después del primer fallo, evitando frustración adicional.

### Ejemplos por Tipo de Error

#### Error de Parsing de IA

**Ubicación**: `bot/handlers/natural_language.py:257-263`

```python
await message_obj.reply_text(
    "😅 No entendí bien ese gasto.\n\n"
    "Intenta así:\n"
    "• _'Gaste 20k en taxi'_\n"
    "• _'Recibí 500k de nómina'_",
    parse_mode="Markdown"
)
```

#### Error de OCR (Foto)

**Ubicación**: `bot/handlers/media_handler.py:88-95`

```python
await message.reply_text(
    "🤖 No pude leer bien esa foto.\n\n"
    "💡 Consejos:\n"
    "• Asegúrate de que la foto esté bien iluminada\n"
    "• Enfoca el texto de la factura\n"
    "• O simplemente escríbeme: 'Gaste 50k en supermercado'"
)
```

#### Error de Transcripción (Audio)

**Ubicación**: `bot/handlers/media_handler.py:230-232`

```python
await message.reply_text(
    "🤖 No pude entender el audio. Intenta hablar más claro o enviar el gasto por texto."
)
```

#### Error de Consulta Analítica

**Ubicación**: `bot/handlers/natural_language.py:375-377`

```python
await message_obj.reply_text(
    f"😅 No pude procesar tu consulta. Intenta reformularla o usar comandos específicos como /reporte_mes"
)
```

### Checklist para Nuevos Errores

Al agregar un nuevo mensaje de error, verificar:

- [ ] ¿Evita la palabra "Error"?
- [ ] ¿Ofrece al menos una alternativa?
- [ ] ¿Incluye un ejemplo concreto?
- [ ] ¿Usa emoji apropiado (😅, 🤖, ⚠️)?
- [ ] ¿Mantiene el tono conversacional?
- [ ] ¿Guía al usuario hacia una solución?

---

## 5. Guía de Estilo para Futuros Desarrollos

### ✅ **DEBE Hacer**

1. **Priorizar lenguaje natural sobre botones**
   - Si puede hacerse con texto/audio/foto, no crear botón

2. **Mantener menú principal en 4 botones máximo**
   - Funciones avanzadas van en Ajustes

3. **Forzar demo/experiencia antes de configuración**
   - "Show, Don't Tell" en onboarding

4. **Usar mensajes empáticos en errores**
   - "No entendí" + ejemplos + alternativas

5. **Mantener coherencia con mensaje AI-First**
   - No contradicciones entre UI y mensajes educativos

### ❌ **NO DEBE Hacer**

1. **Agregar botones de registro manual al menú principal**
   - Violaría principio AI-First

2. **Expandir menú principal más allá de 4 botones**
   - Aumenta carga cognitiva

3. **Mencionar comandos en mensajes educativos**
   - El bot debe ser autoexplicativo

4. **Usar mensajes técnicos de error**
   - "Error: X" → "No entendí, prueba Y"

5. **Crear flujos guiados de 5+ pasos para acciones simples**
   - Si la IA puede hacerlo en 1 paso, no crear UI compleja

---

## 6. Referencias de Implementación

### Archivos Clave

- **Menú Principal**: `bot/keyboards.py:118-130`
- **Onboarding Demo**: `bot/handlers/onboarding.py:193-423`
- **Manejo de Errores**: `bot/handlers/natural_language.py:257-387`
- **Mensajes Educativos**: `bot/handlers/onboarding.py:38-46`

### Decisiones de Diseño Documentadas

- **UX_FINAL_AUDIT.md**: Auditoría completa de UX (Diciembre 2024)
- **UX_INVENTORY.md**: Inventario de características UX
- **PROJECT_CONTEXT.md**: Contexto general del proyecto

---

## 7. Métricas de Éxito

### Indicadores de Coherencia AI-First

- **% de transacciones por lenguaje natural** (objetivo: >80%)
- **% de transacciones por botones/comandos** (objetivo: <20%)
- **Tiempo promedio de primera transacción** (objetivo: <30 segundos)

### Indicadores de Onboarding

- **Tasa de completación de onboarding** (objetivo: >70%)
- **% de usuarios que prueban demo** (objetivo: >60%)
- **Tiempo hasta primera transacción** (objetivo: <2 minutos)

### Indicadores de Manejo de Errores

- **Tasa de retención después de error** (objetivo: >50%)
- **Intentos promedio hasta éxito** (objetivo: <2)

---

## 8. Modo Power User

### Concepto

Algunos usuarios expertos prefieren comandos estructurados sobre lenguaje natural. El bot debe respetar esta preferencia sin alienar a estos usuarios.

### Implementación

**Comandos Avanzados Disponibles**:
- `/gasto` - Flujo guiado de registro de gasto
- `/ingreso` - Flujo guiado de registro de ingreso
- `/categorias` - Gestión directa de categorías
- `/presupuesto` - Configuración directa de presupuesto
- `/ver_presupuesto` - Visualización de presupuestos
- `/crear_meta` - Creación directa de meta
- `/aportar_meta` - Aporte directo a meta
- `/ultimos` - Últimas transacciones
- `/reporte_mes` - Reporte mensual
- `/exportar` - Exportación a Excel

**Documentación Discreta**:
- Los comandos avanzados deben estar documentados en una sección "Comandos Avanzados" dentro de `/help` o `/guia`
- **No se promocionan** en mensajes educativos principales
- **No aparecen** en el menú principal
- Están disponibles para usuarios que los buscan explícitamente

**Filosofía**:
- El bot es **AI-First** por defecto, pero **no excluye** a usuarios que prefieren estructura
- Los comandos actúan como "puente" para usuarios en transición
- Los usuarios expertos pueden usar comandos sin sentirse "menos importantes"

**Ubicación**: `bot/handlers/core.py:help_command()` o `bot/handlers/core.py:user_guide()`

---

## 9. Modo Degradado (IA Down)

### Concepto

Si el servicio de IA (Gemini) está caído o no responde, el bot debe informar al usuario, desactivar análisis avanzado y habilitar registro manual como principal temporalmente.

### Implementación

**Detección de Estado**:
- Monitoreo de salud de la conexión a Gemini
- Detección de fallos repetidos (3+ intentos fallidos en < 1 minuto)
- Timeout de conexión configurado apropiadamente

**Comportamiento en Modo Degradado**:

1. **Informar al Usuario**:
   ```
   "⚠️ Estoy teniendo problemas para conectarme con la IA en este momento.
   
   Mientras tanto, puedes usar:
   • /gasto - Para registrar gastos manualmente
   • /ingreso - Para registrar ingresos manualmente
   
   Los análisis avanzados estarán disponibles nuevamente pronto."
   ```

2. **Desactivar Funcionalidades Avanzadas**:
   - ❌ Procesamiento de lenguaje natural (texto libre)
   - ❌ OCR de fotos
   - ❌ Transcripción de audio
   - ❌ Consultas analíticas (Text-to-SQL)
   - ✅ Comandos manuales (`/gasto`, `/ingreso`)
   - ✅ Reportes básicos (si no dependen de IA)
   - ✅ Visualización de datos existentes

3. **Habilitar Registro Manual como Principal**:
   - Los comandos `/gasto` y `/ingreso` se convierten en la forma principal de registro
   - Se puede mostrar un mensaje temporal en el menú principal indicando el modo degradado
   - Los flujos guiados funcionan normalmente (no dependen de IA)

4. **Recuperación Automática**:
   - Cuando la conexión se restablece, el bot vuelve automáticamente a modo normal
   - Opcionalmente, notificar al usuario: "✅ La IA está de vuelta. Ya puedes usar lenguaje natural nuevamente."

**Beneficio**: El usuario nunca queda completamente bloqueado. Siempre hay una forma de registrar transacciones, aunque sea menos elegante.

**Ubicación**: `bot/services/ai_service.py` (detección de estado), `bot/application.py` (routing condicional)

---

**Última revisión**: Diciembre 2024  
**Próxima revisión**: Después de cambios significativos en UX

