"""Utilidades para manejo de timezones y fechas.

Este módulo proporciona funciones para trabajar con fechas y horas
de manera consistente, asegurando que todas las fechas se almacenen
en UTC en la base de datos y se conviertan a la zona horaria local
para visualización.
"""
from datetime import datetime, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Python < 3.9 fallback
    from backports.zoneinfo import ZoneInfo  # type: ignore


def get_now_utc() -> datetime:
    """Retorna la fecha y hora actual en UTC (timezone-aware).
    
    Esta es la función estándar para obtener el tiempo actual en todo el proyecto.
    Todas las fechas deben almacenarse en UTC en la base de datos.
    
    Returns:
        datetime: Fecha y hora actual en UTC con timezone info.
    
    Example:
        >>> now = get_now_utc()
        >>> print(now.tzinfo)
        UTC
    """
    return datetime.now(timezone.utc)


def convert_utc_to_local(
    utc_dt: datetime,
    timezone_str: str = "America/Bogota"
) -> datetime:
    """Convierte un datetime UTC a la zona horaria local especificada.
    
    Útil para mostrar fechas a los usuarios en su zona horaria local,
    mientras que en la base de datos siempre se almacenan en UTC.
    
    Args:
        utc_dt: Datetime en UTC (debe ser timezone-aware).
        timezone_str: String de zona horaria (default: "America/Bogota").
            Usa formato IANA (ej: "America/Bogota", "America/New_York").
    
    Returns:
        datetime: Datetime convertido a la zona horaria local especificada.
    
    Raises:
        ValueError: Si utc_dt no es timezone-aware o si timezone_str es inválido.
    
    Example:
        >>> utc_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        >>> local_time = convert_utc_to_local(utc_time, "America/Bogota")
        >>> print(local_time.hour)  # 7 (Bogotá está UTC-5)
    """
    if utc_dt.tzinfo is None:
        raise ValueError(
            "utc_dt debe ser timezone-aware. "
            "Asegúrate de que el datetime tenga tzinfo=timezone.utc"
        )
    
    try:
        local_tz = ZoneInfo(timezone_str)
    except Exception as e:
        raise ValueError(
            f"Zona horaria inválida: {timezone_str}. "
            f"Usa formato IANA (ej: 'America/Bogota'). Error: {e}"
        )
    
    return utc_dt.astimezone(local_tz)


def get_utc_now_for_default() -> datetime:
    """Función callable para usar como default en SQLAlchemy Column.
    
    Esta función debe usarse como default en Column(DateTime, default=get_utc_now_for_default)
    para asegurar que cada vez que se crea un registro, se obtiene el tiempo actual.
    
    Returns:
        datetime: Fecha y hora actual en UTC con timezone info.
    
    Note:
        No usar directamente get_now_utc() como default porque se evaluaría
        una sola vez al importar el módulo. Esta función se llama cada vez
        que se necesita el valor por defecto.
    """
    return get_now_utc()

