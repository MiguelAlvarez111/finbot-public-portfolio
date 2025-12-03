from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

import pytest
from pytest_mock import MockerFixture
from telegram import InlineKeyboardMarkup

import main
from models import Category, CategoryType, Transaction


def _mock_session_factory(mocker: MockerFixture, session) -> None:
    context_manager = mocker.MagicMock()
    context_manager.__enter__.return_value = session
    context_manager.__exit__.return_value = None
    mocker.patch("main.SessionLocal", return_value=context_manager)


def _build_update_with_message(mocker: MockerFixture, user_id: int = 123):
    message = SimpleNamespace(reply_text=mocker.AsyncMock())
    effective_user = SimpleNamespace(id=user_id)
    return SimpleNamespace(effective_user=effective_user, message=message)


def _build_update_with_callback(mocker: MockerFixture, data: str, user_id: int = 123):
    query = SimpleNamespace(
        data=data,
        answer=mocker.AsyncMock(),
        edit_message_text=mocker.AsyncMock(),
        message=SimpleNamespace(chat_id=999),
    )
    effective_user = SimpleNamespace(id=user_id)
    return SimpleNamespace(effective_user=effective_user, callback_query=query)


@pytest.mark.asyncio
async def test_show_recent_transactions_without_results(mocker: MockerFixture) -> None:
    session = mocker.MagicMock()
    execute_result = mocker.MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    session.execute.return_value = execute_result
    _mock_session_factory(mocker, session)

    update = _build_update_with_message(mocker)
    context = SimpleNamespace()

    await main.show_recent_transactions(update, context)

    update.message.reply_text.assert_awaited_once_with("No encontré transacciones recientes.")


@pytest.mark.asyncio
async def test_show_recent_transactions_with_results(mocker: MockerFixture) -> None:
    session = mocker.MagicMock()
    tx = SimpleNamespace(
        id=847,
        transaction_date=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
        amount=Decimal("5000.00"),
        description="Café",
    )
    execute_result = mocker.MagicMock()
    execute_result.scalars.return_value = iter((tx,))
    session.execute.return_value = execute_result
    _mock_session_factory(mocker, session)

    update = _build_update_with_message(mocker)
    context = SimpleNamespace()

    await main.show_recent_transactions(update, context)

    await_args = update.message.reply_text.await_args
    assert await_args.kwargs["reply_markup"]
    keyboard: InlineKeyboardMarkup = await_args.kwargs["reply_markup"]
    button = keyboard.inline_keyboard[0][0]
    assert button.callback_data == "del_tx_847"
    assert "Café" in button.text


@pytest.mark.asyncio
async def test_delete_transaction_callback_user_verified(mocker: MockerFixture) -> None:
    session = mocker.MagicMock()
    transaction = Transaction(
        id=847,
        user_id=123,
        category_id=1,
        amount=Decimal("100.00"),
        transaction_date=datetime.now(timezone.utc),
    )
    session.get.return_value = transaction
    _mock_session_factory(mocker, session)

    query = SimpleNamespace(
        data="del_tx_847",
        answer=mocker.AsyncMock(),
        edit_message_text=mocker.AsyncMock(),
        message=SimpleNamespace(chat_id=999),
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=123),
        callback_query=query,
    )
    context = SimpleNamespace()

    await main.delete_transaction_callback(update, context)

    session.delete.assert_called_once_with(transaction)
    session.commit.assert_called_once()
    query.edit_message_text.assert_awaited_once_with("Transacción eliminada correctamente.")


