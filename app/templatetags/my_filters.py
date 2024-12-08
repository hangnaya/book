from django import template
import re
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()

@register.filter
def intcomma_dot(value):
    return intcomma(value).replace(',', '.')
    
@register.filter
def times(value):
    return range(1,value+1)

@register.filter
def extract_order_id(value):
    match = re.search(r"#(\d+)", value)
    return match.group(1) if match else ""