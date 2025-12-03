"""Tests de integración para flujos de navegación y funcionalidades críticas.

Este módulo valida que los flujos de usuario completos funcionan correctamente,
incluyendo los bug fixes críticos en gestión de categorías.
"""

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

# Mockear módulos externos antes de importar bot
# Esto previene errores de importación durante los tests
sys.modules['google'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()

# Configurar DATABASE_URL temporal para evitar error al importar
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt")
os.environ.setdefault("GEMINI_API_KEY", "test-api-key")

from telegram.ext import ConversationHandler

from bot.handlers.core import dashboard
from bot.handlers.onboarding import onboarding_category_choice
from bot.handlers.categories import category_management_menu
from bot.handlers.natural_language import handle_text_message
from bot.conversation_states import ONBOARDING_CATEGORY_CHOICES, CATEGORY_MENU
from bot.utils.callback_manager import CallbackManager


# ========== HELPERS ==========

def _mock_session_factory(mocker: MockerFixture, session: MagicMock) -> None:
    """Mockea SessionLocal para usar una sesión mock."""
    context_manager = mocker.MagicMock()
    context_manager.__enter__.return_value = session
    context_manager.__exit__.return_value = None
    mocker.patch("database.SessionLocal", return_value=context_manager)
    mocker.patch("bot.handlers.categories.SessionLocal", return_value=context_manager)
    mocker.patch("bot.handlers.onboarding.SessionLocal", return_value=context_manager)
    mocker.patch("bot.handlers.natural_language.SessionLocal", return_value=context_manager)


def _mock_ai_service(mocker: MockerFixture) -> MagicMock:
    """Mockea AIService para evitar llamadas reales a Gemini."""
    ai_service_mock = mocker.MagicMock()
    mocker.patch("bot.services.ai_service.get_ai_service", return_value=ai_service_mock)
    return ai_service_mock


def _mock_analytics_service(mocker: MockerFixture) -> MagicMock:
    """Mockea AnalyticsService para evitar llamadas reales a Gemini."""
    analytics_service_mock = mocker.MagicMock()
    mocker.patch("bot.services.analytics_service.get_analytics_service", return_value=analytics_service_mock)
    return analytics_service_mock


def _build_update_with_message(mocker: MockerFixture, user_id: int = 123, text: str = "") -> SimpleNamespace:
    """Construye un Update mock con un mensaje de texto."""
    message = SimpleNamespace(
        reply_text=mocker.AsyncMock(),
        text=text,
    )
    effective_user = SimpleNamespace(id=user_id)
    effective_chat = SimpleNamespace(id=999)
    return SimpleNamespace(
        effective_user=effective_user,
        effective_chat=effective_chat,
        message=message,
        callback_query=None,
    )


def _build_update_with_callback(
    mocker: MockerFixture, 
    callback_data: str, 
    user_id: int = 123
) -> SimpleNamespace:
    """Construye un Update mock con un CallbackQuery."""
    query = SimpleNamespace(
        data=callback_data,
        answer=mocker.AsyncMock(),
        edit_message_text=mocker.AsyncMock(),
        edit_message_reply_markup=mocker.AsyncMock(),
        message=SimpleNamespace(chat_id=999),
        from_user=SimpleNamespace(id=user_id),
    )
    effective_user = SimpleNamespace(id=user_id)
    effective_chat = SimpleNamespace(id=999)
    return SimpleNamespace(
        effective_user=effective_user,
        effective_chat=effective_chat,
        callback_query=query,
        message=None,
    )


def _build_context(mocker: MockerFixture, user_data: dict = None) -> SimpleNamespace:
    """Construye un Context mock."""
    bot = SimpleNamespace(
        send_message=mocker.AsyncMock(),
        send_chat_action=mocker.AsyncMock(),
    )
    return SimpleNamespace(
        bot=bot,
        user_data=user_data or {},
    )


# ========== TESTS ==========


class TestOnboardingFlow:
    """Tests para el flujo de onboarding, validando el bug fix del toggle."""

    @pytest.mark.asyncio
    async def test_onboarding_category_toggle_updates_state(self, mocker: MockerFixture) -> None:
        """Test que valida el bug fix: el toggle de categoría actualiza correctamente el estado.
        
        ESCENARIO:
        - Usuario hace clic en una categoría para marcarla/desmarcarla
        - El callback es parseado correctamente
        - El estado se actualiza y se regenera el teclado visual
        """
        # Setup
        session = mocker.MagicMock()
        _mock_session_factory(mocker, session)
        
        callback_data = CallbackManager.onboarding("toggle", "Comida")
        update = _build_update_with_callback(mocker, callback_data)
        context = _build_context(mocker, user_data={
            "onboarding": {
                "selected_defaults": {"Comida", "Transporte"},
                "custom_categories": [],
            }
        })

        # Ejecución
        result = await onboarding_category_choice(update, context)

        # Verificaciones
        # 1. El callback fue respondido
        update.callback_query.answer.assert_awaited_once()
        
        # 2. El estado fue actualizado (Comida se desmarcó porque ya estaba seleccionada)
        assert "Comida" not in context.user_data["onboarding"]["selected_defaults"]
        assert "Transporte" in context.user_data["onboarding"]["selected_defaults"]
        
        # 3. El mensaje fue editado con el nuevo teclado (validación del bug fix)
        update.callback_query.edit_message_text.assert_awaited_once()
        call_args = update.callback_query.edit_message_text.await_args
        assert call_args is not None
        assert call_args.kwargs.get("reply_markup") is not None
        
        # 4. Retorna el estado correcto
        assert result == ONBOARDING_CATEGORY_CHOICES

    @pytest.mark.asyncio
    async def test_onboarding_category_toggle_adds_category(self, mocker: MockerFixture) -> None:
        """Test que valida que al hacer toggle se puede agregar una categoría."""
        # Setup
        session = mocker.MagicMock()
        _mock_session_factory(mocker, session)
        
        callback_data = CallbackManager.onboarding("toggle", "Salud")
        update = _build_update_with_callback(mocker, callback_data)
        context = _build_context(mocker, user_data={
            "onboarding": {
                "selected_defaults": {"Comida"},
                "custom_categories": [],
            }
        })

        # Ejecución
        result = await onboarding_category_choice(update, context)

        # Verificaciones
        # La categoría se agregó al set
        assert "Salud" in context.user_data["onboarding"]["selected_defaults"]
        assert "Comida" in context.user_data["onboarding"]["selected_defaults"]
        
        # El mensaje fue actualizado
        update.callback_query.edit_message_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_onboarding_category_toggle_locked_category(self, mocker: MockerFixture) -> None:
        """Test que valida que las categorías bloqueadas no se pueden desmarcar."""
        # Setup
        session = mocker.MagicMock()
        _mock_session_factory(mocker, session)
        
        callback_data = CallbackManager.onboarding("toggle", "General")
        update = _build_update_with_callback(mocker, callback_data)
        context = _build_context(mocker, user_data={
            "onboarding": {
                "selected_defaults": {"General", "Comida"},
                "custom_categories": [],
            }
        })

        # Ejecución
        result = await onboarding_category_choice(update, context)

        # Verificaciones
        # Se muestra un alerta al usuario (answer se llama dos veces: al inicio y con alert)
        assert update.callback_query.answer.await_count >= 1
        # Verificar que al menos una llamada fue con show_alert=True
        answer_calls = update.callback_query.answer.await_args_list
        alert_call_found = any(
            call.kwargs.get("show_alert") is True 
            for call in answer_calls
        )
        assert alert_call_found, "Expected at least one call to answer() with show_alert=True"
        
        # La categoría General permanece seleccionada
        assert "General" in context.user_data["onboarding"]["selected_defaults"]


class TestSettingsNavigation:
    """Tests para la navegación a ajustes, validando el bug fix."""

    @pytest.mark.asyncio
    async def test_settings_categories_opens_menu(self, mocker: MockerFixture) -> None:
        """Test que valida el bug fix: callback desde settings abre el menú de categorías.
        
        ESCENARIO:
        - Usuario presiona "Gestionar categorías" en Ajustes
        - El callback s:categories es procesado
        - El ConversationHandler se activa y muestra el menú
        """
        # Setup
        session = mocker.MagicMock()
        _mock_session_factory(mocker, session)
        
        callback_data = CallbackManager.settings("categories")
        update = _build_update_with_callback(mocker, callback_data)
        context = _build_context(mocker)

        # Ejecución
        result = await category_management_menu(update, context)

        # Verificaciones
        # 1. El callback fue respondido (si es necesario)
        # Nota: category_management_menu no llama a answer(), pero el handler sí debería
        
        # 2. El mensaje fue editado con el teclado de gestión
        update.callback_query.edit_message_text.assert_awaited_once()
        call_args = update.callback_query.edit_message_text.await_args
        assert call_args is not None
        assert "Gestión de categorías" in call_args.args[0] or call_args.kwargs.get("text", "")
        assert call_args.kwargs.get("reply_markup") is not None
        
        # 3. Retorna el estado correcto
        assert result == CATEGORY_MENU


class TestGlobalMenuPriority:
    """Tests para validar la prioridad global del menú principal."""

    @pytest.mark.asyncio
    async def test_dashboard_button_cancels_conversation(self, mocker: MockerFixture) -> None:
        """Test que valida que el botón Dashboard cancela cualquier flujo activo.
        
        ESCENARIO:
        - Usuario envía el texto "📈 Dashboard" desde el menú
        - El handler de dashboard se ejecuta
        - El contexto de conversación se limpia
        """
        # Setup
        mocker.patch.dict(os.environ, {"SECRET_KEY": "test-secret-key", "DASHBOARD_URL": "https://test.example.com"})
        mocker.patch("bot.handlers.core.get_now_utc")
        mocker.patch("jwt.encode", return_value="fake-jwt-token")
        
        update = _build_update_with_message(mocker, text="📈 Dashboard")
        context = _build_context(mocker, user_data={
            "some_active_conversation": True,
            "pending_data": {"amount": 1000},
        })

        # Ejecución
        result = await dashboard(update, context)

        # Verificaciones
        # 1. El contexto de conversación fue limpiado (prioridad global)
        assert len(context.user_data) == 0
        
        # 2. El bot respondió con el enlace del dashboard
        update.message.reply_text.assert_awaited_once()
        reply_text = update.message.reply_text.await_args.args[0]
        assert "enlace temporal al dashboard" in reply_text.lower()
        assert "fake-jwt-token" in reply_text
        
        # 3. Retorna END para terminar cualquier conversación
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_dashboard_without_secret_key(self, mocker: MockerFixture) -> None:
        """Test que valida el manejo de error cuando no hay SECRET_KEY."""
        # Setup
        mocker.patch.dict(os.environ, {}, clear=True)
        
        update = _build_update_with_message(mocker, text="📈 Dashboard")
        context = _build_context(mocker)

        # Ejecución
        result = await dashboard(update, context)

        # Verificaciones
        # Se muestra un mensaje de error apropiado
        update.message.reply_text.assert_awaited_once()
        reply_text = update.message.reply_text.await_args.args[0]
        assert "clave secreta" in reply_text.lower()


class TestMultimodalInput:
    """Tests para input multimodal (texto natural)."""

    @pytest.mark.asyncio
    async def test_text_input_triggers_natural_language_handler(self, mocker: MockerFixture) -> None:
        """Test que valida que el texto natural activa el handler correcto.
        
        ESCENARIO:
        - Usuario envía texto "Gaste 20k"
        - El handler de lenguaje natural procesa el mensaje
        - Se intenta clasificar la intención (registro vs consulta)
        """
        # Setup
        session = mocker.MagicMock()
        _mock_session_factory(mocker, session)
        
        # Mock de usuario existente y onboarded
        from models import User
        user_mock = mocker.MagicMock(spec=User)
        user_mock.telegram_id = 123
        user_mock.chat_id = 999
        user_mock.is_onboarded = True
        session.get.return_value = user_mock
        
        # Mock de process_user_text_input para aislar el test
        process_mock = mocker.patch(
            "bot.handlers.natural_language.process_user_text_input",
            new=mocker.AsyncMock()
        )
        
        update = _build_update_with_message(mocker, text="Gaste 20k")
        context = _build_context(mocker)

        # Ejecución
        await handle_text_message(update, context)

        # Verificaciones
        # 1. El mensaje fue recibido correctamente
        assert update.message is not None
        assert update.message.text == "Gaste 20k"
        
        # 2. El handler llamó a process_user_text_input con los parámetros correctos
        process_mock.assert_awaited_once()
        call_args = process_mock.await_args
        assert call_args.args[0] == "Gaste 20k"  # text
        assert call_args.args[1] == 123  # user_id
        assert call_args.args[2] == context  # context
        assert call_args.args[3] == update.message  # message_obj


class TestIntegrationFlows:
    """Tests de integración end-to-end para flujos completos."""

    @pytest.mark.asyncio
    async def test_onboarding_toggle_with_multiple_categories(self, mocker: MockerFixture) -> None:
        """Test de integración: toggle múltiple de categorías en onboarding."""
        # Setup
        session = mocker.MagicMock()
        _mock_session_factory(mocker, session)
        
        update = _build_update_with_callback(
            mocker, 
            CallbackManager.onboarding("toggle", "Transporte")
        )
        context = _build_context(mocker, user_data={
            "onboarding": {
                "selected_defaults": {"Comida", "Salud"},
                "custom_categories": [],
            }
        })

        # Ejecución: Primer toggle (agregar)
        result1 = await onboarding_category_choice(update, context)
        
        # Verificación: Transporte fue agregado
        assert "Transporte" in context.user_data["onboarding"]["selected_defaults"]
        
        # Segundo toggle (remover)
        result2 = await onboarding_category_choice(update, context)
        
        # Verificación: Transporte fue removido
        assert "Transporte" not in context.user_data["onboarding"]["selected_defaults"]
        
        # Verificación: Se llamó edit_message_text en ambas ocasiones
        assert update.callback_query.edit_message_text.await_count == 2

    @pytest.mark.asyncio
    async def test_category_management_menu_from_settings_vs_command(
        self, mocker: MockerFixture
    ) -> None:
        """Test que valida que el menú funciona tanto desde settings como desde comando."""
        # Setup
        session = mocker.MagicMock()
        _mock_session_factory(mocker, session)
        
        # Test 1: Desde callback (settings)
        callback_update = _build_update_with_callback(
            mocker, 
            CallbackManager.settings("categories")
        )
        callback_context = _build_context(mocker)
        
        result1 = await category_management_menu(callback_update, callback_context)
        
        # Verificación: Funciona desde callback
        callback_update.callback_query.edit_message_text.assert_awaited_once()
        
        # Test 2: Desde comando
        message_update = _build_update_with_message(mocker, text="/categorias")
        message_context = _build_context(mocker)
        
        result2 = await category_management_menu(message_update, message_context)
        
        # Verificación: Funciona desde comando
        message_update.message.reply_text.assert_awaited_once()
        
        # Ambos retornan el mismo estado
        assert result1 == CATEGORY_MENU
        assert result2 == CATEGORY_MENU

