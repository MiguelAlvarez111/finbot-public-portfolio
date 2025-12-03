"""Sistema robusto y tipado para manejo de callback_data de Telegram.

Este módulo proporciona una interfaz segura para generar y parsear
callback_data, asegurando que no se exceda el límite de 64 bytes de Telegram
y proporcionando validación de tipos.
"""
from enum import Enum
from typing import Optional, Tuple


# Límite de bytes para callback_data en Telegram
MAX_CALLBACK_DATA_BYTES = 64


class CallbackType(Enum):
    """Tipos de callbacks con prefijos cortos para ahorrar bytes."""
    
    # Categorías
    CATEGORY = "c"  # cat:{id} -> c:{id}
    CATEGORY_MANAGE = "cm"  # cat_manage:* -> cm:*
    CATEGORY_ADD_TYPE = "ct"  # cat_add_type:* -> ct:*
    
    # Settings
    SETTINGS = "s"  # settings:* -> s:*
    
    # Transacciones
    DELETE_TRANSACTION = "dt"  # del_tx_{id} -> dt:{id}
    EXPENSE_DESC = "ed"  # expense_desc:* -> ed:*
    
    # Onboarding
    ONBOARDING = "o"  # onboarding:* -> o:*
    
    # Metas
    GOAL_CONTRIB = "gc"  # goal_contrib_{id} -> gc:{id}
    GOALS = "g"  # goals:* -> g:*
    
    # Presupuestos
    BUDGETS = "b"  # budgets:* -> b:*
    BUDGET_CAT = "bc"  # budget_cat_{id} -> bc:{id}
    
    # Gestión de categorías (acciones específicas)
    DELETE_CATEGORY = "dc"  # del_cat_{id} -> dc:{id}
    RENAME_CATEGORY = "rc"  # ren_cat_{id} -> rc:{id}


