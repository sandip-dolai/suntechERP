from django import template
from decimal import Decimal
register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Gets an item from a dictionary by key."""
    return dictionary.get(key)


@register.filter
def multiply(value, arg):
    """Multiply two values"""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError, AttributeError):
        return None


@register.filter
def subtract(value, arg):
    """Subtracts arg from value."""
    try:
        return value - arg
    except (TypeError, ValueError):
        return value
