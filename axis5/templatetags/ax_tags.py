from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    """{{ my_dict|get_item:variable_key }}"""
    if isinstance(d, dict):
        return d.get(str(key), key)
    return key
