from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Gets an item from a dictionary by key."""
    return dictionary.get(key)


@register.filter
def subtract(value, arg):
    """Subtracts arg from value."""
    try:
        return value - arg
    except (TypeError, ValueError):
        return value
