"""
ICDexplorer

(c) 2011 Jan Poeschko
jan@poeschko.com
"""

from __future__ import division

from django.core.management import setup_environ
import settings

setup_environ(settings)

from django.db import connection
from django.db.models import Avg, Count, Min, Max

from icd.models import Category, Timespan, Change, Author, Group, SelectedChange
from storage.models import PickledData
from precalc import write_csv
from icd.util import *

import sys
import random
from datetime import timedelta
import re
import math
from collections import defaultdict
import networkx as nx

import networkx as nx

from statlib import stats

def username(name):
    uppercase = [c for c in name if 'A' <= c <= 'Z']
    if not uppercase:
        return name[:2]
    return ''.join(uppercase)

def learn_changes_pyml():
    from PyML import VectorDataSet
    from PyML.classifiers.svm import SVR
    from PyML.classifiers.ridgeRegression import RidgeRegression

    print "Get data"
    X = []
    L = []
    patternID = []
    featureID = []
    categories = Category.objects.order_by('name').select_related('metrics')
    #categories = list(categories)
    categories = random.sample(categories, 100)
    for index, category in enumerate(categories):
        if index % 1000 == 0:
            print (index, category)
        metrics = category.metrics.get_metrics()
        X.append([(float(value) if value is not None else 0) for key, value, description in metrics if key not in ['changes', 'annotations']])
        L.append(float(category.metrics.changes))
        patternID.append(category.get_key())
        #if not L:
        #    featureID = [str(key) for key, value in metrics]
        #if index > 2000:
        #    break
    print " Create data set"
    data = VectorDataSet(X, L=L, patternID=patternID, numericLabels=True)
    
    print "Cross-fold validation"
    s = SVR()
    #s = RidgeRegression()
    result = s.cv(data, 3)
    #s.save('svm.data')
    print "Save"
    PickledData.objects.set(settings.INSTANCE, 'svm', s)
    
    print "Result:"
    #print "Success rate: %s" % result.getSuccessRate()
    print result.getInfo()
    print result.getLog()
    print result.getDecisionFunction()
    print "RMSE: %s" % result.getRMSE()
    
    print "Done"

def learn_orange():
    import orange, orngTree

    data = orange.ExampleTable("../orange/categories.tab")
    rt = orngTree.TreeLearner(data, measure="retis", mForPruning=2, minExamples=20)
    orngTree.printTxt(rt, leafStr="%V %I")
    
def export_tab_categories():
    result = []
    categories = Category.objects.order_by('name').select_related('metrics')
    print 'Export to Orange tab format'
    for index, category in enumerate(categories):
        if index % 1000 == 0:
            print '%d: %s' % (index, category.name)
        metrics = category.metrics.get_metrics()
        if not result:
            result.append(['name'] + [key for key, value, description in metrics] + ['display_status'])
            #result.append(['string' if key in [''] for key, value, description in metrics])
            result.append(['string'] + ['c'] * len(metrics) + ['string'])
            #result.append([''] + ['class' if key == 'changes' else '' for key, value, description in metrics])
            result.append([''] + ['' for key, value, description in metrics] + ['class'])
        #for key, value in metrics:
        result.append([category.get_key()] + [value for key, value, description in metrics] + [category.get_display_status()])
    write_csv('../output/categories.tab', result, na='')
    print "Done"
    
def export_timespans(format='tab'):
    print "Export timespans"
    for timespan in Timespan.objects.filter(instance__isnull=False).order_by('start', 'stop'):
        categories = Category.objects.filter(instance=timespan.instance).order_by('name').select_related('metrics')
        categories = list(categories)
        for following in timespan.following.order_by('start', 'stop'):
            name = (timespan.start, timespan.stop, following.start, following.stop)
            name = '%s-%s-%s-%s' % tuple(date.strftime('%y%m%d') for date in name)
            print name
            result = []
            for index, category in enumerate(categories):
                if index % 1000 == 0:
                    print "  %d: %s" % (index, category.name)
                category_metrics = category.metrics.get_metrics() 
                metrics = category.timespan_metrics.get(timespan=timespan).get_metrics()
                metrics += [(key, value, description) for key, value, description in category_metrics if key in set([
                    'parents', 'children', 'depth', 'clustering', 'betweenness_centrality', 'betweenness_centrality_undirected',
                    'pagerank', 'closeness_centrality'])]
                
                """parents = models.IntegerField(db_index=True, help_text="Number of parents")
    children = models.IntegerField(db_index=True, help_text="Number of children")
    depth = models.IntegerField(db_index=True, help_text="Depth in network")
    clustering = models.FloatField(db_index=True, null=True, help_text="Clustering coefficient")
    betweenness_centrality = models.FloatField(db_index=True, null=True, help_text="Betweenness centrality (directed)")
    betweenness_centrality_undirected = models.FloatField(db_index=True, null=True, help_text="Betweenness centrality (undirected)")
    pagerank = models.FloatField(db_index=True, null=True, help_text="Pagerank")
    #authority = models.FloatField(null=True)
    #hub = models.FloatField(null=True)
    closeness_centrality"""
                
                following_category = Category.objects.get(instance=following.instance, name=category.name)
                following_metrics = following_category.timespan_metrics.get(timespan=following).get_metrics_dict()
                if not result:
                    result.append(['name'] + [key for key, value, description in metrics] + ['following_changes'])
                    #result.append(['string' if key in [''] for key, value, description in metrics])
                    if format == 'tab':
                        result.append(['string'] + ['c'] * (len(metrics) + 1))
                        result.append([''] + [''] * len(metrics) + ['class'])
                result.append([category.get_key()] + [value for key, value, description in metrics] + [following_metrics['changes']])
            write_csv('../output/categories-%s.%s' % (name, 'dat' if format == 'r' else format), result, na=('NA' if format == 'r' else ''))
    print "Done"
    
def export_r_categories():
    result = []
    categories = Category.objects.filter(instance=settings.INSTANCE).order_by('name').select_related('metrics')
    print 'Export to R data format'
    for index, category in enumerate(categories):
        if index % 1000 == 0:
            print '%d: %s' % (index, category.name)
        metrics = category.metrics.get_metrics()
        if not result:
            result.append([key for key, value, description in metrics] + ['display_status'])
        #for key, value in metrics:
        ds = category.get_display_status()
        ds = {
            'red': 0,
            'yellow': 1,
            'blue': 2,
        }.get(ds, '')
        result.append([category.get_key()] + [value for key, value, description in metrics] + [ds])
    write_csv('../output/categories.dat', result)
    print "Done"
    
