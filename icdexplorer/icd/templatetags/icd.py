# -*- coding: UTF-8 -*-

from __future__ import division

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils import simplejson

import re
from lxml.html import clean

register = template.Library()

@register.filter
def js(object):
    return mark_safe(simplejson.dumps(object, ensure_ascii=False))

@register.filter
def get_attr(object, attr):
    return getattr(object, attr)

@register.filter
def clean_html(content):
    html = clean.clean_html(content)
    if html.startswith('<p>') and html.endswith('</p>'):
        html = html[3:-4]
    if '<tr' in html:
        html = u'<table>%s</table>' % html
    if html != content:
        #print u'"%s" - "%s"' % (html, content)
        html = u'<div class="html-display">%s</div><div class="html-code">%s</html>' % (html, escape(content))
    return mark_safe(html)

@register.filter
def percent(value):
    return value * 100

#DISPLAY_CONTEXT_RE = re.compile(r'^(?s)(.*?)(?: -- Apply to: .*$)?')

@register.filter
def display_context(value):
    #value = DISPLAY_CONTEXT_RE.sub(lambda m: m.group(1), value)
    #return value
    value = value.rsplit(' -- Apply to: ', 1)
    return value[0]

@register.filter
def append(value, other):
    #print value
    #print other
    return unicode(value + other)

@register.filter
def prepend(value, other):
    #print value
    #print other
    return unicode(other + value)

@register.inclusion_tag('tags/valuestable.html')
def valuestable(items, attrs, caption="", max_bar_width=200, line_after=None):
    attrs = attrs.split('.')
    
    def get_value(item):
        #print item
        for attr in attrs:
            if isinstance(item, dict):
                item = item[attr]
            else:
                item = getattr(item, attr)
        return item
        
    values = [get_value(item) for item in items]
    max_value = max(values)
    if any(isinstance(value, float) for value in values):
        #max_value = values[0]
        decimal_places = 2
        if max_value > 0:
            while float(('%.' + str(decimal_places) + 'f') % max_value) == 0:
                decimal_places += 1
            decimal_places += 2
        values_format = [('%.' + str(decimal_places) + 'f') % value for value in values]
    else:
        values_format = values
    bar_widths = [(max_bar_width * value / max_value if max_value > 0 else 0) for value in values]
    line_above = [index == line_after for index, item in enumerate(items)]
    return {
        'items': zip(items, values_format, bar_widths, line_above),
        #'attr': attr,
        'caption': caption,
    }
