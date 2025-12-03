"""Tests unitarios para CallbackManager."""

import os
import pytest

# Configurar DATABASE_URL temporal para evitar error al importar
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

from bot.utils.callback_manager import CallbackManager, MAX_CALLBACK_DATA_BYTES


class TestCallbackManager:
    """Tests para CallbackManager."""

    def test_category_generation(self):
        """Verifica que la generación de callback de categoría funciona."""
        result = CallbackManager.category(123)
        assert result == "c:123"
        assert len(result.encode("utf-8")) <= MAX_CALLBACK_DATA_BYTES

    def test_category_parsing(self):
        """Verifica que el parsing de callback de categoría funciona."""
        category_id = CallbackManager.parse_category("c:123")
        assert category_id == 123

    def test_category_parsing_invalid(self):
        """Verifica que el parsing lanza ValueError con formato inválido."""
        with pytest.raises(ValueError):
            CallbackManager.parse_category("invalid:123")
        
        with pytest.raises(ValueError):
            CallbackManager.parse_category("c:invalid")

    def test_settings_generation(self):
        """Verifica que la generación de callback de settings funciona."""
        result = CallbackManager.settings("back")
        assert result == "s:back"
        
        result = CallbackManager.settings("currency", "COP")
        assert result == "s:currency:COP"

    def test_settings_parsing(self):
        """Verifica que el parsing de callback de settings funciona."""
        parts = CallbackManager.parse_settings("s:back")
        assert parts == ("back",)
        
        parts = CallbackManager.parse_settings("s:currency:COP")
        assert parts == ("currency", "COP")

    def test_delete_transaction_generation(self):
        """Verifica que la generación de callback de eliminar transacción funciona."""
        result = CallbackManager.delete_transaction(456)
        assert result == "dt:456"

    def test_delete_transaction_parsing(self):
        """Verifica que el parsing de callback de eliminar transacción funciona."""
        transaction_id = CallbackManager.parse_delete_transaction("dt:456")
        assert transaction_id == 456

    def test_onboarding_generation(self):
        """Verifica que la generación de callback de onboarding funciona."""
        result = CallbackManager.onboarding("start")
        assert result == "o:start"
        
        result = CallbackManager.onboarding("toggle", "Comida")
        assert result == "o:toggle:Comida"

    def test_onboarding_parsing(self):
        """Verifica que el parsing de callback de onboarding funciona."""
        parts = CallbackManager.parse_onboarding("o:start")
        assert parts == ("start",)
        
        parts = CallbackManager.parse_onboarding("o:toggle:Comida")
        assert parts == ("toggle", "Comida")

    def test_goal_contribution_generation(self):
        """Verifica que la generación de callback de aporte a meta funciona."""
        result = CallbackManager.goal_contribution(789)
        assert result == "gc:789"

    def test_goal_contribution_parsing(self):
        """Verifica que el parsing de callback de aporte a meta funciona."""
        goal_id = CallbackManager.parse_goal_contribution("gc:789")
        assert goal_id == 789

    def test_budgets_generation(self):
        """Verifica que la generación de callback de presupuestos funciona."""
        result = CallbackManager.budgets("create")
        assert result == "b:create"

    def test_budgets_parsing(self):
        """Verifica que el parsing de callback de presupuestos funciona."""
        action = CallbackManager.parse_budgets("b:create")
        assert action == "create"

    def test_budget_category_generation(self):
        """Verifica que la generación de callback de categoría de presupuesto funciona."""
        result = CallbackManager.budget_category(123)
        assert result == "bc:123"

    def test_budget_category_parsing(self):
        """Verifica que el parsing de callback de categoría de presupuesto funciona."""
        category_id = CallbackManager.parse_budget_category("bc:123")
        assert category_id == 123

    def test_category_manage_generation(self):
        """Verifica que la generación de callback de gestión de categorías funciona."""
        result = CallbackManager.category_manage("add")
        assert result == "cm:add"

    def test_category_manage_parsing(self):
        """Verifica que el parsing de callback de gestión de categorías funciona."""
        action = CallbackManager.parse_category_manage("cm:add")
        assert action == "add"

    def test_delete_category_generation(self):
        """Verifica que la generación de callback de eliminar categoría funciona."""
        result = CallbackManager.delete_category(123)
        assert result == "dc:123"

    def test_delete_category_parsing(self):
        """Verifica que el parsing de callback de eliminar categoría funciona."""
        category_id = CallbackManager.parse_delete_category("dc:123")
        assert category_id == 123

    def test_rename_category_generation(self):
        """Verifica que la generación de callback de renombrar categoría funciona."""
        result = CallbackManager.rename_category(123)
        assert result == "rc:123"

    def test_rename_category_parsing(self):
        """Verifica que el parsing de callback de renombrar categoría funciona."""
        category_id = CallbackManager.parse_rename_category("rc:123")
        assert category_id == 123

    def test_expense_desc_generation(self):
        """Verifica que la generación de callback de descripción de gasto funciona."""
        result = CallbackManager.expense_desc("yes")
        assert result == "ed:yes"

    def test_expense_desc_parsing(self):
        """Verifica que el parsing de callback de descripción de gasto funciona."""
        choice = CallbackManager.parse_expense_desc("ed:yes")
        assert choice == "yes"

    def test_length_validation(self):
        """Verifica que la validación de longitud funciona."""
        # Crear un callback que exceda 64 bytes
        # Usamos un string muy largo en la parte de onboarding
        long_string = "A" * 60  # Esto hará que el callback exceda 64 bytes
        
        with pytest.raises(ValueError) as exc_info:
            CallbackManager.onboarding("toggle", long_string)
        
        assert "excede el límite" in str(exc_info.value).lower()
        assert str(MAX_CALLBACK_DATA_BYTES) in str(exc_info.value)

    def test_all_callbacks_under_limit(self):
        """Verifica que todos los callbacks generados están bajo el límite."""
        test_cases = [
            CallbackManager.category(999999),
            CallbackManager.delete_transaction(999999),
            CallbackManager.settings("very_long_action_name"),
            CallbackManager.settings("currency", "USD"),
            CallbackManager.onboarding("start"),
            CallbackManager.onboarding("toggle", "CategoryName"),
            CallbackManager.goal_contribution(999999),
            CallbackManager.goals("create"),
            CallbackManager.budgets("create"),
            CallbackManager.budget_category(999999),
            CallbackManager.category_manage("add"),
            CallbackManager.delete_category(999999),
            CallbackManager.rename_category(999999),
            CallbackManager.expense_desc("yes"),
        ]
        
        for callback in test_cases:
            byte_length = len(callback.encode("utf-8"))
            assert byte_length <= MAX_CALLBACK_DATA_BYTES, (
                f"Callback '{callback}' excede el límite: {byte_length} bytes"
            )

