#!/usr/bin/env python3
"""
Script para preparar una versión pública y segura del repositorio para portafolio.

Este script:
1. Copia el proyecto a ../finbot-public-portfolio
2. Filtra archivos sensibles (no copia)
3. Sanitiza prompts de IA en archivos específicos
4. Crea .env.example con placeholders
"""

import os
import re
import shutil
import sys
from pathlib import Path
from typing import Set

# Colores para output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a header message."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


# Directorios y archivos a ignorar
IGNORED_PATTERNS: Set[str] = {
    '.git',
    '.env',
    'venv',
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '*.log',
    '*.db',
    '*.sqlite',
    'google_credentials.json',
    '*.save',
}

# Archivos específicos a ignorar
IGNORED_FILES: Set[str] = {
    'scripts/seed_prod_direct.py',
}

# Archivos que requieren sanitización
FILES_TO_SANITIZE: Set[str] = {
    'bot/services/ai_service.py',
    'bot/services/analytics_service.py',
}


def should_ignore(path: Path, root: Path) -> bool:
    """Check if a path should be ignored."""
    rel_path = path.relative_to(root)
    rel_str = str(rel_path)
    
    # Check specific files
    if rel_str in IGNORED_FILES:
        return True
    
    # Check patterns
    for pattern in IGNORED_PATTERNS:
        if pattern.startswith('*.'):
            # File extension pattern
            if path.name.endswith(pattern[1:]):
                return True
        elif pattern in path.parts:
            # Directory or file name pattern
            return True
    
    return False


def replace_function_block(content: str, function_name: str, new_code: str) -> str:
    """Replace a complete function block with new code.
    
    Finds the function from 'def function_name(...):' until the next function/class or end of file.
    Uses indentation to determine function boundaries.
    
    Args:
        content: Original file content
        function_name: Name of the function to replace (e.g., '_build_image_prompt')
        new_code: Complete replacement code (must be valid Python)
    
    Returns:
        Content with function replaced
    """
    # Find the start of the function definition
    # Search for "def function_name(" - this handles both single-line and multiline definitions
    func_start_pattern = rf'def {re.escape(function_name)}\s*\('
    match = re.search(func_start_pattern, content)
    
    if not match:
        print_warning(f"Function {function_name} not found in content")
        return content
    
    start_pos = match.start()
    
    # Find the end of the function definition (the colon after the closing paren)
    # Handle multiline function definitions by counting parentheses
    remaining = content[start_pos:]
    paren_count = 0
    found_colon = False
    def_end_pos = 0
    
    for i, char in enumerate(remaining):
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
            if paren_count == 0:
                # Found matching closing paren, now look for colon (may have type hints -> str:)
                j = i + 1
                while j < len(remaining):
                    if remaining[j] == ':':
                        found_colon = True
                        def_end_pos = start_pos + j + 1
                        break
                    elif remaining[j] not in ' \t\n->':
                        # Unexpected character, break
                        break
                    j += 1
                if found_colon:
                    break
    
    if not found_colon:
        print_warning(f"Could not find complete function definition for {function_name}")
        return content
    
    # Now find where the function body ends by looking at indentation
    # Get the indentation level of the function definition
    func_def_start_line = content[:start_pos].rfind('\n') + 1
    func_def_line = content[func_def_start_line:def_end_pos]
    func_indent = len(func_def_line) - len(func_def_line.lstrip())
    
    # Find the next line that starts a new function/class at same or less indentation
    lines_after_def = content[def_end_pos:].split('\n')
    end_pos = def_end_pos
    found_end = False
    
    for i, line in enumerate(lines_after_def):
        stripped = line.lstrip()
        if not stripped:  # Empty line, continue
            end_pos += len(line) + 1  # +1 for newline
            continue
        
        line_indent = len(line) - len(stripped)
        
        # Check if this line starts a new function or class at same or less indentation
        if (line_indent <= func_indent and 
            (stripped.startswith('def ') or stripped.startswith('class '))):
            found_end = True
            break
        
        end_pos += len(line) + 1  # +1 for newline
    
    if not found_end:
        # Function goes to end of file
        end_pos = len(content)
    
    # Get the indentation of the function definition line in the original
    # Find the start of the line containing the function definition
    func_def_line_start = content[:start_pos].rfind('\n') + 1
    if func_def_line_start > 0:
        # Get the part of the line before "def function_name"
        line_prefix = content[func_def_line_start:start_pos]
        original_base_indent = len(line_prefix) - len(line_prefix.lstrip())
    else:
        original_base_indent = 0
    
    # Get the indentation of the first line in the template
    new_code_lines = new_code.split('\n')
    if new_code_lines:
        first_non_empty = next((line for line in new_code_lines if line.strip()), None)
        if first_non_empty:
            template_base_indent = len(first_non_empty) - len(first_non_empty.lstrip())
            # Calculate the difference
            indent_diff = original_base_indent - template_base_indent
            
            if indent_diff != 0:
                # Adjust all lines by the difference, preserving relative indentation
                adjusted_lines = []
                for line in new_code_lines:
                    if line.strip():
                        # Preserve the original indent and add the difference
                        current_indent = len(line) - len(line.lstrip())
                        adjusted_lines.append(' ' * (current_indent + indent_diff) + line.lstrip())
                    else:
                        adjusted_lines.append('')
                new_code = '\n'.join(adjusted_lines)
    
    # Replace the function block
    # Use func_def_line_start instead of start_pos to include the indentation
    # But we need to find where the function definition line actually starts
    func_def_line_start = content[:start_pos].rfind('\n') + 1
    before = content[:func_def_line_start]
    after = content[end_pos:]
    
    print_success(f"Replaced function {function_name}")
    
    return before + new_code + after


