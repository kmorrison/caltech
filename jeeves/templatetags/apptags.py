from django import template


register = template.Library()


@register.assignment_tag()
def resolve(lookup, target):
    try:
        return lookup[target]
    except KeyError:
        return None