def export_r_timeseries_fast():
    print "Get changes"
    changes = Change.objects.all() #.filter(_instance=settings.INSTANCE) #.filter(Change.relevant_filter)
    changes = changes.defer('old_value', 'new_value') #only('timestamp', 'apply_to')
    changes = queryset_generator(changes)
    print "Initialize"
    changes_by_week = defaultdict(int)
    concepts_by_week = defaultdict(set)
    min_date = max_date = None
    for change in debug_iter(changes):
        year, week, weekday = change.timestamp.isocalendar()
        week = (year, week)
        #print week
        changes_by_week[week] += 1
        concepts_by_week[week].add(change.apply_to_id)
        if min_date is None or change.timestamp < min_date:
            min_date = change.timestamp
        if max_date is None or change.timestamp > max_date:
            max_date = change.timestamp
    print "Output"
    result = [['year', 'week', 'count', 'concepts']]
    current_date = min_date
    index = 0
    while current_date <= max_date:
        year, year_week, weekday = current_date.isocalendar()
        week = (year, year_week)
        changes = changes_by_week[week]
        concepts = concepts_by_week[week]
        result.append([index, year, year_week, changes, len(concepts)])
        current_date += timedelta(days=7)
        index += 1
    write_csv('../output/changes_weekly.dat', result)
    
def export_r_timeseries():
    print "Export time series to R format"
    
    changes = Change.objects.filter(_instance=settings.INSTANCE).filter(Change.relevant_filter).order_by('timestamp')
    changes = list(changes)
    
    all_dates = set()
    all_users = set()
    for change in changes:
        all_users.add(change.author_id)
        all_dates.add(change.timestamp.date())
    all_users = sorted(all_users)
    captions = [user.replace(' ', '_') for user in all_users]
    
    """changes_by_month_user = {}
    for change in changes:
        user = change.author_id
        year, month = change.timestamp.year, change.timestamp.month
        if (year, month) not in changes_by_month_user:
            changes_by_month_user[(year, month)] = {}
        changes_by_month_user[(year, month)][user] = changes_by_month_user[(year, month)].get(user, 0) + 1
    monthly_changes = [['year', 'month'] + captions]
    for index, (month, users) in enumerate(sorted(changes_by_month_user.iteritems())):
        #top5 = sorted([(count, user) for user, count in users.iteritems()], reverse=True)[:5]
        #print "%s: %s" % (month, top5)
        row = [users.get(user, 0) for user in all_users]
        monthly_changes.append([index, month[0], month[1]] + row)
    write_r('../r/changes_monthly.dat', monthly_changes)"""
    
    changes_by_week = {}
    day, max_day = min(all_dates), max(all_dates)
    while day <= max_day:
        year, week, weekday = day.isocalendar()
        if (year, week) not in changes_by_week:
            changes_by_week[(year, week)] = [0, set(), 0, {}] 
                # number, set of concepts, total_levenshtein_distance, by property
        day += timedelta(days=7)
        
    for change in debug_iter(changes):
        #user = change.author_id
        year, week, weekday = change.timestamp.isocalendar()
        #if (year, week) not in changes_by_week_user:
        #    changes_by_week_user[(year, week)] = {}
        data = changes_by_week[(year, week)]
        data[0] += 1 # = changes_by_week[(year, week)].get(user, 0) + 1
        data[1].add(change.apply_to_id)
        if change.property and change.levenshtein_distance is not None:
            data[2] += change.levenshtein_distance
            data[3][change.property] = data[3].get(change.property, 0) + 1
    properties = ['sorting label', 'use', 'icd title', 'short definition', 'synonym', 'display status', 'type', 'inclusions', 'icd numerical code', 'exclusions', 'definition prefilled', 'diagnostic criteria']
    weekly_changes = [['year', 'week', 'count', 'concepts', 'total_levenshtein'] + [property.replace(' ', '_') for property in properties]]
    for index, item in enumerate(sorted(changes_by_week.iteritems())):
        ((year, week), (count, concepts, total_levenshtein, by_property)) = item
        #top5 = sorted([(count, user) for user, count in users.iteritems()], reverse=True)[:5]
        #print "%s: %s" % (week, top5)
        #row = [users.get(user, 0) for user in all_users]
        #weekly_changes.append([index, week[0], week[1]] + row)
        weekly_changes.append([index, year, week, count, len(concepts), total_levenshtein] + \
            [by_property.get(property, 0) for property in properties])
    write_csv('../output/changes_weekly.dat', weekly_changes)
    
    return

    print "Grouped analysis"
        
    changes_by_week_user = {}
    day, max_day = min(all_dates), max(all_dates)
    while day <= max_day:
        year, week, weekday = day.isocalendar()
        if (year, week) not in changes_by_week_user:
            changes_by_week_user[(year, week)] = {}
        day += timedelta(days=7)
        
    for change in changes:
        user = change.author_id
        year, week, weekday = change.timestamp.isocalendar()
        #if (year, week) not in changes_by_week_user:
        #    changes_by_week_user[(year, week)] = {}
        changes_by_week_user[(year, week)][user] = changes_by_week_user[(year, week)].get(user, 0) + 1
    weekly_changes = [['year', 'week'] + captions]
    for index, (week, users) in enumerate(sorted(changes_by_week_user.iteritems())):
        #top5 = sorted([(count, user) for user, count in users.iteritems()], reverse=True)[:5]
        #print "%s: %s" % (week, top5)
        row = [users.get(user, 0) for user in all_users]
        weekly_changes.append([index, week[0], week[1]] + row)
    write_csv('../output/changes_weekly_users.dat', weekly_changes)
    
    groups = [1, 9, 99, 999, None]
    weekly_changes_grouped = [groups]
    weekly_changes_group_sizes = [groups]
    for index, (week, users) in enumerate(sorted(changes_by_week_user.iteritems())):
        groups_users = [0 for group in groups]
        groups_edits = [0 for group in groups]
        for user, count in users.iteritems():
            for group_index, group in enumerate(groups):
                if group is None or count <= group:
                    break
            groups_users[group_index] += 1
            groups_edits[group_index] += count
        weekly_changes_grouped.append([index] + groups_edits)
        weekly_changes_group_sizes.append([index] + groups_users)
    write_csv('../output/changes_weekly_grouped.dat', weekly_changes_grouped)
    write_csv('../output/changes_weekly_group_sizes.dat', weekly_changes_group_sizes)
   
