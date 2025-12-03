"""AI service for natural language transaction parsing using Google Gemini."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Dict, List, Optional

import google.generativeai as genai
from PIL import Image
from bot.common import get_logger
from bot.utils.time_utils import convert_utc_to_local
from models import Category, CategoryType

logger = get_logger("services.ai_service")


class AIService:
    """Service for parsing natural language transactions using Google Gemini AI."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the AI service with Google Gemini API key.
        
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
                "Please set it to use the AI service."
            )
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        logger.info("AIService initialized successfully")

    def parse_transaction(
        self, 
        text: str, 
        categories: List[Category], 
        transaction_date: Optional[date] = None,
        image_data: Optional[bytes] = None,
        audio_data: Optional[bytes] = None
    ) -> Dict[str, object]:
        """Parse a natural language transaction text, image, or audio into structured data.
        
        This method uses Google Gemini AI to extract:
        - amount: The transaction amount as a Decimal
        - category_id: The ID of the most appropriate category from the provided list
        - description: A cleaned description extracted from the text/image/audio
        - type: Either "expense" or "income" based on context
        - date: The transaction date in YYYY-MM-DD format
        
        Args:
            text: Natural language text describing the transaction (e.g., "Gaste 20k en comida ayer")
                  If image_data or audio_data is provided, this can be empty or used as additional context.
            categories: List of Category objects available to the user
            transaction_date: Optional reference date for relative date parsing. 
                            Defaults to today if not provided.
            image_data: Optional image bytes (e.g., from a photo of a receipt/bill)
            audio_data: Optional audio bytes (e.g., from a voice message)
        
        Returns:
            Dictionary with keys:
                - amount: Decimal - The transaction amount
                - category_id: int - The ID of the selected category
                - description: str - Extracted description (may be empty)
                - type: str - "expense" or "income"
                - date: str - Transaction date in YYYY-MM-DD format
        
        Raises:
            ValueError: If the AI response cannot be parsed or is invalid.
            RuntimeError: If the AI API call fails.
        """
        if not image_data and not audio_data and (not text or not text.strip()):
            raise ValueError("Either transaction text, image_data, or audio_data must be provided")
        
        if not categories:
            raise ValueError("At least one category must be provided")

        # Use today as reference date if not provided
        # Convert to Colombia timezone for proper date context
        if transaction_date is None:
            # Get current UTC time and convert to Colombia timezone
            now_utc = datetime.now(timezone.utc)
            now_colombia = convert_utc_to_local(now_utc, "America/Bogota")
            transaction_date = now_colombia.date()

        # Build categories context for the AI
        expense_categories = [
            {"id": cat.id, "name": cat.name}
            for cat in categories
            if cat.type == CategoryType.EXPENSE
        ]
        income_categories = [
            {"id": cat.id, "name": cat.name}
            for cat in categories
            if cat.type == CategoryType.INCOME
        ]

        # Create the prompt (different for images, audio, or text)
        if image_data:
            prompt = self._build_image_prompt(expense_categories, income_categories, transaction_date)
        elif audio_data:
            prompt = self._build_audio_prompt(expense_categories, income_categories, transaction_date)
        else:
            prompt = self._build_prompt(text, expense_categories, income_categories, transaction_date)

        try:
            if image_data:
                logger.debug("Sending image to Gemini API for OCR processing")
                # Load image from bytes
                image = Image.open(BytesIO(image_data))
                # Use Gemini's vision capability
                response = self.model.generate_content([prompt, image])
            elif audio_data:
                logger.debug("Sending audio to Gemini API for speech-to-text processing")
                # Use Gemini's audio capability with proper mime type
                content = [
                    prompt,
                    {"mime_type": "audio/ogg", "data": audio_data}
                ]
                response = self.model.generate_content(content)
            else:
                logger.debug("Sending request to Gemini API for text: %s", text)
                response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            # Parse JSON response
            parsed = json.loads(response_text)
            
            # Validate and normalize the response
            result = self._validate_and_normalize_response(parsed, categories)
            
            logger.info(
                "Successfully parsed transaction: amount=%s, category_id=%s, type=%s, date=%s",
                result["amount"],
                result["category_id"],
                result["type"],
                result["date"],
            )
            
            return result

        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI response as JSON: %s", response_text)
            raise ValueError(f"AI response is not valid JSON: {e}") from e
        except Exception as e:
            logger.error("Error calling Gemini API: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to parse transaction with AI: {e}") from e

    def _build_image_prompt(
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

    def _build_audio_prompt(
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

    def _build_prompt(
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

    def _format_categories(self, categories: List[Dict]) -> str:
        """Format categories list for the prompt."""
        if not categories:
            return "  (ninguna disponible)"
        return "\n".join(f"  - ID {cat['id']}: {cat['name']}" for cat in categories)

    def _validate_and_normalize_response(
        self, parsed: Dict, categories: List[Category]
    ) -> Dict[str, object]:
        """Validate and normalize the AI response."""
        # Validate required fields
        required_fields = ["amount", "category_id", "type", "description", "date"]
        for field in required_fields:
            if field not in parsed:
                raise ValueError(f"AI response missing required field: {field}")

        # Validate and convert amount
        try:
            amount = Decimal(str(parsed["amount"]))
            if amount <= 0:
                raise ValueError("Amount must be positive")
            # Quantize to 2 decimal places
            amount = amount.quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError) as e:
            raise ValueError(f"Invalid amount in AI response: {e}") from e

        # Validate category_id exists
        category_id = int(parsed["category_id"])
        category = next((c for c in categories if c.id == category_id), None)
        if not category:
            raise ValueError(
                f"Category ID {category_id} not found in user's categories"
            )

        # Validate type
        transaction_type = str(parsed["type"]).lower()
        if transaction_type not in ["expense", "income"]:
            raise ValueError(f"Invalid type: {transaction_type}. Must be 'expense' or 'income'")

        # Validate type matches category type
        expected_category_type = (
            CategoryType.EXPENSE if transaction_type == "expense" else CategoryType.INCOME
        )
        if category.type != expected_category_type:
            raise ValueError(
                f"Category {category.name} (ID: {category_id}) is of type {category.type.value}, "
                f"but transaction type is {transaction_type}"
            )

        # Validate and normalize date
        date_str = str(parsed["date"]).strip()
        try:
            # Parse date to validate format YYYY-MM-DD
            parsed_date = date.fromisoformat(date_str)
            # Ensure it's a reasonable date (not too far in past/future)
            today = date.today()
            if parsed_date > today:
                raise ValueError(f"Date {date_str} is in the future")
            # Allow dates up to 10 years in the past (reasonable for financial records)
            if parsed_date < (today - timedelta(days=3650)):
                raise ValueError(f"Date {date_str} is too far in the past")
            # Normalize to string format
            date_str = parsed_date.strftime("%Y-%m-%d")
        except ValueError as e:
            if "Invalid isoformat" in str(e) or "does not match format" in str(e):
                raise ValueError(
                    f"Invalid date format: {date_str}. Expected YYYY-MM-DD format"
                ) from e
            raise

        # Normalize description
        description = str(parsed.get("description", "")).strip()

        return {
            "amount": amount,
            "category_id": category_id,
            "description": description,
            "type": transaction_type,
            "date": date_str,
        }


    def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcribe audio to text using Google Gemini AI.
        
        This method uses Gemini's audio capabilities to convert voice messages
        to plain text transcription without any parsing or interpretation.
        
        Args:
            audio_bytes: Audio bytes (typically OGG format from Telegram voice messages)
        
        Returns:
            Transcribed text as a string
        
        Raises:
            RuntimeError: If the AI API call fails.
        """
        if not audio_bytes:
            raise ValueError("Audio bytes cannot be empty")
        
        prompt = "Transcribe este audio exactamente como fue dicho. Solo el texto."
        
        try:
            logger.debug("Transcribing audio to text")
            # Use Gemini's audio capability with proper mime type
            content = [
                prompt,
                {"mime_type": "audio/ogg", "data": audio_bytes}
            ]
            response = self.model.generate_content(content)
            
            transcribed_text = response.text.strip()
            logger.debug("Transcribed text: %s", transcribed_text[:100])
            
            return transcribed_text
        
        except Exception as e:
            logger.error("Error transcribing audio: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to transcribe audio: {e}") from e


# Singleton instance (lazy initialization)
_ai_service_instance: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create the singleton AIService instance.
    
    Returns:
        AIService instance.
    
    Raises:
        RuntimeError: If GEMINI_API_KEY is not configured.
    """
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance

