"""Application builder for the Telegram bot."""

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from bot.common import debug_update, log_error
from bot.utils.callback_manager import CallbackType
from bot.conversation_states import (
    BUDGET_AMOUNT_INPUT,
    BUDGET_CATEGORY_SELECT,
    CATEGORY_ADD_NAME,
    CATEGORY_ADD_TYPE,
    CATEGORY_MENU,
    CATEGORY_RENAME_NAME,
    CATEGORY_RENAME_SELECT,
    EXPENSE_AMOUNT,
    EXPENSE_CATEGORY,
    EXPENSE_DESCRIPTION_DECISION,
    EXPENSE_DESCRIPTION_INPUT,
    GOAL_CONTRIBUTION_AMOUNT,
    GOAL_CONTRIBUTION_SELECT,
    GOAL_NAME_INPUT,
    GOAL_TARGET_INPUT,
    INCOME_AMOUNT,
    INCOME_CATEGORY,
    ONBOARDING_CATEGORY_CHOICES,
    ONBOARDING_COMPLETE,
    ONBOARDING_CUSTOM_INPUT,
    ONBOARDING_DEMO,
    ONBOARDING_WELCOME,
)
from bot.handlers.budgets import (
    budget_amount_received,
    budget_category_selected,
    budgets_menu,
    cancel_budget_flow,
    start_budget,
    view_budgets,
)
from bot.handlers.categories import (
    cancel_category_management,
    category_add_name_received,
    category_add_type_selected,
    category_delete_selected,
    category_management_menu,
    category_menu_selection,
    category_rename_name_received,
    category_rename_selected,
)
from bot.handlers.core import (
    dashboard,
    settings_back,
    settings_back_to_menu,
    settings_budgets_handler,
    settings_categories,
    settings_change_currency,
    settings_currency_selected,
    settings_delete_recent_handler,
    settings_export_handler,
    settings_gamification,
    settings_guide_handler,
    settings_menu,
    settings_quick_stats,
    settings_reset_cancel,
    settings_reset_confirm,
    settings_reset_prompt,
    user_guide,
)
from bot.handlers.goals import (
    cancel_goal_contribution,
    cancel_goal_creation,
    goals_menu,
    goal_contribution_amount_received,
    goal_contribution_selected,
    goal_name_received,
    goal_target_received,
    start_goal_contribution,
    start_goal_creation,
)
from bot.handlers.onboarding import (
    onboarding_category_choice,
    onboarding_custom_categories,
    onboarding_demo_handler,
    onboarding_demo_process,
    onboarding_finish,
    onboarding_restart,
    onboarding_start,
)
from bot.handlers.media_handler import handle_photo_message, handle_voice_message
from bot.handlers.natural_language import handle_text_message
from bot.handlers.reporting import export_transactions, monthly_report
from bot.handlers.transactions import (
    cancel_transaction,
    delete_transaction_callback,
    expense_amount_received,
    expense_category_selected,
    expense_description_decision,
    expense_description_received,
    income_amount_received,
    income_category_selected,
    income_description_received,
    show_recent_transactions,
    start_expense,
    start_income,
)


def _build_onboarding_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", onboarding_start),
            CallbackQueryHandler(onboarding_restart, pattern=rf"^{CallbackType.ONBOARDING.value}:restart$"),
        ],
        states={
            ONBOARDING_DEMO: [
                CallbackQueryHandler(
                    onboarding_demo_handler, pattern=rf"^{CallbackType.ONBOARDING.value}:(demo|skip_demo)$"
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    onboarding_demo_process,
                ),
                MessageHandler(
                    filters.VOICE,
                    onboarding_demo_process,
                ),
            ],
            ONBOARDING_CATEGORY_CHOICES: [
                CallbackQueryHandler(
                    onboarding_category_choice, pattern=rf"^{CallbackType.ONBOARDING.value}:(toggle|next).*$"
                )
            ],
            ONBOARDING_CUSTOM_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    onboarding_custom_categories,
                )
            ],
            ONBOARDING_COMPLETE: [
                CallbackQueryHandler(
                    onboarding_finish, pattern=rf"^{CallbackType.ONBOARDING.value}:finish$"
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", onboarding_finish),
        ],
        per_chat=True,
        allow_reentry=True,
    )


