from django import template
import calendar

register = template.Library()

@register.filter
def get_month_name(month_num):
    try:
        return calendar.month_name[month_num]
    except IndexError:
        return ''
