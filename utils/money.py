from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# Global money settings (2 decimal places like INR)
MONEY_PLACES = Decimal("0.01")

def to_decimal(value) -> Decimal:
    """
    Convert a user input or DB numeric into Decimal safely.
    Accepts str/int/float/Decimal. We convert float via str(float) to reduce float artifacts.
    """
    if value is None:
        raise ValueError("Amount is required.")

    if isinstance(value, Decimal):
        return value

    # IMPORTANT: floats are unsafe; convert through str
    if isinstance(value, float):
        value = str(value)

    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ValueError("Please enter a valid amount.")

def quantize_money(amount: Decimal) -> Decimal:
    """
    Round to 2 decimal places using bankers-friendly rounding.
    """
    return amount.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)

def parse_money(amount_raw: str) -> Decimal:
    """
    Parse and validate user input.
    """
    amount = quantize_money(to_decimal(amount_raw))
    if amount <= 0:
        raise ValueError("Amount must be greater than 0.")
    return amount

def fmt_money(amount: Decimal) -> str:
    """
    For UI messages: always show 2 decimal places.
    """
    return f"{quantize_money(to_decimal(amount)):.2f}"