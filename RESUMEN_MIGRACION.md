# Resumen de Migración: Staging → Producción

## 📋 Cambios Detectados en la Base de Datos

### Tabla `users` - Nuevas columnas:
- ✅ `is_onboarded` (Boolean, NOT NULL, default=False)
- ✅ `streak_days` (Integer, NOT NULL, default=0)
- ✅ `last_entry_date` (Date, nullable=True)

### Tabla `budgets` - Cambio estructural:
- ❌ **Eliminar**: `period` (Enum: monthly, weekly, yearly)
- ✅ **Agregar**: `start_date` (Date, NOT NULL)
- ✅ **Agregar**: `end_date` (Date, NOT NULL)

## 🚀 Pasos Rápidos

### 1. Diagnóstico (Opcional pero recomendado)

```bash
# Configura la URL de la base de datos de producción
export DATABASE_URL="postgresql://postgres:vkfhyIbdyEwOWHSpWWMurAmNIWOZFdmc@metro.proxy.rlwy.net:38878/railway"

# Ejecuta el diagnóstico
python diagnose_db.py
```

### 2. Backupe

```bash
# Haz un backup antes de cualquier cambio
pg_dump -h host -U user -d database > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 3. Aplicar Migración

Revisa y ejecuta el archivo `migration_production.sql`:

```bash
psql -h host -U user -d database -f migration_production.sql
```

O ejecuta las consultas manualmente siguiendo el archivo SQL.

## ⚠️ Puntos Críticos

### Migración de `budgets`

La tabla `budgets` es la más compleja porque cambia de usar `period` a `start_date` y `end_date`.

**Orden de ejecución:**
1. Agregar columnas `start_date` y `end_date`
2. Migrar datos de `period` a las nuevas columnas
3. Verificar que todos los registros tienen fechas
4. Hacer las columnas NOT NULL
5. Eliminar la columna `period` (solo después de verificar que todo funciona)

**Nota:** Las consultas de migración calculan las fechas basándose en la fecha actual:
- Mensual: mes actual (día 1 al último día del mes)
- Semanal: semana actual (lunes a domingo)
- Anual: año actual (día 1 de enero al 31 de diciembre)

## 📁 Archivos Creados

1. **`diagnose_db.py`**: Script de diagnóstico que verifica el estado de la BD
2. **`migration_production.sql`**: Consultas SQL para aplicar la migración
3. **`MIGRATION_GUIDE.md`**: Guía completa con instrucciones detalladas
4. **`RESUMEN_MIGRACION.md`**: Este archivo (resumen rápido)

## ✅ Checklist

- [ ] Backup de la base de datos realizado
- [ ] Script de diagnóstico ejecutado (opcional)
- [ ] Columnas agregadas a la tabla `users`
- [ ] Columnas agregadas a la tabla `budgets`
- [ ] Datos de `period` migrados a `start_date` y `end_date`
- [ ] Verificación de que no hay valores NULL
- [ ] Columnas `start_date` y `end_date` configuradas como NOT NULL
- [ ] Columna `period` eliminada (después de verificar)
- [ ] Verificación post-migración exitosa
- [ ] Aplicación probada en producción

## 📖 Documentación Completa

Para más detalles, consulta `MIGRATION_GUIDE.md`.

