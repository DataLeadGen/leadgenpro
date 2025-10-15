# e:\DATA\Working On Database\leadgenpro\accounts\templatetags\auth_extras.py
from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Checks if a user is in a specific group.
    Usage: {% if user|has_group:"Managers" %}
    """
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return False
    return group in user.groups.all()
