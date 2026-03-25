from django import template

register = template.Library()


@register.filter
def dict_key(d, key):
    """Return d[key] — used to look up sub-items by indent_item.pk in template."""
    if d is None:
        return []
    return d.get(key, [])
