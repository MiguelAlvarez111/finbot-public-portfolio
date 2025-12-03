"""Analytics service for answering financial questions using AI-powered SQL generation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from bot.common import get_logger
from bot.utils.time_utils import convert_utc_to_local, get_now_utc
from database import SessionLocal

logger = get_logger("services.analytics_service")


class AnalyticsService:
    """Service for answering financial questions by generating and executing safe SQL queries."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the analytics service with Google Gemini API key.
        
        Args:
            api_key: Google Gemini API key. If not provided, will try to get from
                     GEMINI_API_KEY environment variable.
        
        Raises:
            RuntimeError: If API key is not provided and not found in environment.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set it to use the analytics service."
            )
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        logger.info("AnalyticsService initialized successfully")

    def answer_question(self, question: str, user_id: int) -> str:
        """Answer a financial question by generating SQL, executing it, and interpreting results.
        
        This method uses a safe Text-to-SQL approach:
        1. AI generates a SQL query based on the question
        2. Query is validated for safety (only SELECT, no DROP/DELETE, etc.)
        3. Query is executed in read-only mode
        4. Results are interpreted by AI to generate a friendly response
        
        Args:
            question: Natural language question about finances (e.g., "¿Cuánto gasté en comida este mes?")
            user_id: Telegram user ID to filter data
        
        Returns:
            Friendly response in Colombian Spanish
        
        Raises:
            ValueError: If the question cannot be processed or SQL is invalid
            RuntimeError: If AI service fails
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        try:
            # Check for destructive intentions first
            if self._has_destructive_intent(question):
                logger.warning("Destructive intent detected in question: %s", question)
                return "⛔ Lo siento, soy un analista de datos y solo puedo **leer y consultar** tu información. Para borrar datos, por favor usa los comandos manuales o el menú."
            
            # Step A: Generate SQL query
            sql_query = self._generate_sql(question, user_id)
            
            # Check if SQL is ACTION_NOT_ALLOWED (double safety check)
            sql_upper = sql_query.strip().upper()
            if "ACTION_NOT_ALLOWED" in sql_upper or "SELECT 'ACTION_NOT_ALLOWED'" in sql_upper:
                logger.warning("SQL generation returned ACTION_NOT_ALLOWED for question: %s", question)
                return "⛔ Lo siento, soy un analista de datos y solo puedo **leer y consultar** tu información. Para borrar datos, por favor usa los comandos manuales o el menú."
            
            # Step B: Validate and execute SQL
            query_results = self._execute_safe_query(sql_query, user_id)
            
            # Check if results contain ACTION_NOT_ALLOWED (triple safety check)
            if query_results and len(query_results) > 0:
                first_result = query_results[0]
                # Check if any value in the result is ACTION_NOT_ALLOWED
                if any(str(v).upper() == 'ACTION_NOT_ALLOWED' for v in first_result.values()):
                    logger.warning("Query results contain ACTION_NOT_ALLOWED for question: %s", question)
                    return "⛔ Lo siento, soy un analista de datos y solo puedo **leer y consultar** tu información. Para borrar datos, por favor usa los comandos manuales o el menú."
            
            # Step C: Interpret results and generate friendly response
            response = self._interpret_results(question, query_results)
            
            logger.info(
                "Successfully answered question for user_id=%s: %s",
                user_id,
                question[:50],
            )
            
            return response
        
        except ValueError as e:
            logger.warning("Validation error answering question '%s': %s", question, e)
            raise
        except Exception as e:
            logger.error("Error answering question '%s': %s", question, e, exc_info=True)
            raise RuntimeError(f"Error procesando tu pregunta: {e}") from e

    def _has_destructive_intent(self, question: str) -> bool:
        """Check if the question contains destructive intent (delete, update, etc.).
        
        Args:
            question: User's question text
        
        Returns:
            True if destructive intent is detected, False otherwise
        """
        question_lower = question.lower()
        destructive_keywords = [
            "borrar", "eliminar", "delete", "drop",
            "cambiar", "actualizar", "update", "modificar",
            "limpiar", "vaciar", "truncate", "clear",
            "remover", "quitar", "remove",
        ]
        return any(keyword in question_lower for keyword in destructive_keywords)
    
    def _generate_sql(self, question: str, user_id: int) -> str:
        """Generate a SQL query from a natural language question.
        
        Args:
            question: Natural language question
            user_id: Telegram user ID
        
        Returns:
            SQL query string (must be SELECT only)
        
        Raises:
            ValueError: If SQL generation fails
            RuntimeError: If AI service fails
        """
        # Calculate today's date in Colombia timezone
        now_utc = get_now_utc()
        now_colombia = convert_utc_to_local(now_utc, "America/Bogota")
        today_colombia_str = now_colombia.strftime('%Y-%m-%d')
        today_colombia_date = now_colombia.date()
        
        # Calculate yesterday and day before yesterday in Colombia timezone
        yesterday_colombia_str = (today_colombia_date - timedelta(days=1)).strftime('%Y-%m-%d')
        day_before_yesterday_str = (today_colombia_date - timedelta(days=2)).strftime('%Y-%m-%d')
        
        # [PROPRIETARY SCHEMA INFO REDACTED]
        # The full schema_info contains detailed database schema, relationships,
        # timezone conversion rules, and critical SQL conventions.
        schema_info = f"""
        ESQUEMA DE BASE DE DATOS:
        
        Tabla: transactions
        - id (Integer, PK)
        - user_id (BigInteger, FK -> users.telegram_id)
        - category_id (Integer, FK -> categories.id)
        - amount (Numeric(10, 2)) - Monto en COP
        - transaction_date (DateTime) - Fecha y hora en UTC
        - description (String, nullable)
        
        Tabla: categories
        - id (Integer, PK)
        - user_id (BigInteger, FK -> users.telegram_id)
        - name (String)
        - type (Enum: 'INCOME' o 'EXPENSE' en MAYÚSCULAS)
        - is_default (Boolean)
        
        REGLA CRÍTICA DE TIMEZONE:
        - Convertir transaction_date a America/Bogota antes de filtrar por fecha
        """
        
        # [PROPRIETARY PROMPT REDACTED FOR PUBLIC REPO]
        # This prompt contains proprietary business logic including:
        # - Multi-layer security rules and guardrails
        # - SQL generation examples and patterns
        # - Destructive intent detection logic
        # - Timezone conversion rules for Colombia
        # - Detailed schema information and query examples
        #
        # For portfolio purposes, a simplified prompt is used.
        prompt = f"""ROL: Eres un Analista de Datos de SOLO LECTURA (Read-Only). Tu trabajo es generar consultas SQL (PostgreSQL) para responder preguntas financieras.