def _build_expense_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("gasto", start_expense),
            MessageHandler(filters.Regex(r"^💸 Registrar Gasto$"), start_expense),
        ],
        states={
            EXPENSE_AMOUNT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    expense_amount_received,
                )
            ],
            EXPENSE_CATEGORY: [
                CallbackQueryHandler(
                    expense_category_selected, pattern=rf"^{CallbackType.CATEGORY.value}:\d+$"
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    expense_description_received,
                ),
            ],
            EXPENSE_DESCRIPTION_DECISION: [
                CallbackQueryHandler(
                    expense_description_decision,
                    pattern=rf"^{CallbackType.EXPENSE_DESC.value}:(yes|no)$",
                )
            ],
            EXPENSE_DESCRIPTION_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    expense_description_received,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_transaction)],
    )


def _build_income_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("ingreso", start_income),
            MessageHandler(filters.Regex(r"^💰 Registrar Ingreso$"), start_income),
        ],
        states={
            INCOME_AMOUNT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    income_amount_received,
                )
            ],
            INCOME_CATEGORY: [
                CallbackQueryHandler(
                    income_category_selected, pattern=rf"^{CallbackType.CATEGORY.value}:\d+$"
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    income_description_received,
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_transaction)],
    )


def _build_category_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("categorias", category_management_menu),
            CallbackQueryHandler(
                category_management_menu,
                pattern=rf"^{CallbackType.SETTINGS.value}:categories$",
            ),
        ],
        states={
            CATEGORY_MENU: [
                CallbackQueryHandler(
                    category_menu_selection, pattern=rf"^{CallbackType.CATEGORY_MANAGE.value}:"
                ),
                CallbackQueryHandler(
                    category_delete_selected, pattern=rf"^{CallbackType.DELETE_CATEGORY.value}:\d+$"
                ),
            ],
            CATEGORY_ADD_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    category_add_name_received,
                )
            ],
            CATEGORY_ADD_TYPE: [
                CallbackQueryHandler(
                    category_add_type_selected, pattern=rf"^{CallbackType.CATEGORY_ADD_TYPE.value}:"
                )
            ],
            CATEGORY_RENAME_SELECT: [
                CallbackQueryHandler(
                    category_rename_selected, pattern=rf"^{CallbackType.RENAME_CATEGORY.value}:\d+$"
                ),
                CallbackQueryHandler(
                    category_delete_selected, pattern=rf"^{CallbackType.DELETE_CATEGORY.value}:\d+$"
                ),
            ],
            CATEGORY_RENAME_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    category_rename_name_received,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_category_management)],
    )


def _build_budget_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("presupuesto", start_budget),
            CallbackQueryHandler(start_budget, pattern=rf"^{CallbackType.BUDGETS.value}:create$"),
        ],
        states={
            BUDGET_CATEGORY_SELECT: [
                CallbackQueryHandler(
                    budget_category_selected, pattern=rf"^{CallbackType.BUDGET_CAT.value}:\d+$"
                )
            ],
            BUDGET_AMOUNT_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    budget_amount_received,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_budget_flow)],
    )


def _build_goal_creation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("crear_meta", start_goal_creation),
            CallbackQueryHandler(start_goal_creation, pattern=rf"^{CallbackType.GOALS.value}:create$"),
        ],
        states={
            GOAL_NAME_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    goal_name_received,
                )
            ],
            GOAL_TARGET_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    goal_target_received,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_goal_creation)],
    )


def _build_goal_contribution_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("aportar_meta", start_goal_contribution),
            CallbackQueryHandler(start_goal_contribution, pattern=rf"^{CallbackType.GOALS.value}:contribute$"),
        ],
        states={
            GOAL_CONTRIBUTION_SELECT: [
                CallbackQueryHandler(
                    goal_contribution_selected, pattern=rf"^{CallbackType.GOAL_CONTRIB.value}:\d+$"
                )
            ],
            GOAL_CONTRIBUTION_AMOUNT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    goal_contribution_amount_received,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_goal_contribution)],
    )