def sanitize_ai_service(content: str) -> str:
    """Sanitize prompts in ai_service.py by replacing entire function blocks."""
    print_info("Sanitizing ai_service.py...")
    
    # Template for _build_image_prompt
    image_prompt_template = '''    def _build_image_prompt(
        self,
        expense_categories: List[Dict],
        income_categories: List[Dict],
        today_date: date
    ) -> str:
        """Build the prompt for analyzing receipt/bill images."""
        # [PROPRIETARY PROMPT REDACTED FOR PUBLIC REPO]
        # This prompt contains proprietary business logic including:
        # - Colombian slang and monetary expressions ("k", "lucas", "barras", "palos")
        # - Semantic categorization rules for receipts
        # - Timezone handling for Colombia
        # - Detailed extraction instructions for OCR of receipts/bills
        #
        # For portfolio purposes, a generic prompt is used.
        prompt = os.getenv("AI_IMAGE_PROMPT", "Extract transaction data from receipt image. Return JSON with amount, category_id, description, type, and date.")
        return prompt

'''
    
    # Template for _build_audio_prompt
    audio_prompt_template = '''    def _build_audio_prompt(
        self,
        expense_categories: List[Dict],
        income_categories: List[Dict],
        today_date: date
    ) -> str:
        """Build the prompt for analyzing voice messages with speech-to-text."""
        # [PROPRIETARY PROMPT REDACTED FOR PUBLIC REPO]
        # This prompt contains proprietary business logic including:
        # - Colombian slang and monetary expressions ("k", "lucas", "barras", "palos")
        # - Semantic categorization rules
        # - Timezone handling for Colombia
        # - Speech-to-text transcription with Colombian context
        # - Detailed extraction instructions for audio messages
        #
        # For portfolio purposes, a generic prompt is used.
        prompt = os.getenv("AI_AUDIO_PROMPT", "Extract transaction data from audio transcription. Return JSON with amount, category_id, description, type, and date.")
        return prompt

'''
    
    # Template for _build_prompt
    text_prompt_template = '''    def _build_prompt(
        self, 
        text: str, 
        expense_categories: List[Dict], 
        income_categories: List[Dict],
        today_date: date
    ) -> str:
        """Build the prompt for the AI model with Colombian context."""
        # [PROPRIETARY PROMPT REDACTED FOR PUBLIC REPO]
        # This prompt contains proprietary business logic including:
        # - Colombian slang and monetary expressions ("k", "lucas", "barras", "palos")
        # - Semantic categorization rules
        # - Timezone handling for Colombia
        # - Relative date parsing ("ayer", "antier", "hoy")
        # - Detailed extraction instructions for natural language text
        #
        # For portfolio purposes, a generic prompt is used.
        prompt = os.getenv("AI_TEXT_PROMPT", "Extract transaction data from natural language text. Return JSON with amount, category_id, description, type, and date.")
        return prompt

'''
    
    # Replace each function
    content = replace_function_block(content, '_build_image_prompt', image_prompt_template)
    content = replace_function_block(content, '_build_audio_prompt', audio_prompt_template)
    content = replace_function_block(content, '_build_prompt', text_prompt_template)
    
    return content