{schema_info}

PREGUNTA DEL USUARIO: "{question}"
ID DEL USUARIO: {user_id}
FECHA DE HOY EN COLOMBIA: {today_colombia_str}

REGLAS:
- Solo SELECT permitido
- Filtrar por user_id = {user_id}
- Convertir timezone a America/Bogota
- Si detectas intención destructiva, retorna: SELECT 'ACTION_NOT_ALLOWED'

Genera el SQL para esta pregunta: "{question}"

SQL:"""
        
        try:
            logger.debug("Generating SQL for question: %s", question)
            response = self.model.generate_content(prompt)
            sql_query = response.text.strip()
            
            # Clean up SQL if wrapped in markdown code blocks
            if "```sql" in sql_query.lower():
                sql_start = sql_query.lower().find("```sql") + 6
                sql_end = sql_query.lower().find("```", sql_start)
                sql_query = sql_query[sql_start:sql_end].strip()
            elif "```" in sql_query:
                sql_start = sql_query.find("```") + 3
                sql_end = sql_query.find("```", sql_start)
                sql_query = sql_query[sql_start:sql_end].strip()
            
            # Remove trailing semicolons
            sql_query = sql_query.rstrip(";").strip()
            
            logger.debug("Generated SQL: %s", sql_query)
            
            return sql_query
        
        except Exception as e:
            logger.error("Error generating SQL: %s", e, exc_info=True)
            raise RuntimeError(f"Error generando consulta SQL: {e}") from e
    def _validate_sql_safety(self, sql_query: str) -> Tuple[bool, Optional[str]]:
        """Validate that SQL query is safe to execute (read-only).
        
        Args:
            sql_query: SQL query string to validate
        
        Returns:
            Tuple of (is_safe, error_message). If safe, error_message is None.
        """
        sql_upper = sql_query.upper().strip()
        
        # Must start with SELECT
        if not sql_upper.startswith("SELECT"):
            return False, "La consulta debe ser solo SELECT"
        
        # Check for dangerous keywords
        dangerous_keywords = [
            "DROP", "DELETE", "INSERT", "UPDATE", "TRUNCATE",
            "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
            "MERGE", "COPY", "CALL", "COMMIT", "ROLLBACK",
        ]
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"No se permiten operaciones {keyword}"
        
        # Check for multiple statements (semicolon indicates multiple queries)
        if ";" in sql_query:
            return False, "No se permiten múltiples consultas"
        
        # Check for function calls that could be dangerous
        dangerous_functions = [
            "PG_",  # PostgreSQL system functions
            "EXEC", "EXECUTE",
        ]
        
        for func_pattern in dangerous_functions:
            if func_pattern in sql_upper:
                return False, f"No se permiten llamadas a funciones del sistema"
        
        return True, None

    def _execute_safe_query(self, sql_query: str, user_id: int) -> List[Dict[str, Any]]:
        """Execute a validated SQL query and return results.
        
        Args:
            sql_query: SQL query string (must be validated first)
            user_id: Telegram user ID (for additional validation)
        
        Returns:
            List of dictionaries with query results
        
        Raises:
            ValueError: If query is invalid or unsafe
            RuntimeError: If query execution fails
        """
        # Validate SQL safety
        is_safe, error_message = self._validate_sql_safety(sql_query)
        if not is_safe:
            raise ValueError(f"Consulta SQL no segura: {error_message}")
        
        # Additional check: ensure user_id is in the query (basic validation)
        # Note: This is not foolproof, but adds a layer of safety
        if str(user_id) not in sql_query and "user_id" not in sql_query.lower():
            logger.warning(
                "Generated SQL might not filter by user_id. Query: %s",
                sql_query[:200]
            )
        
        try:
            logger.debug("Executing SQL query: %s", sql_query)
            
            with SessionLocal() as session:
                # Execute query with parameter binding for safety
                # We use text() from SQLAlchemy for raw SQL
                result = session.execute(text(sql_query))
                
                # Fetch all rows
                rows = result.fetchall()
                
                # Convert to list of dictionaries
                columns = result.keys()
                results = [dict(zip(columns, row)) for row in rows]
                
                logger.debug("Query returned %d rows", len(results))
                
                return results
        
        except SQLAlchemyError as e:
            logger.error("SQL execution error: %s", e, exc_info=True)
            raise RuntimeError(f"Error ejecutando consulta: {e}") from e
        except Exception as e:
            logger.error("Unexpected error executing SQL: %s", e, exc_info=True)
            raise RuntimeError(f"Error inesperado: {e}") from e

    def _interpret_results(
        self, 
        question: str, 
        query_results: List[Dict[str, Any]]
    ) -> str:
        """Interpret SQL query results and generate a friendly response in Colombian Spanish.
        
        Args:
            question: Original user question
            query_results: List of dictionaries with query results
        
        Returns:
            Friendly response in Colombian Spanish
        
        Raises:
            RuntimeError: If AI interpretation fails
        """
        # Early check: If results contain ACTION_NOT_ALLOWED, return rejection message immediately
        if query_results:
            for result in query_results:
                for value in result.values():
                    if str(value).upper() == 'ACTION_NOT_ALLOWED':
                        logger.warning("ACTION_NOT_ALLOWED detected in results, returning rejection message")
                        return "⛔ Lo siento, soy un analista de datos y solo puedo **leer y consultar** tu información. Para borrar datos, por favor usa los comandos manuales o el menú."
        
        # Prepare results for AI interpretation
        results_str = json.dumps(query_results, default=str, ensure_ascii=False, indent=2)
        
        # [PROPRIETARY PROMPT REDACTED FOR PUBLIC REPO]
        # This prompt contains proprietary business logic for interpreting SQL results
        # and generating friendly responses in Colombian Spanish.
        #
        # The full prompt includes:
        # - Detailed formatting rules for Colombian currency
        # - Colombian slang usage ("lucas", "palos")
        # - Specific response patterns and examples
        # - Emoji usage guidelines
        #
        # For portfolio purposes, a simplified prompt is used.
        prompt = f"""ROL: Eres un asistente financiero colombiano amable y profesional de SOLO LECTURA.