FEATURED_PAGES = """ 
<Acute myeloid leukemia>
<Acute radiation syndrome>
<Alzheimer's disease>
<Asperger syndrome>
<Autism>
<Chagas disease>
<Cholangiocarcinoma>
<Coeliac disease>
<Dengue fever>
<Hepatorenal syndrome>
<Huntington's disease>
<Influenza>
<Keratoconus>
<Lung cancer>
<Major depressive disorder>
<Meningitis>
<Multiple sclerosis>
<Osteochondritis dissecans>
<Oxygen toxicity>
<Parkinson's disease>
<Poliomyelitis>
<Pulmonary contusion>
<Reactive attachment disorder>
<Rhabdomyolysis>
<Rotavirus>
<Schizophrenia>
<Subarachnoid hemorrhage>
<Thyrotoxic periodic paralysis>
"""
FEATURED_PAGES = re.findall(r'\<(.*?)\>', FEATURED_PAGES)
#print FEATURED_PAGES

def queryset_singular(query, n=10):
    count = query.count()
    for index in xrange(count // n + 1):
        slice = query[index*n : (index+1)*n]
        #slice = list(slice)
        #yield query[index]
        for item in slice:
            yield item 
            
def featured():
    relevant_categories = list(Category.objects.filter(name__in=FEATURED_PAGES))
    print ", ".join('"%s"' % c.pk for c in relevant_categories)
    
def export_changes_accumulated():
    print "Export time-accumulated changes to R format"
    
    empty_values = ['', '(empty)']
    
    """categories = Category.objects.filter(metrics__isnull=False).select_related('metrics')
    categories = list(categories)
    for category in categories:
        category.change_count = category.metrics.changes
    categories.sort(key=lambda c: c.change_count, reverse=True)
    #print categories[:10]
    relevant_categories = categories[:10]"""
    relevant_categories = list(Category.objects.filter(name__in=FEATURED_PAGES))
    #print "Relevant categories: %s" % [c.name for c in relevant_categories]
    print "Relevant categories: %s" % ", ".join('"%s"' % c.pk for c in relevant_categories)
    
    vocabulary_analysis = True #not settings.IS_WIKI
    
    #changes = Change.objects.filter(_instance=settings.INSTANCE).filter(Change.relevant_filter)
    changes = Change.objects
    changes = changes.order_by('timestamp')
    changes = changes.filter(apply_to__in=relevant_categories)
    if not vocabulary_analysis:
        changes = changes.defer('old_value', 'new_value')
    print "Relevant changes total: %d" % changes.count()
    if not settings.IS_WIKI:
        changes = changes.filter(levenshtein_distance__isnull=False)
    if not settings.IS_WIKI:
        changes = changes.exclude(property="")
    #print "Property and Levenshtein distance set: %d" % changes.count()
    
    #changes = Change.objects.all()[:10000]
    #changes_count = changes.count()
    
    if settings.IS_WIKI:
        #modify_changes = changes.exclude(old_value__in=empty_values).exclude(new_value__in=empty_values)
        text_changes = changes #= list(changes)
    else:
        non_textual_properties = ['sorting label', 'use', 'display status', 'type', 'inclusions', 'exclusions',
            'primary tag']
        text_changes = changes.exclude(property__in=non_textual_properties)
        modify_changes = text_changes.exclude(old_value__in=empty_values).exclude(new_value__in=empty_values)    
    
    #changes = Change.objects.all()[:5000]
    #modify_changes = text_changes = changes = list(changes)
    
    first_timestamp = changes[0].timestamp
    
    if settings.IS_WIKI:
        #text_changes = text_changes.iterator()
        #text_changes = queryset_singular(text_changes)
        text_changes = queryset_generator(SelectedChange.objects.all())
    else:
        text_changes = list(text_changes)
        print "Textual properties filtered: %d" % len(text_changes)
        changes = list(changes)
    
    def get_words(text):
        return (word.lower() for word in word_re.findall(text))
    
    def get_week(timestamp):
        delta = timestamp - first_timestamp
        return 1.0 * (delta.days + delta.seconds / (24 * 3600.0)) / 7
    
    output = [['count', 'week', 'concepts', 'levenshtein', 'levenshtein_rel',
        'total_levenshtein', 'total_levenshtein_rel', 'total_levenshtein_sim',
        'total_lcs_rel',
        'authors_gini',
        'vocabulary', 'word_count']]
    total_levenshtein = total_levenshtein_rel = total_levenshtein_sim = 0
    total_lcs_rel = 0
    authors = {}
    vocabulary = {}
    concepts = set()
    word_re = re.compile('([a-zA-Z]{2,})')    
    for index, change in enumerate(text_changes):
        if index % 1000 == 0:
            print index
            print sorted(((count, word) for word, count in vocabulary.iteritems()), reverse=True)[:50]
        concepts.add(change.apply_to_id)
        #add_to_dict(authors, change.author_id)
        total_levenshtein += change.levenshtein_distance
        total_levenshtein_rel += change.levenshtein_distance_rel
        if change.levenshtein_similarity is not None:
            total_levenshtein_sim += change.levenshtein_similarity
        if change.lcs_rel is not None:
            total_lcs_rel += change.lcs_rel # if change.old_value else 1
        if vocabulary_analysis:
            for word in get_words(change.old_value):
                if word in vocabulary:
                    vocabulary[word] -= 1
                    if not vocabulary[word]:
                        del vocabulary[word]
            for word in get_words(change.new_value):
                add_to_dict(vocabulary, word)
        output.append([index, index+1, get_week(change.timestamp), len(concepts),
            change.levenshtein_distance, change.levenshtein_distance_rel,
            total_levenshtein, total_levenshtein_rel, total_levenshtein_sim,
            total_lcs_rel,
            0, #calculate_gini(authors),
            len(vocabulary), sum(vocabulary.itervalues())])
    write_csv('../output/changes_accumulated_text.dat', output)
    
    if settings.IS_WIKI:
        return
    
    vocabulary_analysis = False # only needed for text_changes
    
    print "Get modifying changes"
    modify_changes = list(modify_changes)
    print "Modifying changes: %d" % len(modify_changes)
    
    output = [['count', 'week', 'concepts', 'levenshtein', 'levenshtein_rel',
        'total_levenshtein', 'total_levenshtein_rel', 'total_levenshtein_sim',
        'total_lcs_rel',
        'authors_gini',
        'vocabulary', 'word_count']]
    total_levenshtein = total_levenshtein_rel = total_levenshtein_sim = 0
    total_lcs_rel = 0
    authors = {}
    vocabulary = {}
    concepts = set()
    word_re = re.compile('([a-zA-Z]{2,})')    
    for index, change in enumerate(modify_changes):
        if index % 1000 == 0:
            print index
            print sorted(((count, word) for word, count in vocabulary.iteritems()), reverse=True)[:50]
        concepts.add(change.apply_to_id)
        add_to_dict(authors, change.author_id)
        total_levenshtein += change.levenshtein_distance
        total_levenshtein_rel += change.levenshtein_distance_rel
        total_levenshtein_sim += change.levenshtein_similarity
        if change.lcs_rel is not None:
            total_lcs_rel += change.lcs_rel
        if vocabulary_analysis:
            for word in get_words(change.old_value):
                if word in vocabulary:
                    vocabulary[word] -= 1
                    if not vocabulary[word]:
                        del vocabulary[word]
            for word in get_words(change.new_value):
                add_to_dict(vocabulary, word)
        output.append([index, index+1, get_week(change.timestamp), len(concepts),
            change.levenshtein_distance, change.levenshtein_distance_rel,
            total_levenshtein, total_levenshtein_rel, total_levenshtein_sim,
            total_lcs_rel,
            calculate_gini(authors),
            len(vocabulary), sum(vocabulary.itervalues())])
    write_csv('../output/changes_accumulated_modify.dat', output)
    
    output = [['count', 'week', 'concepts', 'levenshtein', 'levenshtein_rel',
        'total_levenshtein', 'total_levenshtein_rel', 'total_levenshtein_sim',
        'total_lcs_rel',
        'authors_gini']]
    total_levenshtein = total_levenshtein_rel = total_levenshtein_sim = 0
    total_lcs_rel = 0
    authors = {}
    concepts = set()
    for index, change in enumerate(changes):
        if index % 1000 == 0:
            print index
        concepts.add(change.apply_to_id)
        add_to_dict(authors, change.author_id)
        total_levenshtein += change.levenshtein_distance
        """if change.property in non_textual_properties or change.old_value in empty_values or change.new_value in empty_values:
            total_levenshtein_rel += 1
            total_levenshtein_sim += 0
            total_lcs_rel += 0
        else:"""
        total_levenshtein_rel += change.levenshtein_distance_rel
        total_levenshtein_sim += change.levenshtein_similarity
        if change.lcs_rel is not None:
            total_lcs_rel += change.lcs_rel
        output.append([index, index+1, get_week(change.timestamp), len(concepts),
            change.levenshtein_distance, change.levenshtein_distance_rel,
            total_levenshtein, total_levenshtein_rel, total_levenshtein_sim,
            total_lcs_rel,
            calculate_gini(authors)])
    write_csv('../output/changes_accumulated_all.dat', output)
        
def export_changes_grouped():
    changes = Change.objects.filter(_instance=settings.INSTANCE).filter(Change.relevant_filter).order_by('timestamp')
    changes = changes.filter(levenshtein_distance__isnull=False).exclude(property="")
      
    per_group = int(math.ceil(len(changes) / 10.0) + 0.1)
    groups = []
    while changes:
        groups.append(changes[:per_group])
        changes = changes[per_group:]
        
    output = [['count', 'concepts', 'authors_count', 'authors_gini', 'total_levenshtein', 'total_levenshtein_rel']]
    for index, group in enumerate(groups):
        print "Group %s: %d changes" % (index, len(group))
        authors = {}
        relevant_changes = 0
        concepts = set()
        total_levenshtein = 0
        total_levenshtein_rel = 0
        for change in group:
            #if change.levenshtein_distance is not None:
            relevant_changes += 1
            concepts.add(change.apply_to_id)
            #authors.add(change.author_id)
            add_to_dict(authors, change.author_id)
            total_levenshtein += change.levenshtein_distance
            total_levenshtein_rel += change.levenshtein_distance_rel
        output.append([index, relevant_changes, len(concepts),
            len(authors), calculate_gini(authors),
            total_levenshtein, total_levenshtein_rel])
    
    write_csv('../output/changes_grouped.dat', output)
    
    print "Done"
    
def analyse_propagation_sessioned(baseline=False):
    print "analyse_propagation_sessioned()"
    G_orig = PickledData.objects.get(settings.INSTANCE, 'graph')
    if baseline:
        nodes = G_orig.nodes()
        in_degrees = G_orig.in_degree()
        out_degrees = G_orig.out_degree()
        G_random = nx.directed_configuration_model([in_degrees[node] for node in nodes],
            [out_degrees[node] for node in nodes], seed=1)
        G = nx.DiGraph()
        for node in nodes:
            G.add_node(node)
        for u, v in G_random.edges_iter():
            G.add_edge(nodes[u], nodes[v])
        print "Original: %d nodes, %d edges -> random: %d nodes, %d edges" % (len(G_orig), G_orig.size(),
            len(G), G.size())
    else:
        G = G_orig
    
    #changes_base = Change.objects.exclude(action__startswith='Subclass Added').exclude(action__startswith='Superclass Added')
    #changes_base = changes_base.exclude(action__startswith='Change in hierarchy for class')
    
    changes_base = Change.objects.filter(_instance=settings.INSTANCE).filter(Change.relevant_filter)
    changes_base = changes_base.defer('old_value', 'new_value') 
    #changes = changes_base.order_by('timestamp')
    changes = changes_base.select_related('apply_to')
    changes = queryset_generator(changes)
    changes_by_category = defaultdict(list)
    for change in debug_iter(changes):
        if change.apply_to is not None:
            changes_by_category[change.apply_to.category_id[len(settings.INSTANCE):]].append(change)
    
    for key in changes_by_category:
        print key
        changes_by_category[key].sort(key = lambda x: x.timestamp)

    #changes = list(changes)
    #already_investigated = set()
    total_changes = 0
    
    #counters = {}
    
    #relations = [('parent', )]
    
    distributions = defaultdict(list)
    
    for u, v in G.edges_iter():
        changes_child = changes_by_category[u]
        changes_parent = changes_by_category[v]
        changes = [(change.timestamp, 'c', change.author_id) for change in changes_child] + [(change.timestamp, 'p', change.author_id) for change in changes_parent]
        changes.sort()
        for by_author in (False, True):
            times_down = []
            times_up = []
            if by_author:
                authors = [a for t, k, a in changes]
            else:
                authors = [None]
            for author in authors:
                if author is None:
                    changes_author = changes
                else:
                    changes_author = [(t, k, a) for t, k, a in changes if a == author]
                links = zip(changes_author[:-1], changes_author[1:])
                for c1, c2 in links:
                    if c1[1] != c2[1]:
                        is_parent_to_child = c1[1] == 'p'
                        time = c2[0] - c1[0]
                        if is_parent_to_child:
                            times_down.append(time)
                        else:
                            times_up.append(time)
            if times_down:
                distributions[('author' if by_author else 'any', 'down')].append(min(times_down))
                    #sum(times_down, timedelta(0)) // len(times_down))
            if times_up:
                distributions[('author' if by_author else 'any', 'up')].append(min(times_up))
                    #sum(times_up, timedelta(0)) // len(times_up))
                
    #print distributions
    
    
    #preceded_by_parent = preceded_by_child = preceded_by_related = 0
    #author_preceded_by_parent = author_preceded_by_child = author_preceded_by_related = 0
    """for index, change in enumerate(changes):
        #day = change.timestamp.date()
        if change.apply_to is None:
            continue
        category = change.apply_to.category_id[len(settings.INSTANCE):]
        if index % 1000 == 0:
            print "%d: %s" % (index, category)
        #if (day, change.author_id, category) in already_investigated:
        #    continue
        #already_investigated.add((day, change.author_id, category))
        if category not in G:
            continue
        total_changes += 1
        parents = G.successors(category)
        children = G.predecessors(category)
        
        ""for time, others in [('followed', changes[index+1:]), ('preceded', changes[index-1::-1])]:
            for relation, relation_categories in [('parents', parents), ('children', children), ('relation', parents+children)]:
                relation_categories = [settings.INSTANCE + other for other in relation_categories]
                for author, author_filter in [('author', lambda c: c.author_id == change.author_id), ('any', lambda c: True)]:
                    id = (time, relation, author)
                    related_time = None
                    for other in others:
                        if other.apply_to is not None and other.apply_to.category_id in relation_categories and author_filter(other):
                            related_time = other.timestamp
                            break
                    if related_time is not None:
                        related_time = abs(related_time - change.timestamp)
                    distributions[id].append(related_time)""
        
        for time, time_filter, acc in [('followed', 'gte', Min), ('preceded', 'lte', Max)]:
            for relation, relation_categories in [('parents', parents), ('children', children), ('relation', parents+children)]:
                relation_categories = [settings.INSTANCE + other for other in relation_categories]
                for author, author_filter in [('author', {'author': change.author_id}), ('any', {})]:
                    #id = (relation, author, timespan)
                    id = (time, relation, author)
                    related_changes = changes_base.filter(**{'timestamp__' + time_filter: change.timestamp})
                    related_changes = related_changes.filter(apply_to__category__in=relation_categories)
                    if author_filter: related_changes = related_changes.filter(**author_filter)
                    #if timespan_filter: preceding = preceding.filter(**timespan_filter)
                    related_time = related_changes.aggregate(time=acc('timestamp'))['time']
                    if related_time is not None:
                        related_time = abs(related_time - change.timestamp)
                    distributions[id].append(related_time)
        
        ""parent = Change.objects.filter(apply_to__category__in=parents, timestamp__lte=change.timestamp).count()
        child = Change.objects.filter(apply_to__category__in=children, timestamp__lte=change.timestamp).count()
        author_parent = Change.objects.filter(author=change.author_id, apply_to__category__in=parents, timestamp__lte=change.timestamp).count()
        author_child = Change.objects.filter(author=change.author_id, apply_to__category__in=children, timestamp__lte=change.timestamp).count()
        
        if parent: preceded_by_parent += 1
        if child: preceded_by_child += 1
        if parent or child: preceded_by_related += 1""
    """
    print distributions
    print "Save"
    suffix = '_baseline' if baseline else ''
    PickledData.objects.set(settings.INSTANCE, 'propagation_sessioned_distribution%s' % suffix, distributions)
    #print counterss
    #print total_changes
    
    print "Done"
    
def analyse_propagation(baseline=False):
    G_orig = PickledData.objects.get(settings.INSTANCE, 'graph')
    if baseline:
        nodes = G_orig.nodes()
        in_degrees = G_orig.in_degree()
        out_degrees = G_orig.out_degree()
        G_random = nx.directed_configuration_model([in_degrees[node] for node in nodes],
            [out_degrees[node] for node in nodes], seed=1)
        G = nx.DiGraph()
        for node in nodes:
            G.add_node(node)
        for u, v in G_random.edges_iter():
            G.add_edge(nodes[u], nodes[v])
        print "Original: %d nodes, %d edges -> random: %d nodes, %d edges" % (len(G_orig), G_orig.size(),
            len(G), G.size())
    else:
        G = G_orig
    
    #changes_base = Change.objects.exclude(action__startswith='Subclass Added').exclude(action__startswith='Superclass Added')
    #changes_base = changes_base.exclude(action__startswith='Change in hierarchy for class')
    changes_base = Change.objects.filter(_instance=settings.INSTANCE).filter(Change.relevant_filter)
    changes = changes_base.order_by('timestamp').select_related('apply_to')
    #changes = list(changes)
    #already_investigated = set()
    total_changes = 0
    
    #counters = {}
    
    #relations = [('parent', )]
    
    distributions = defaultdict(list)
    
    #preceded_by_parent = preceded_by_child = preceded_by_related = 0
    #author_preceded_by_parent = author_preceded_by_child = author_preceded_by_related = 0
    for index, change in enumerate(changes):
        #day = change.timestamp.date()
        if change.apply_to is None:
            continue
        category = change.apply_to.category_id[len(settings.INSTANCE):]
        if index % 1000 == 0:
            print "%d: %s" % (index, category)
        #if (day, change.author_id, category) in already_investigated:
        #    continue
        #already_investigated.add((day, change.author_id, category))
        if category not in G:
            continue
        total_changes += 1
        parents = G.successors(category)
        children = G.predecessors(category)
        
        """for time, others in [('followed', changes[index+1:]), ('preceded', changes[index-1::-1])]:
            for relation, relation_categories in [('parents', parents), ('children', children), ('relation', parents+children)]:
                relation_categories = [settings.INSTANCE + other for other in relation_categories]
                for author, author_filter in [('author', lambda c: c.author_id == change.author_id), ('any', lambda c: True)]:
                    id = (time, relation, author)
                    related_time = None
                    for other in others:
                        if other.apply_to is not None and other.apply_to.category_id in relation_categories and author_filter(other):
                            related_time = other.timestamp
                            break
                    if related_time is not None:
                        related_time = abs(related_time - change.timestamp)
                    distributions[id].append(related_time)"""
        
        for time, time_filter, acc in [('followed', 'gte', Min), ('preceded', 'lte', Max)]:
            for relation, relation_categories in [('parents', parents), ('children', children), ('relation', parents+children)]:
                relation_categories = [settings.INSTANCE + other for other in relation_categories]
                for author, author_filter in [('author', {'author': change.author_id}), ('any', {})]:
                    #id = (relation, author, timespan)
                    id = (time, relation, author)
                    related_changes = changes_base.filter(**{'timestamp__' + time_filter: change.timestamp})
                    related_changes = related_changes.filter(apply_to__category__in=relation_categories)
                    if author_filter: related_changes = related_changes.filter(**author_filter)
                    #if timespan_filter: preceding = preceding.filter(**timespan_filter)
                    related_time = related_changes.aggregate(time=acc('timestamp'))['time']
                    if related_time is not None:
                        related_time = abs(related_time - change.timestamp)
                    distributions[id].append(related_time)
        
        """parent = Change.objects.filter(apply_to__category__in=parents, timestamp__lte=change.timestamp).count()
        child = Change.objects.filter(apply_to__category__in=children, timestamp__lte=change.timestamp).count()
        author_parent = Change.objects.filter(author=change.author_id, apply_to__category__in=parents, timestamp__lte=change.timestamp).count()
        author_child = Change.objects.filter(author=change.author_id, apply_to__category__in=children, timestamp__lte=change.timestamp).count()
        
        if parent: preceded_by_parent += 1
        if child: preceded_by_child += 1
        if parent or child: preceded_by_related += 1"""
        
    print "Save"
    suffix = '_baseline' if baseline else ''
    PickledData.objects.set(settings.INSTANCE, 'propagation_distribution%s' % suffix, distributions)
    #print counterss
    #print total_changes
    
    print "Done"
    
def analyse_propagation_sessioned_export(baseline=False):
    print "analyse_propagation_sessioned_export()"
    G_orig = PickledData.objects.get(settings.INSTANCE, 'graph')
    links = G_orig.size()
    
    suffix = '_baseline' if baseline else ''
    distributions = PickledData.objects.get(settings.INSTANCE, 'propagation_sessioned_distribution%s' % suffix)
    per_hour = {}
    for id, changes in distributions.iteritems():
        changes = [time.days * 24 + time.seconds // 3600 + 1 for time in changes if time is not None]   # round down to hours
        #changes.sort(key=lambda t: t if t is not None else timedelta.max)
        changes.sort()
        per_hour[id] = defaultdict(int)
        for hour in changes:
            per_hour[id][hour] += 1
        per_week = []
        print "%s: %d" % (id, len(changes))
        #for change in changes:
    #for id in per_hour:
    #    per
    max_hours = max(max(hours.keys()) for hours in per_hour.values())
    print "Max hours: %d" % max_hours
    ids = sorted(per_hour.keys())
    data = [['_'.join(id) for id in ids]]
    accumulated = defaultdict(int)
    for hour in range(1, max_hours + 1):
        for id in ids:
            accumulated[id] += per_hour[id][hour] 
        data.append([hour] + [accumulated[id] / links for id in ids]) #[per_hour[id][hour] for id in ids])
        
    write_csv('../output/propagation_sessioned%s.dat' % suffix, data)
    
def analyse_propagation_export(baseline=False):
    suffix = '_baseline' if baseline else ''
    distributions = PickledData.objects.get(settings.INSTANCE, 'propagation_distribution%s' % suffix)
    per_hour = {}
    for id, changes in distributions.iteritems():
        changes = [time.days * 24 + time.seconds // 3600 + 1 for time in changes if time is not None]   # round down to hours
        #changes.sort(key=lambda t: t if t is not None else timedelta.max)
        changes.sort()
        per_hour[id] = defaultdict(int)
        for hour in changes:
            per_hour[id][hour] += 1
        per_week = []
        print "%s: %d" % (id, len(changes))
        #for change in changes:
    #for id in per_hour:
    #    per
    max_hours = max(max(hours.keys()) for hours in per_hour.values())
    print "Max hours: %d" % max_hours
    ids = sorted(per_hour.keys())
    data = [['_'.join(id) for id in ids]]
    accumulated = defaultdict(int)
    for hour in range(1, max_hours + 1):
        for id in ids:
            accumulated[id] += per_hour[id][hour] 
        data.append([hour] + [accumulated[id] for id in ids]) #[per_hour[id][hour] for id in ids])
        
    write_csv('../output/propagation%s.dat' % suffix, data)
    
def analyse_tags_reverts():
    random.seed(1)
    authors = dict((author.instance_name, author) for author in Author.objects.filter(instance=settings.INSTANCE))
    for graph in ('author_graph_directed', 'author_graph'):
        print graph
        G = PickledData.objects.get(settings.INSTANCE, graph)
        inter_tag_counts = []
        tags = [authors[node].affiliation for node in G]
        for k in range(100):
            #print k
            tags_by_author = dict(zip(G, tags))
            count = 0
            for u, v, data in G.edges_iter(data=True):
                if tags_by_author[u] != tags_by_author[v]:
                    count += data['count']
            inter_tag_counts.append(count)
            random.shuffle(tags)
        #print inter_tag_counts
        print inter_tag_counts[0]
        print "Means: %f" % stats.mean(inter_tag_counts[1:])
        print "Standard deviation: %f" % stats.stdev(inter_tag_counts[1:])
    
def export_follow_ups():
    G = nx.DiGraph()
    for property in Change.objects.values_list('property', flat=True).distinct():
        print property
        count = Change.objects.filter(property=property).count()
        G.add_node(property, count=count)
    follow_ups = PickledData.objects.get(settings.INSTANCE, 'follow_ups')
    for timespan, follows in follow_ups.iteritems():
        print timespan
        Gt = G.copy()
        for (u, v), count in follows.iteritems():
            Gt.add_edge(u, v, count=count)
        Gt.remove_node('')
        nx.write_graphml(Gt, '../output/followups_%s.graphml' % timespan, prettyprint=True)
    print "Done"
    
def pattern_analysis_features():
    " Analysis analog to K-CAP paper by S. Falconer et al. "
    
    if not settings.IS_NCI:
        change_kinds = {
            'Property': 'pro',
            'Set': 'pro',
            'Replaced': 'pro',
            'ReplacedProperty': 'pro',
            'Hierarchy': 'mov',
            'Added': 'pro',
            'AddedAs': 'pro',
            'AddedValue': 'pro',
            'AddDirectType': '',
            'RemoveDirectType': '',
            'Removed': 'pro',
            'RemovedSuperclass': '',
            'RemoveDeprecationFlag': '',
            'Deleted': 'pro',
            'DeleteCondition': 'pro',
            'SetCondition': 'pro',
            'Moved': 'mov',
            'CreatedReference': 'add',
            'ImportedReference': '',
            'ImportedReferenceProperty': '',
            'ReplacedReference': '',
            'CreateReference': '',
            'ModifiedClassDescription': 'pro',
            'Export': '',
            'RetireClass': '',
            'RetireClassMoveChildren': '',
            'CreateClass': 'add',
            'DeleteClass': 'del',
            'Automatic': '',
            'AnnotationChange': '',
        }
    else:
        change_kinds = {
            'Annotation Added': '',
            'Annotation Modified': '',
            'Annotation Removed': '',
            'Class_Created': 'add',
            'Class_Deleted': 'del',
            'Composite_Change': '',
            'DisjointClass_Added': 'add',
            'DomainProperty_Added': '',
            'DomainProperty_Removed': '',
            'Individual_Added': 'add',
            'Individual_Created': 'add',
            'Individual_Deleted': 'del',
            'Individual_Removed': 'del',
            'Name_Changed': 'pro',
            'Property Value Changed': 'pro',
            'Property_Created': 'pro',
            'Property_Deleted': 'pro',
            'Subclass_Added': 'mov',
            'Subclass_Removed': 'mov',
            'Superclass_Added': 'mov',
            'Superclass_Removed': 'mov',
        }
    
    all_changes = Change.objects.filter(_instance=settings.INSTANCE).filter(Change.relevant_filter)
    avg_depth = all_changes.aggregate(d=Avg('apply_to__category__metrics__depth'))['d']
    print "Average depth: %f" % avg_depth
    
    G = PickledData.objects.get(settings.INSTANCE, 'author_graph')
    centrality = nx.closeness_centrality(G)
    
    features = {}
    authors = Author.objects.filter(instance=settings.INSTANCE).order_by('name')
    for author in authors:
        cursor = connection.cursor()
        if settings.IS_NCI:
            kind_field = 'action'
        else:
            kind_field = 'kind'
        cursor.execute("""
            select %(field)s, count(*) from icd_change
            where _instance=%%s
            and action%(is_cc)s"Composite_Change" and context not like "Automatic%%%%"
            and author_id=%%s
            group by %(field)s;
        """ % {'field': kind_field, 'is_cc': '!=' if settings.IS_NCI else '='}, [settings.INSTANCE, author.pk])
        c = defaultdict(int)
        rows = cursor.fetchall()
        total = 0
        for kind, count in rows:
            feature = change_kinds.get(kind)
            if feature:
                c[feature] += count
            total += count
        if total > 0:
            changes = author.changes.filter(Change.relevant_filter)
            #hierarchies = defaultdict(int)
            #for change in changes:
            hierarchies = changes.values('apply_to__category__hierarchy_id').annotate(count=Count('pk'))
            print hierarchies
            max_hierarchy = max([0] + [hierarchy['count'] for hierarchy in hierarchies
                if hierarchy['apply_to__category__hierarchy_id'] is not None])
            author_features = {
                'changes_count': total,
                'multi_author': changes.filter(apply_to__category__metrics__authors_changes__gt=1).count() / total,
                'leaf': changes.filter(apply_to__category__metrics__children=0).count() / total,
                'depth': changes.aggregate(d=Avg('apply_to__category__metrics__depth'))['d'] / avg_depth,
                'one_hierarchy': max_hierarchy / total,
                'centrality': centrality.get(author.pk),
            }
            #for feature, value in c.iteritems():
            for feature in ['del', 'add', 'mov', 'pro']:
                author_features['c_' + feature] = c[feature] / total
            print "%s: %s" % (author.name, author_features)
            features[author.name] = author_features
        #c_del = author.changes.filter(Change.relevant_filter).filter(kind__startswith="Delete")
        #c_add = fds
        
    print "Save"
    PickledData.objects.set(settings.INSTANCE, 'pattern_analysis_features', features)
    
    data = []
    for author, author_features in sorted(features.iteritems()):
        if not data:
            data.append(['author'] + sorted(author_features.keys()))
        data.append([author] + [value for key, value in sorted(author_features.iteritems())])
        
    write_csv('../output/pattern_analysis_features.csv', data)
    
def analyse_authors(G=None, suffix=""):
    if G is None:
        G = PickledData.objects.get(settings.INSTANCE, 'author_graph_directed')
        for u, v, data in G.edges_iter(data=True):
            data['weight'] = data['count']
    
    hubs, authorities = nx.hits(G, max_iter=1000)
    
    data = []
    authors = Author.objects.filter(instance=settings.INSTANCE).order_by('-changes_count')
    for author in authors:
        data.append([author.name, author.changes_count,
            author.overrides_count, author.overridden_count,
            hubs.get(author.pk, ""), authorities.get(author.pk, "")
        ])
        
    print data
        
    write_csv('../output/authors_hubs_authorities%s.csv' % suffix, data)
    
def analyse_authors_relative():
    G_orig = PickledData.objects.get(settings.INSTANCE, 'author_graph_directed')
    """nodes = G_orig.nodes()
    in_degrees = [sum(data['count'] for u, v, data in G_orig.in_edges([node],data=True)) for node in nodes] #G_orig.in_degree()
    out_degrees = [sum(data['count'] for u, v, data in G_orig.out_edges([node],data=True)) for node in nodes]
    print in_degrees
    expected_numbers = defaultdict(int)
    K = 10000
    for k in range(K):
        if k % 100 == 0:
            print k
        G_random = nx.directed_configuration_model(in_degrees, out_degrees)
        #G = nx.DiGraph()
        #for node in nodes:
        #    G.add_node(node)
        for u, v in G_random.edges_iter():
            #G.add_edge(nodes[u], nodes[v])
            expected_numbers[(nodes[u], nodes[v])] += 1
    for edge in expected_numbers:
        expected_numbers[edge] = expected_numbers[edge] / K
    #print sorted(expected_numbers.iteritems())
    for u in nodes:
        others = sorted(((v, c) for (u_, v), c in expected_numbers.iteritems() if u_ == u),
                key=lambda (v, c): c, reverse=True)[:5]
        print "%s: %s" % (u[len(settings.INSTANCE):],
            [(v[len(settings.INSTANCE):], c) for v, c in others])"""
    authors = Author.objects.filter(instance=settings.INSTANCE)
    authors = dict((author.pk, author) for author in authors)
    #in_degrees = G_orig.in_degree()
    for u, v, data in G_orig.edges_iter(data=True):
        #data['weight'] = data['count'] - expected_numbers[(u, v)]
        data['weight'] = data['count'] / authors[v].sessions_count
        
    analyse_authors(G_orig, '_relative')
    
def tag_borders():
    " Analyse how often users cross TAG borders "
    
    print "TAG borders"
    
    class TAG:
        def __init__(self):
            self.changes = []
            self.changed_categories = set()
            self.users = []
            self.authors = defaultdict(int)
            self.changes_by_others = 0
            self.categories_count = 0
            
        def get_data(self):
            return [
                self.categories_count, len(self.changed_categories),
                len(self.changed_categories) / self.categories_count if self.categories_count > 0 else '',
                len(self.changes), self.changes_by_others,
                self.changes_by_others / len(self.changes) if self.changes else '',
                len(self.authors), calculate_gini(self.authors),
            ]
            #return [len(self.changes), len(self.changed_categories), len(self.users),
            #    len(self.authors), calculate_gini(self.authors),
            #    self.changes_by_others, self.categories_count]
            
    def normalize_tag(name):
        if name is not None and name.startswith('http://who.int/icd#TAG_IM_'):
            name = 'http://who.int/icd#TAG_Internal_Medicine'
        return name
    
    data = []
    all_changes = Change.objects.filter(_instance=settings.INSTANCE).filter(Change.relevant_filter).select_related('apply_to').order_by('author')
    all_categories = Category.objects.filter(instance=settings.INSTANCE)
    all_categories = dict((category.pk, category) for category in all_categories)
    authors = Author.objects.filter(instance=settings.INSTANCE).order_by('name')
    authors = dict((author.pk, author) for author in authors)
    deleted_categories = 0
    tags = defaultdict(TAG)
    for author_id, changes in group(all_changes, lambda c: c.author_id):
        #print author.name
        author = authors[author_id]
        groups = set(normalize_tag(author_group.name) for author_group in author.groups.all())
        cross_changes = 0
        cross_categories = set()
        #changes = len(changes)
        categories = set()
        for change in changes:
            category = all_categories.get(change.apply_to.category_id if change.apply_to is not None else None)
            if category is not None:
                categories.add(category.pk)
                #other = False
                category_tag = normalize_tag(category.primary_tag)
                #if category_tag is not None and category_tag.startswith('http://who.int/icd#TAG_IM_'):
                #    category_tag = 'http://who.int/icd#TAG_Internal_Medicine' 
                if category_tag:
                    #other = 
                    #if category.primary_tag not in groups and category.secondary_tag not in groups:
                    if category_tag not in groups:
                        cross_changes += 1
                        cross_categories.add(category.pk)
                #if category.primary_tag:
                tag = tags[category_tag]
                tag.authors[author.pk] += 1
                tag.changes.append(change)
                tag.changed_categories.add(category.pk)
                if category_tag not in groups:
                    tag.changes_by_others += 1
            else:
                deleted_categories += 1
        tag_groups = []
        for author_group in groups:
            if author_group.startswith(Group.tag_prefix):
                #author_group = normalize_tag(author_group)
                tag_groups.append(author_group)
                tags[author_group].users.append(author)
        author_data = [author.name, u", ".join(tag_groups), len(changes), len(categories), cross_changes, len(cross_categories)]
        #aut
        print author_data
        data.append(author_data)
        
    print "Deleted categories: %d" % deleted_categories
        
    #print data
    print "Save"   
    write_csv('../output/authors_tags_crossings.csv', data)
    
    print "TAGs"
    
    for category in all_categories.itervalues():
        tags[normalize_tag(category.primary_tag)].categories_count += 1
        
    data = []
    for name, tag in sorted(tags.iteritems()):
        data.append([name[len("http://who.int/icd#TAG_"):]] + tag.get_data())
        #data.append(tag.get_data())
        
    print "Save"
    write_csv('../output/authors_tags.csv', data)
            
    #for author in authors:
    #    groups = set(group.name for group in authors.groups.all())
    #    cross_changes = author.changes.filter(Change.relevant_filter).
    
    print "Done"
        
def patterns():
    " Analysis analog to K-CAP paper by S. Falconer et al. "
    
    pattern_analysis_features()
    
def export_authors_network():    
    G = PickledData.objects.get(settings.INSTANCE, 'author_graph')
    for node in G:
        G.node[node]['display'] = username(G.node[node]['name'])
    nx.write_gml(G, '../output/social.gml')
    
    print "Overrides"
    G = PickledData.objects.get(settings.INSTANCE, 'author_graph_directed')
    authors = Author.objects.filter(instance=settings.INSTANCE)
    authors = dict((author.pk, author) for author in authors)
    for node in G:
        G.node[node]['display'] = username(authors[node].name)
        G.node[node]['name'] = authors[node].name
        G.node[node]['changes_count'] = authors[node].changes_count
        G.node[node]['overridden_count'] = authors[node].overridden_count
        G.node[node]['overrides_count'] = authors[node].overrides_count
    nx.write_gml(G, '../output/social_overrides.gml')
    
    #print "Export"
    #nx.write_graphml(G, '../output/social.graphml', prettyprint=True)
    #print "Plot"
    #nx.plot()
    print "Done"
    
    
    
def learn():
    learn_orange()
    
def export():
    #export_r_categories()
    #export_tab_categories()
    #export_timespans(format='r')
    #export_r_timeseries_fast()
    export_changes_accumulated()
    #export_authors_network()
    #export_r_categories()
    #calc_cooccurrences()
    #create_social_network()
    
    #export_follow_ups()
    
def analyse():
    #for baseline in (False, True):
    #analyse_propagation(baseline=False)
    #analyse_propagation(baseline=True)
    #analyse_propagation_baseline()
    #analyse_propagation_export(baseline=True)
    
    analyse_propagation_sessioned(baseline=False)
    analyse_propagation_sessioned_export(baseline=False)
    analyse_propagation_sessioned(baseline=True)
    analyse_propagation_sessioned_export(baseline=True)
    
    #analyse_tags_reverts()
    #analyse_authors()
    #analyse_authors_relative()
    
    #tag_borders()
    
def main():
    argc = len(sys.argv)
    if argc not in (2, 3):
        print "Wrong usage. Please specify a function to call!"
        return
    command = sys.argv[1]
    f = globals()[command]
    if argc == 3:
        f(sys.argv[2])
    else:
        f()

if __name__ == '__main__':
    main()
