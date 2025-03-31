from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Template filter to access a dictionary value by key or index.

    Usage:
    {{ my_dict|get_item:key_name }}
    {{ my_list|get_item:index }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    elif isinstance(dictionary, (list, tuple)) and key < len(dictionary):
        return dictionary[key]
    return None