@pytest.mark.asyncio
async def test_category_add_type_selected_creates_category(mocker: MockerFixture) -> None:
    session = mocker.MagicMock()
    execute_result = mocker.MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    session.execute.return_value = execute_result
    _mock_session_factory(mocker, session)

    query = SimpleNamespace(
        data=f"cat_add_type:{CategoryType.EXPENSE.value}",
        answer=mocker.AsyncMock(),
        edit_message_text=mocker.AsyncMock(),
        message=SimpleNamespace(chat_id=777),
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=321),
        callback_query=query,
    )
    bot = SimpleNamespace(send_message=mocker.AsyncMock())
    context = SimpleNamespace(bot=bot, user_data={"category_operation": {"name": "Transporte"}})

    await main.category_add_type_selected(update, context)

    session.add.assert_called_once()
    added_category: Category = session.add.call_args.args[0]
    assert added_category.user_id == 321
    assert added_category.name == "Transporte"
    assert added_category.type == CategoryType.EXPENSE

    query.edit_message_text.assert_awaited()
    context.bot.send_message.assert_awaited_once()


def test_parse_amount_success() -> None:
    amount = main.parse_amount(" 1234,56 ")
    assert amount == Decimal("1234.56")


def test_parse_amount_invalid() -> None:
    with pytest.raises(InvalidOperation):
        main.parse_amount("-50")


@pytest.mark.asyncio
async def test_expense_amount_received_stores_pending_transaction(mocker: MockerFixture) -> None:
    send_prompt = mocker.patch("main.send_category_prompt", new=mocker.AsyncMock())

    update = _build_update_with_message(mocker)
    update.message.text = "1500"
    context = SimpleNamespace(user_data={})

    next_state = await main.expense_amount_received(update, context)

    assert next_state == main.EXPENSE_CATEGORY
    assert context.user_data["pending_transaction"]["amount"] == Decimal("1500.00")
    send_prompt.assert_awaited_once()


@pytest.mark.asyncio
async def test_expense_amount_received_invalid_input(mocker: MockerFixture) -> None:
    update = _build_update_with_message(mocker)
    update.message.text = "mil pesos"
    context = SimpleNamespace(user_data={})

    next_state = await main.expense_amount_received(update, context)

    assert next_state == main.EXPENSE_AMOUNT
    update.message.reply_text.assert_awaited_once_with(
        "Monto no válido. Intenta nuevamente con un número positivo."
    )


@pytest.mark.asyncio
async def test_expense_category_selected_prompts_description(mocker: MockerFixture) -> None:
    session = mocker.MagicMock()
    category = Category(
        id=5,
        user_id=123,
        name="Comida",
        type=CategoryType.EXPENSE,
        is_default=False,
    )
    session.get.return_value = category
    _mock_session_factory(mocker, session)

    update = _build_update_with_callback(mocker, "cat:5")
    context = SimpleNamespace(
        user_data={"pending_transaction": {"amount": Decimal("25000.00"), "type": "expense"}}
    )

    next_state = await main.expense_category_selected(update, context)

    assert next_state == main.EXPENSE_DESCRIPTION_DECISION
    session.add.assert_not_called()
    assert context.user_data["pending_transaction"]["category_id"] == 5
    update.callback_query.edit_message_text.assert_awaited()


@pytest.mark.asyncio
async def test_expense_description_received_uses_default_category(mocker: MockerFixture) -> None:
    session = mocker.MagicMock()
    default_category = Category(
        id=99,
        user_id=123,
        name="General",
        type=CategoryType.EXPENSE,
        is_default=True,
    )
    execute_result = mocker.MagicMock()
    execute_result.scalar_one_or_none.return_value = default_category
    session.execute.return_value = execute_result
    _mock_session_factory(mocker, session)

    update = _build_update_with_message(mocker)
    update.message.text = "Cena de trabajo"
    context = SimpleNamespace(
        user_data={"pending_transaction": {"amount": Decimal("40000.00"), "type": "expense"}}
    )

    next_state = await main.expense_description_received(update, context)

    assert next_state == main.ConversationHandler.END
    session.add.assert_called_once()
    transaction: Transaction = session.add.call_args.args[0]
    assert transaction.category_id == 99
    assert transaction.description == "Cena de trabajo"
    assert "pending_transaction" not in context.user_data
    update.message.reply_text.assert_awaited_once_with(
        "Gasto registrado correctamente en la categoría General."
    )


