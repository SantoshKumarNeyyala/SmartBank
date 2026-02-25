from decimal import Decimal
from utils.money import parse_money

def parse_positive_amount(amount_raw: str) -> Decimal:
    return parse_money(amount_raw)