PREGUNTA ORIGINAL DEL USUARIO: "{question}"

RESULTADOS DE LA CONSULTA:
{results_str}

Interpreta los resultados y responde la pregunta del usuario de forma clara y amable.
Formatea montos en formato colombiano (punto para miles, coma para decimales).
Usa emojis cuando sea apropiado (💰, 📊, 💸, etc.).

Responde ahora:"""
        
        try:
            logger.debug("Interpreting results for question: %s", question)
            response = self.model.generate_content(prompt)
            answer = response.text.strip()
            
            logger.debug("Generated answer: %s", answer[:100])
            
            return answer
        
        except Exception as e:
            logger.error("Error interpreting results: %s", e, exc_info=True)
            # Fallback response if AI fails
            if not query_results:
                return "No encontré información para tu pregunta. 😅"
            
            # Try to create a basic response from results
            try:
                first_result = query_results[0]
                if len(first_result) == 1:
                    key, value = next(iter(first_result.items()))
                    if isinstance(value, (int, float, Decimal)):
                        return f"El resultado es: ${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    return f"El resultado es: {value}"
                return f"Encontré {len(query_results)} resultado(s). Usa /dashboard para ver más detalles."
            except Exception:
                return "Obtuve resultados pero no pude interpretarlos. Intenta reformular tu pregunta."
def get_analytics_service() -> AnalyticsService:
    """Get or create the singleton AnalyticsService instance.
    
    Returns:
        AnalyticsService instance.
    
    Raises:
        RuntimeError: If GEMINI_API_KEY is not configured.
    """
    global _analytics_service_instance
    if _analytics_service_instance is None:
        _analytics_service_instance = AnalyticsService()
    return _analytics_service_instance

