from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary.
    Usage: {{ my_dict|get_item:key_var }}
    """
    if dictionary is None:
        return None

    # Convert key to string if it's not a string
    key = str(key)

    # Try to get the value
    return dictionary.get(key)