def sanitize_analytics_service(content: str) -> str:
    """Sanitize prompts in analytics_service.py by replacing entire function blocks."""
    print_info("Sanitizing analytics_service.py...")
    
    # Template for _generate_sql
    generate_sql_template = '''    def _generate_sql(self, question: str, user_id: int) -> str:
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
'''
    
    # Template for _interpret_results
    interpret_results_template = '''    def _interpret_results(
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
'''
    
    # Replace each function
    content = replace_function_block(content, '_generate_sql', generate_sql_template)
    content = replace_function_block(content, '_interpret_results', interpret_results_template)
    
    return content


def sanitize_file(file_path: Path, project_root: Path) -> None:
    """Sanitize a specific file by replacing sensitive prompts.
    
    Args:
        file_path: Absolute path to the file to sanitize
        project_root: Absolute path to the project root (for relative path calculation)
    """
    # Calculate relative path from project root using pathlib for cross-platform compatibility
    try:
        rel_path = file_path.relative_to(project_root)
        rel_str = str(rel_path).replace('\\', '/')  # Normalize path separators
    except ValueError:
        # If file_path is not relative to project_root, try to find it in FILES_TO_SANITIZE
        rel_str = None
        for sanitize_path in FILES_TO_SANITIZE:
            if file_path.name in sanitize_path or str(file_path).endswith(sanitize_path.replace('/', os.sep)):
                rel_str = sanitize_path
                break
        
        if rel_str is None:
            return
    
    if rel_str not in FILES_TO_SANITIZE:
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'bot/services/ai_service.py' in rel_str:
            content = sanitize_ai_service(content)
        elif 'bot/services/analytics_service.py' in rel_str:
            content = sanitize_analytics_service(content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print_success(f"Sanitized {rel_str}")
    except Exception as e:
        print_error(f"Error sanitizing {rel_str}: {e}")


def copy_project(src: Path, dst: Path) -> None:
    """Copy project files to destination, filtering ignored files."""
    if dst.exists():
        response = input(f"\n{Colors.WARNING}Destination {dst} already exists. Delete and recreate? (y/N): {Colors.ENDC}")
        if response.lower() != 'y':
            print_error("Operation cancelled.")
            sys.exit(1)
        shutil.rmtree(dst)
        print_success(f"Removed existing {dst}")
    
    dst.mkdir(parents=True, exist_ok=True)
    
    copied_files = 0
    ignored_files = 0
    
    print_header(f"Copying files from {src} to {dst}...")
    
    for root, dirs, files in os.walk(src):
        root_path = Path(root)
        rel_root = root_path.relative_to(src)
        dst_root = dst / rel_root
        
        # Filter directories to ignore
        dirs[:] = [d for d in dirs if not should_ignore(root_path / d, src)]
        
        # Create destination directory if needed
        if not should_ignore(root_path, src):
            dst_root.mkdir(parents=True, exist_ok=True)
        
        # Copy files
        for file in files:
            file_path = root_path / file
            if should_ignore(file_path, src):
                ignored_files += 1
                continue
            
            dst_file = dst_root / file
            try:
                shutil.copy2(file_path, dst_file)
                copied_files += 1
            except Exception as e:
                print_error(f"Error copying {file_path}: {e}")
    
    print_success(f"Copied {copied_files} files")
    print_info(f"Ignored {ignored_files} files/directories")
    
    # Sanitize files in destination
    print_header("Sanitizing sensitive files...")
    for rel_path in FILES_TO_SANITIZE:
        file_path = dst / rel_path
        if file_path.exists():
            sanitize_file(file_path, dst)
        else:
            print_warning(f"File not found: {rel_path}")


def create_env_example(dst: Path) -> None:
    """Create .env.example file with placeholders."""
    print_header("Creating .env.example...")
    
    env_example = """# Telegram Bot Configuration
TELEGRAM_TOKEN=your_telegram_token_here

# Webhook Configuration
WEBHOOK_URL=https://your-domain.com
WEBHOOK_PATH=telegram-webhook
PORT=8000

# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/dbname

# Dashboard Configuration
SECRET_KEY=your_secret_key_here
DASHBOARD_URL=https://your-dashboard-domain.com

# AI Service Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Custom AI Prompts (if using sanitized version)
# AI_SYSTEM_PROMPT=your_custom_prompt_here
# AI_IMAGE_PROMPT=your_custom_image_prompt_here
# AI_AUDIO_PROMPT=your_custom_audio_prompt_here
# AI_TEXT_PROMPT=your_custom_text_prompt_here
"""
    
    env_file = dst / '.env.example'
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_example)
    
    print_success("Created .env.example")