class CallbackManager:
    """Manager para generar y parsear callback_data de forma segura."""
    
    SEPARATOR = ":"
    
    @staticmethod
    def _validate_length(callback_data: str) -> None:
        """Valida que el callback_data no exceda el límite de 64 bytes.
        
        Args:
            callback_data: String del callback_data a validar.
        
        Raises:
            ValueError: Si el callback_data excede 64 bytes.
        """
        byte_length = len(callback_data.encode("utf-8"))
        if byte_length > MAX_CALLBACK_DATA_BYTES:
            raise ValueError(
                f"Callback data excede el límite de {MAX_CALLBACK_DATA_BYTES} bytes. "
                f"Longitud actual: {byte_length} bytes. "
                f"Callback: {callback_data[:50]}..."
            )
    
    @staticmethod
    def _build_callback(callback_type: CallbackType, *parts: str) -> str:
        """Construye un callback_data con validación.
        
        Args:
            callback_type: Tipo de callback.
            *parts: Partes adicionales del callback (IDs, acciones, etc.).
        
        Returns:
            str: Callback data formateado.
        
        Raises:
            ValueError: Si el callback excede 64 bytes.
        """
        parts_list = [callback_type.value] + list(parts)
        callback_data = CallbackManager.SEPARATOR.join(parts_list)
        CallbackManager._validate_length(callback_data)
        return callback_data
    
    @staticmethod
    def _parse_callback(callback_data: str, expected_type: CallbackType) -> Tuple[str, ...]:
        """Parsea un callback_data y valida su tipo.
        
        Args:
            callback_data: String del callback_data a parsear.
            expected_type: Tipo esperado del callback.
        
        Returns:
            Tuple[str, ...]: Partes del callback (sin el prefijo del tipo).
        
        Raises:
            ValueError: Si el callback no tiene el formato esperado.
        """
        parts = callback_data.split(CallbackManager.SEPARATOR)
        if not parts:
            raise ValueError(f"Callback data vacío: {callback_data}")
        
        if parts[0] != expected_type.value:
            raise ValueError(
                f"Tipo de callback inesperado. Esperado: {expected_type.value}, "
                f"recibido: {parts[0]}. Callback: {callback_data}"
            )
        
        return tuple(parts[1:])
    
    # ========== MÉTODOS DE GENERACIÓN ==========
    
    @staticmethod
    def category(category_id: int) -> str:
        """Genera callback para selección de categoría.
        
        Args:
            category_id: ID de la categoría.
        
        Returns:
            str: Callback data (ej: "c:123").
        """
        return CallbackManager._build_callback(CallbackType.CATEGORY, str(category_id))
    
    @staticmethod
    def delete_transaction(transaction_id: int) -> str:
        """Genera callback para eliminar transacción.
        
        Args:
            transaction_id: ID de la transacción.
        
        Returns:
            str: Callback data (ej: "dt:456").
        """
        return CallbackManager._build_callback(CallbackType.DELETE_TRANSACTION, str(transaction_id))
    
    @staticmethod
    def settings(action: str, *args: str) -> str:
        """Genera callback para acciones de settings.
        
        Args:
            action: Acción de settings (ej: "back", "currency", "export").
            *args: Argumentos adicionales (ej: código de moneda).
        
        Returns:
            str: Callback data (ej: "s:back", "s:currency:COP").
        """
        return CallbackManager._build_callback(CallbackType.SETTINGS, action, *args)
    
    @staticmethod
    def onboarding(action: str, *args: str) -> str:
        """Genera callback para acciones de onboarding.
        
        Args:
            action: Acción de onboarding (ej: "start", "toggle", "finish").
            *args: Argumentos adicionales (ej: nombre de categoría).
        
        Returns:
            str: Callback data (ej: "o:start", "o:toggle:Comida").
        """
        return CallbackManager._build_callback(CallbackType.ONBOARDING, action, *args)
    
    @staticmethod
    def goal_contribution(goal_id: int) -> str:
        """Genera callback para aportar a una meta.
        
        Args:
            goal_id: ID de la meta.
        
        Returns:
            str: Callback data (ej: "gc:789").
        """
        return CallbackManager._build_callback(CallbackType.GOAL_CONTRIB, str(goal_id))
    
    @staticmethod
    def goals(action: str) -> str:
        """Genera callback para acciones de metas.
        
        Args:
            action: Acción de metas (ej: "create", "contribute").
        
        Returns:
            str: Callback data (ej: "g:create").
        """
        return CallbackManager._build_callback(CallbackType.GOALS, action)
    
    @staticmethod
    def budgets(action: str) -> str:
        """Genera callback para acciones de presupuestos.
        
        Args:
            action: Acción de presupuestos (ej: "create", "view").
        
        Returns:
            str: Callback data (ej: "b:create").
        """
        return CallbackManager._build_callback(CallbackType.BUDGETS, action)
    
    @staticmethod
    def budget_category(category_id: int) -> str:
        """Genera callback para selección de categoría en presupuesto.
        
        Args:
            category_id: ID de la categoría.
        
        Returns:
            str: Callback data (ej: "bc:123").
        """
        return CallbackManager._build_callback(CallbackType.BUDGET_CAT, str(category_id))
    
    @staticmethod
    def category_manage(action: str) -> str:
        """Genera callback para gestión de categorías.
        
        Args:
            action: Acción (ej: "add", "delete", "rename").
        
        Returns:
            str: Callback data (ej: "cm:add").
        """
        return CallbackManager._build_callback(CallbackType.CATEGORY_MANAGE, action)
    
    @staticmethod
    def category_add_type(category_type: str) -> str:
        """Genera callback para tipo de categoría al agregar.
        
        Args:
            category_type: Tipo de categoría (ej: "income", "expense").
        
        Returns:
            str: Callback data (ej: "ct:income").
        """
        return CallbackManager._build_callback(CallbackType.CATEGORY_ADD_TYPE, category_type)
    
    @staticmethod
    def expense_desc(choice: str) -> str:
        """Genera callback para decisión de descripción en gasto.
        
        Args:
            choice: Elección (ej: "yes", "no").
        
        Returns:
            str: Callback data (ej: "ed:yes").
        """
        return CallbackManager._build_callback(CallbackType.EXPENSE_DESC, choice)
    
    # ========== MÉTODOS DE PARSING ==========
    
    @staticmethod
    def parse_category(callback_data: str) -> int:
        """Parsea callback de categoría y retorna el ID.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            int: ID de la categoría.
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        parts = CallbackManager._parse_callback(callback_data, CallbackType.CATEGORY)
        if len(parts) != 1:
            raise ValueError(f"Formato inválido para categoría: {callback_data}")
        return int(parts[0])
    
    @staticmethod
    def parse_delete_transaction(callback_data: str) -> int:
        """Parsea callback de eliminar transacción y retorna el ID.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            int: ID de la transacción.
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        parts = CallbackManager._parse_callback(callback_data, CallbackType.DELETE_TRANSACTION)
        if len(parts) != 1:
            raise ValueError(f"Formato inválido para eliminar transacción: {callback_data}")
        return int(parts[0])
    
    @staticmethod
    def parse_settings(callback_data: str) -> Tuple[str, ...]:
        """Parsea callback de settings y retorna las partes.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            Tuple[str, ...]: Partes del callback (acción y argumentos).
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        return CallbackManager._parse_callback(callback_data, CallbackType.SETTINGS)
    
    @staticmethod
    def parse_onboarding(callback_data: str) -> Tuple[str, ...]:
        """Parsea callback de onboarding y retorna las partes.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            Tuple[str, ...]: Partes del callback (acción y argumentos).
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        return CallbackManager._parse_callback(callback_data, CallbackType.ONBOARDING)
    
    @staticmethod
    def parse_goal_contribution(callback_data: str) -> int:
        """Parsea callback de aporte a meta y retorna el ID.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            int: ID de la meta.
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        parts = CallbackManager._parse_callback(callback_data, CallbackType.GOAL_CONTRIB)
        if len(parts) != 1:
            raise ValueError(f"Formato inválido para aporte a meta: {callback_data}")
        return int(parts[0])
    
    @staticmethod
    def parse_budget_category(callback_data: str) -> int:
        """Parsea callback de categoría en presupuesto y retorna el ID.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            int: ID de la categoría.
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        parts = CallbackManager._parse_callback(callback_data, CallbackType.BUDGET_CAT)
        if len(parts) != 1:
            raise ValueError(f"Formato inválido para categoría de presupuesto: {callback_data}")
        return int(parts[0])
    
    @staticmethod
    def parse_category_manage(callback_data: str) -> str:
        """Parsea callback de gestión de categorías y retorna la acción.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            str: Acción (ej: "add", "delete", "rename").
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        parts = CallbackManager._parse_callback(callback_data, CallbackType.CATEGORY_MANAGE)
        if len(parts) != 1:
            raise ValueError(f"Formato inválido para gestión de categorías: {callback_data}")
        return parts[0]
    
    @staticmethod
    def parse_category_add_type(callback_data: str) -> str:
        """Parsea callback de tipo de categoría y retorna el tipo.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            str: Tipo de categoría (ej: "income", "expense").
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        parts = CallbackManager._parse_callback(callback_data, CallbackType.CATEGORY_ADD_TYPE)
        if len(parts) != 1:
            raise ValueError(f"Formato inválido para tipo de categoría: {callback_data}")
        return parts[0]
    
    @staticmethod
    def parse_expense_desc(callback_data: str) -> str:
        """Parsea callback de descripción de gasto y retorna la elección.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            str: Elección (ej: "yes", "no").
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        parts = CallbackManager._parse_callback(callback_data, CallbackType.EXPENSE_DESC)
        if len(parts) != 1:
            raise ValueError(f"Formato inválido para descripción de gasto: {callback_data}")
        return parts[0]
    
    @staticmethod
    def parse_goals(callback_data: str) -> str:
        """Parsea callback de metas y retorna la acción.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            str: Acción (ej: "create", "contribute").
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        parts = CallbackManager._parse_callback(callback_data, CallbackType.GOALS)
        if len(parts) != 1:
            raise ValueError(f"Formato inválido para metas: {callback_data}")
        return parts[0]
    
    @staticmethod
    def parse_budgets(callback_data: str) -> str:
        """Parsea callback de presupuestos y retorna la acción.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            str: Acción (ej: "create", "view").
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        parts = CallbackManager._parse_callback(callback_data, CallbackType.BUDGETS)
        if len(parts) != 1:
            raise ValueError(f"Formato inválido para presupuestos: {callback_data}")
        return parts[0]
    
    @staticmethod
    def delete_category(category_id: int) -> str:
        """Genera callback para eliminar categoría.
        
        Args:
            category_id: ID de la categoría.
        
        Returns:
            str: Callback data (ej: "dc:123").
        """
        return CallbackManager._build_callback(CallbackType.DELETE_CATEGORY, str(category_id))
    
    @staticmethod
    def rename_category(category_id: int) -> str:
        """Genera callback para renombrar categoría.
        
        Args:
            category_id: ID de la categoría.
        
        Returns:
            str: Callback data (ej: "rc:123").
        """
        return CallbackManager._build_callback(CallbackType.RENAME_CATEGORY, str(category_id))
    
    @staticmethod
    def parse_delete_category(callback_data: str) -> int:
        """Parsea callback de eliminar categoría y retorna el ID.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            int: ID de la categoría.
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        parts = CallbackManager._parse_callback(callback_data, CallbackType.DELETE_CATEGORY)
        if len(parts) != 1:
            raise ValueError(f"Formato inválido para eliminar categoría: {callback_data}")
        return int(parts[0])
    
    @staticmethod
    def parse_rename_category(callback_data: str) -> int:
        """Parsea callback de renombrar categoría y retorna el ID.
        
        Args:
            callback_data: Callback data a parsear.
        
        Returns:
            int: ID de la categoría.
        
        Raises:
            ValueError: Si el formato es inválido.
        """
        parts = CallbackManager._parse_callback(callback_data, CallbackType.RENAME_CATEGORY)
        if len(parts) != 1:
            raise ValueError(f"Formato inválido para renombrar categoría: {callback_data}")
        return int(parts[0])

