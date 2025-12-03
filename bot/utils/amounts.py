"""Utility helpers for working with monetary amounts."""

from decimal import Decimal, InvalidOperation


def parse_amount(value: str) -> Decimal:
    """Parse a string into a decimal monetary amount."""
    normalized = value.replace(",", ".").strip()
    amount = Decimal(normalized)
    if amount <= 0:
        raise InvalidOperation("Amount must be positive.")
    return amount.quantize(Decimal("0.01"))


def format_currency(amount: Decimal | float | int | None) -> str:
    """Format a decimal amount in COP format (e.g., $1.500,50).
    
    Formats amounts with:
    - Thousands separator: '.' (dot)
    - Decimal separator: ',' (comma)
    - Currency symbol: '$' (peso colombiano)
    
    Args:
        amount: The amount to format. Can be Decimal, float, int, or None.
        
    Returns:
        Formatted string like "$1.500,50" or "$0,00" for None/invalid values.
    """
    if amount is None:
        amount = Decimal("0")
    
    try:
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        quantized = amount.quantize(Decimal("0.01"))
    except (ValueError, InvalidOperation):
        quantized = Decimal("0")
    
    # Handle negative sign separately
    is_negative = quantized < 0
    if is_negative:
        quantized = -quantized
    
    # Convert to string and split integer and decimal parts
    amount_str = str(quantized)
    if "." in amount_str:
        integer_part, decimal_part = amount_str.split(".")
    else:
        integer_part = amount_str
        decimal_part = "00"
    
    # Ensure decimal part has 2 digits
    decimal_part = decimal_part.ljust(2, "0")[:2]
    
    # Add thousands separator (dots) from right to left
    formatted_integer = ""
    for i, digit in enumerate(reversed(integer_part)):
        if i > 0 and i % 3 == 0:
            formatted_integer = "." + formatted_integer
        formatted_integer = digit + formatted_integer
    
    # Add negative sign before dollar sign if needed
    sign = "-" if is_negative else ""
    return f"{sign}${formatted_integer},{decimal_part}"