def create_readme_note(dst: Path) -> None:
    """Create a note about sanitization in the public repo."""
    print_header("Creating sanitization note...")
    
    note = """# ⚠️ Public Repository Notice

This is a **sanitized version** of the FinBot AI 2.0 repository prepared for portfolio purposes.

## What Was Removed/Sanitized

1. **Credential Files**: `.env`, `google_credentials.json`, database files
2. **Production Scripts**: `scripts/seed_prod_direct.py` (contains production credentials)
3. **AI Prompts**: Proprietary prompts in `bot/services/ai_service.py` and `bot/services/analytics_service.py` have been replaced with generic versions or environment variable placeholders.

## Proprietary Content

The following proprietary content has been redacted:
- **Colombian slang and monetary expressions** ("k", "lucas", "barras", "palos")
- **Semantic categorization rules** for transactions
- **Detailed security guardrails** for SQL generation
- **Timezone handling logic** specific to Colombia
- **Complete AI prompts** for OCR, STT, and text parsing

## Setup

1. Copy `.env.example` to `.env` and fill in your credentials
2. Install dependencies: `pip install -r requirements.txt`
3. Set up database and run migrations: `alembic upgrade head`
4. Run the bot: `python main.py`

## Note

The actual production prompts and business logic are kept in a private repository. This public version demonstrates the architecture, patterns, and structure of the project.
"""
    
    note_file = dst / 'PUBLIC_REPO_NOTICE.md'
    with open(note_file, 'w', encoding='utf-8') as f:
        f.write(note)
    
    print_success("Created PUBLIC_REPO_NOTICE.md")


def main():
    """Main function."""
    print_header("=" * 60)
    print_header("FinBot AI - Public Repository Preparation Script")
    print_header("=" * 60)
    
    # Get project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    dest_root = project_root.parent / 'finbot-public-portfolio'
    
    print_info(f"Source: {project_root}")
    print_info(f"Destination: {dest_root}")
    
    try:
        # Copy project
        copy_project(project_root, dest_root)
        
        # Create .env.example
        create_env_example(dest_root)
        
        # Create notice file
        create_readme_note(dest_root)
        
        print_header("=" * 60)
        print_success("Public repository prepared successfully!")
        print_header("=" * 60)
        print_info(f"Location: {dest_root}")
        print_info("\nNext steps:")
        print_info("1. Review the sanitized files in bot/services/")
        print_info("2. Verify that no sensitive data remains")
        print_info("3. Test that the code structure is intact")
        print_info("4. Initialize git repo if needed: cd ../finbot-public-portfolio && git init")
        
    except KeyboardInterrupt:
        print_error("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

