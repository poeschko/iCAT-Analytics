"""
ICDexplorer

(c) 2011 Jan Poeschko
jan@poeschko.com
"""

from __future__ import division

from datetime import datetime, date, timedelta
from math import floor
from hashlib import md5
import colorsys
    
def debug_iter(items):
    for index, item in enumerate(items):
        if index % 1000 == 0:
            print "%d: %s" % (index, item)
        yield item

def get_week(datetime):
    year, week, weekday = datetime.isocalendar()
    return (year, week)

# trasnlated from JavaScript
# from http://www.staff.science.uu.nl/~gent0113/calendar/isocalendar.htm
def week_to_date(isoyear, isoweeknr, isoweekday=1):
    q = floor(isoyear / 400)
    z = isoyear - 400 * q
    weeksum = 20871*q+52*z+floor((5*z+7-4*floor((z-1)/100))/28)+isoweeknr
    day = 7*weeksum+isoweekday-5
    return date(1, 1, 1) + timedelta(days=day) - timedelta(days=365)
    
def get_weekly(data, get_datetime, to_ordinal=True, min_date=None, max_date=None):
    result = {}
    #min_date = max_date = None
    for item in data:
        #year, week, weekday = get_datetime(item).date().iso_week()
        date = get_datetime(item)
        if date is None:
            continue
        if min_date is None or date < min_date:
            min_date = date
        if max_date is None or date > max_date:
            max_date = date
        week = get_week(date)
        result[week] = result.get(week, 0) + 1
    """if min_date is None:
        min_week = min(result)
    else:
        min_week = get_week(min_date)
    if max_date is None:
        max_week = max(result)
    else:
        max_week = get_week(max_date)"""
    if min_date is not None and max_date is not None and min_date <= max_date:
        date = min_date
        while date <= max_date:
            week = get_week(date)
            if week not in result:
                result[week] = 0
            date += timedelta(days=7)
    result = sorted(result.iteritems())
    if to_ordinal:
        result = [(day_to_ordinal(week_to_date(year, week)), count) for (year, week), count in result]
    return result

def day_to_ordinal(day):
    delta = day - date(1970, 1, 1)
    #day = day.total_seconds() * 1000
    return delta.days * 24 * 3600 * 1000

def counts(items):
    result = {}
    for item in items:
        result[item] = result.get(item, 0) + 1
    return result

def days(td):
    seconds = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
    return seconds * 1.0 / (24 * 60 * 60)

def median(items):
    items = list(items)
    if items:
        items.sort()
        return items[len(items) // 2]
    else:
        return None
    
def min_null(items):
    try:
        return min(items)
    except ValueError:
        return None
    
def get_color(value):
    value = 1.0 * int(md5(value or '').hexdigest()[:8], base=16) / (1 << 32)
    rgb = colorsys.hls_to_rgb(value, 0.5, 1)
    rgb = [hex(int(c * 255))[2:] for c in rgb]
    rgb = [('0' + c if len(c) < 2 else c) for c in rgb]
    return '#%s%s%s' % tuple(rgb)
    
def pop(items, default=None):
    if items:
        return items.pop(0)
    return default

def pop_values(items, count, default=None):
    for index in range(count):
        yield pop(items, default=default)
    
def calculate_gini(distribution):
    n = len(distribution)
    if n <= 1:
        return 0
    y = sorted(distribution.values())
    y_sum = sum(y)
    if y_sum == 0:
        return 0
    gini = 1 - 2 / (n - 1) * (n - sum((i + 1) * yi for i, yi in enumerate(y)) / y_sum)
    #print (y, gini)
    return gini
    
def group(items, key_func):
    last_key = None
    current = []
    for item in items:
        key = key_func(item)
        if last_key is not None and key != last_key:
            yield (last_key, current)
            current = []
        last_key = key
        current.append(item)
    if current:
        yield (last_key, current)
        
def levenshtein(a,b):
    "Calculates the Levenshtein distance between a and b."
    
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n
        
    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)
            
    return current[n]
        
def levenshtein_noadd(a,b):
    "Calculates the Levenshtein distance between a and b."
    
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n
        
    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n+1):
            add, delete = previous[j]+0, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)
            
    return current[n]

def longest_common_subsequence(a, b):
    m, n = len(a), len(b)
    c = [[0 for j in range(n+1)] for i in range(m+1)]
    for i in range(1,m+1):
        for j in range(1,n+1):
            if a[i-1] == b[j-1]:
                c[i][j] = c[i-1][j-1] + 1
            else:
                c[i][j] = max(c[i][j-1], c[i-1][j])
    return c[m][n]

def add_to_dict(dict, key, value=1):
    try:
        dict[key] += value
    except KeyError:
        dict[key] = value
    