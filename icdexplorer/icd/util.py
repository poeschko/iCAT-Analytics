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

import Levenshtein

from stringutils import lcs_length
    
def debug_iter(items, n=1000):
    for index, item in enumerate(items):
        if index % n == 0:
            #print "%d: %s" % (index, item)
            print "%s: %5d: %s" % (datetime.now(), index, item)
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
    
    return Levenshtein.distance(a, b)
    
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

# Hirschberg algorithm from http://wordaligned.org/articles/longest-common-subsequence

import itertools

def lcs_lens(xs, ys):
    curr = list(itertools.repeat(0, 1 + len(ys)))
    for x in xs:
        prev = list(curr)
        for i, y in enumerate(ys):
            if x == y:
                curr[i + 1] = prev[i] + 1
            else:
                curr[i + 1] = max(curr[i], prev[i + 1])
    return curr

def lcs(xs, ys):
    nx, ny = len(xs), len(ys)
    if nx == 0:
        return []
    elif nx == 1:
        return [xs[0]] if xs[0] in ys else []
    else:
        i = nx // 2
        xb, xe = xs[:i], xs[i:]
        ll_b = lcs_lens(xb, ys)
        ll_e = lcs_lens(xe[::-1], ys[::-1])
        _, k = max((ll_b[j] + ll_e[ny - j], j)
                    for j in range(ny + 1))
        yb, ye = ys[:k], ys[k:]
        return lcs(xb, yb) + lcs(xe, ye)

def longest_common_subsequence(a, b):
    return lcs_length(a.encode('utf-8'), b.encode('utf-8'))
    
    #return len(lcs(a, b))
    
    #blocks = Levenshtein.matching_blocks(Levenshtein.editops(a, b), a, b)
    #return sum(length for index1, index2, length in blocks)
    
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
    
def queryset_generator(queryset, chunksize=1000, get_pk=lambda row: row.pk, reverse=False):
    """ 
    Iterate over a Django Queryset ordered by the primary key

    This method loads a maximum of chunksize (default: 1000) rows in its
    memory at the same time while django normally would load all rows in its
    memory. Using the iterator() method only causes it to not preload all the
    classes.

    Note that the implementation of the generator does not support ordered query sets.

    """
    ordering = '-' if reverse else ''
    queryset = queryset.order_by(ordering + 'pk')
    last_pk = None
    new_items = True
    while new_items:
        new_items = False
        chunk = queryset
        if last_pk is not None:
            filter_func = 'lt' if reverse else 'gt'
            chunk = chunk.filter({'pk__' + filter_func: last_pk})
        chunk = chunk[:chunksize]
        row = None
        for row in chunk:
            yield row
        if row is not None:
            last_pk = get_pk(row)
            new_items = True