def build_application(bot_token: str) -> Application:
    application = ApplicationBuilder().token(bot_token).build()
    application.add_handler(TypeHandler(Update, debug_update), group=-1)
    application.add_error_handler(log_error)

    # CRÍTICO: Handlers de botones del menú principal DEBEN estar ANTES de ConversationHandlers
    # para que actúen como "comandos globales" que cancelan cualquier flujo activo
    application.add_handler(MessageHandler(filters.Regex(r"^📈 Dashboard$"), dashboard))
    application.add_handler(MessageHandler(filters.Regex(r"^📊 Reporte$"), monthly_report))
    application.add_handler(MessageHandler(filters.Regex(r"^🎯 Metas$"), goals_menu))
    application.add_handler(MessageHandler(filters.Regex(r"^⚙️ Ajustes$"), settings_menu))

    application.add_handler(_build_onboarding_handler())

    application.add_handler(CommandHandler("dashboard", dashboard))
    application.add_handler(CommandHandler("guia", user_guide))
    application.add_handler(CommandHandler("help", user_guide))

    application.add_handler(_build_expense_handler())
    application.add_handler(_build_income_handler())
    application.add_handler(_build_category_handler())
    application.add_handler(CommandHandler("ultimos", show_recent_transactions))
    application.add_handler(CommandHandler("reporte_mes", monthly_report))
    application.add_handler(CommandHandler("exportar", export_transactions))
    application.add_handler(_build_budget_handler())
    application.add_handler(CommandHandler("ver_presupuesto", view_budgets))
    application.add_handler(_build_goal_creation_handler())
    application.add_handler(_build_goal_contribution_handler())
    application.add_handler(
        CallbackQueryHandler(
            view_budgets,
            pattern=rf"^{CallbackType.BUDGETS.value}:view$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            delete_transaction_callback,
            pattern=rf"^{CallbackType.DELETE_TRANSACTION.value}:\d+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            settings_reset_prompt,
            pattern=rf"^{CallbackType.SETTINGS.value}:reset$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            settings_reset_confirm,
            pattern=rf"^{CallbackType.SETTINGS.value}:confirm_reset$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            settings_reset_cancel,
            pattern=rf"^{CallbackType.SETTINGS.value}:cancel_reset$",
        )
    )
    # New settings menu handlers
    application.add_handler(
        CallbackQueryHandler(
            settings_export_handler,
            pattern=rf"^{CallbackType.SETTINGS.value}:export$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            settings_delete_recent_handler,
            pattern=rf"^{CallbackType.SETTINGS.value}:delete_recent$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            settings_quick_stats,
            pattern=rf"^{CallbackType.SETTINGS.value}:quick_stats$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            settings_change_currency,
            pattern=rf"^{CallbackType.SETTINGS.value}:change_currency$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            settings_currency_selected,
            pattern=rf"^{CallbackType.SETTINGS.value}:currency:[A-Z]{{3}}$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            settings_gamification,
            pattern=rf"^{CallbackType.SETTINGS.value}:gamification$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            settings_back_to_menu,
            pattern=rf"^{CallbackType.SETTINGS.value}:back_to_menu$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            settings_back,
            pattern=rf"^{CallbackType.SETTINGS.value}:back$",
        )
    )
    # settings_categories ahora se maneja como entry point del ConversationHandler de categorías
    application.add_handler(
        CallbackQueryHandler(
            settings_guide_handler,
            pattern=rf"^{CallbackType.SETTINGS.value}:guide$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            settings_budgets_handler,
            pattern=rf"^{CallbackType.SETTINGS.value}:budgets$",
        )
    )
    
    # Photo handler for OCR - before text handler but after conversation handlers
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo_message,
        )
    )
    
    # Voice handler for speech-to-text - before text handler but after conversation handlers
    application.add_handler(
        MessageHandler(
            filters.VOICE,
            handle_voice_message,
        )
    )
    
    # Natural language handler - MUST be last to avoid interfering with conversation flows
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text_message,
        )
    )
    
    return application