@pytest.mark.asyncio
async def test_expense_description_decision_yes_prompts_for_text(mocker: MockerFixture) -> None:
    update = _build_update_with_callback(mocker, "expense_desc:yes")
    context = SimpleNamespace(
        user_data={
            "pending_transaction": {
                "amount": Decimal("123.45"),
                "category_id": 5,
                "category_name": "Comida",
            }
        }
    )

    next_state = await main.expense_description_decision(update, context)

    assert next_state == main.EXPENSE_DESCRIPTION_INPUT
    update.callback_query.edit_message_text.assert_awaited_once()
    assert "pending_transaction" in context.user_data


@pytest.mark.asyncio
async def test_expense_description_decision_no_creates_transaction(mocker: MockerFixture) -> None:
    session = mocker.MagicMock()
    _mock_session_factory(mocker, session)

    update = _build_update_with_callback(mocker, "expense_desc:no")
    context = SimpleNamespace(
        user_data={
            "pending_transaction": {
                "amount": Decimal("123.45"),
                "category_id": 5,
                "category_name": "Comida",
                "type": "expense",
            }
        }
    )

    next_state = await main.expense_description_decision(update, context)

    assert next_state == main.ConversationHandler.END
    session.add.assert_called_once()
    transaction: Transaction = session.add.call_args.args[0]
    assert transaction.category_id == 5
    update.callback_query.edit_message_text.assert_awaited_once()
    assert "pending_transaction" not in context.user_data


@pytest.mark.asyncio
async def test_expense_description_received_with_selected_category(mocker: MockerFixture) -> None:
    session = mocker.MagicMock()
    category = Category(
        id=5,
        user_id=123,
        name="Comida",
        type=CategoryType.EXPENSE,
        is_default=False,
    )
    session.get.return_value = category
    _mock_session_factory(mocker, session)

    update = _build_update_with_message(mocker)
    update.message.text = "Cena rápida"
    context = SimpleNamespace(
        user_data={
            "pending_transaction": {
                "amount": Decimal("500.00"),
                "type": "expense",
                "category_id": 5,
                "category_name": "Comida",
            }
        }
    )

    next_state = await main.expense_description_received(update, context)

    assert next_state == main.ConversationHandler.END
    session.add.assert_called_once()
    transaction: Transaction = session.add.call_args.args[0]
    assert transaction.category_id == 5
    assert transaction.description == "Cena rápida"
    update.message.reply_text.assert_awaited_once_with(
        "Gasto registrado correctamente en la categoría Comida."
    )
    assert "pending_transaction" not in context.user_data


@pytest.mark.asyncio
async def test_income_category_selected_creates_transaction(mocker: MockerFixture) -> None:
    session = mocker.MagicMock()
    category = Category(
        id=7,
        user_id=123,
        name="Salario",
        type=CategoryType.INCOME,
        is_default=False,
    )
    session.get.return_value = category
    _mock_session_factory(mocker, session)

    update = _build_update_with_callback(mocker, "cat:7")
    context = SimpleNamespace(
        user_data={"pending_transaction": {"amount": Decimal("1500.50"), "type": "income"}}
    )

    next_state = await main.income_category_selected(update, context)

    assert next_state == main.ConversationHandler.END
    session.add.assert_called_once()
    transaction: Transaction = session.add.call_args.args[0]
    assert transaction.amount == Decimal("1500.50")
    assert transaction.category_id == 7
    assert "pending_transaction" not in context.user_data
    update.callback_query.edit_message_text.assert_awaited_once_with(
        "Ingreso registrado correctamente en la categoría Salario."
    )


def test_format_transaction_button_text_today(monkeypatch) -> None:
    tx = SimpleNamespace(
        transaction_date=datetime.now(timezone.utc),
        amount=Decimal("1234.50"),
        description="Pago",
    )
    text = main.format_transaction_button_text(tx)
    assert text.startswith("Hoy - 1234.5")

