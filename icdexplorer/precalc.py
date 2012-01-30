# -*- coding: UTF-8 -*-

"""
ICDexplorer
Pre-calculations before twex can run.

(c) 2011 Jan Poeschko
jan@poeschko.com
"""

from __future__ import division
from __future__ import with_statement

from django.core.management import setup_environ
import settings

setup_environ(settings)

import sys

# to get rid of "RuntimeError: could not create GdkCursor object" when importing networkx
import matplotlib
matplotlib.use("Agg")

import networkx as nx

import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
import re
import cPickle as pickle
import subprocess
import types

import math
import pydot
import os
from collections import defaultdict

import csv

import gc

from django.db.models import Q, Min, Max, Count
from django.conf import settings

from icd.models import (Category, OntologyComponent, LinearizationSpec, AnnotatableThing,
    Change, Annotation, CategoryMetrics, User, Timespan, TimespanCategoryMetrics, Author,
    AuthorCategoryMetrics,
    Property, Group)
from storage.models import PickledData
from quadtree import QuadTree
from icd.util import *

if settings.IS_NCI:
    ROOT_CATEGORY = 'http://www.w3.org/2002/07/owl#Thing'
elif settings.IS_ICTM:
    ROOT_CATEGORY = 'http://who.int/ictm#ICTMCategory'
else:
    ROOT_CATEGORY = 'http://who.int/icd#ICDCategory'
    
def node_name(category):
    if isinstance(category, basestring):
        return category.encode('utf-8')
    return category.name.encode('utf-8')

def createnetwork():
    print "Create network"
    G = nx.DiGraph()
    categories = Category.objects.filter(instance=settings.INSTANCE) #.select_related('change_component')
    print "%d categories" % len(categories)
    for index, category in enumerate(categories):
        if index % 1000 == 0:
            print " %d: %s" % (index, category)
        G.add_node(node_name(category), display=category.display) #, weight=activity)
        parents = category.parents.values_list('name', flat=True)
        if not (parents or category.name == ROOT_CATEGORY):
            print category.name
        for parent_name in parents:
            G.add_edge(node_name(category), node_name(parent_name))
            
    print "Save graph"
    PickledData.objects.set(settings.INSTANCE, 'graph', G)
    print "Network saved"

def call_dot(prog, filename, args, temp_output='output.dot', verbose=True):
    cmdline = [prog, '-Tdot', '-o' + temp_output, filename] + args
    if verbose:
        cmdline.append('-v')
        
    p = subprocess.Popen(
        cmdline,
        stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        
    stderr = p.stderr
    stdout = p.stdout
    
    stdout_output = list()
    while True:
        data = stdout.read()
        if not data:
            break
        stdout_output.append(data)
        if verbose:
            print data
    stdout.close()
        
    stdout_output = ''.join(stdout_output)
    
    if not stderr.closed:
        stderr_output = list()
        while True:
            data = stderr.read()
            if not data:
                break
            stderr_output.append(data)
        stderr.close()
            
        if stderr_output:
            stderr_output = ''.join(stderr_output)
        
    status = p.wait()
    
    if status != 0 :
        raise pydot.InvocationException(
            'Program terminated with status: %d. stderr follows: %s' % (
                status, stderr_output) )
    elif stderr_output:
        print stderr_output
    
    with open(temp_output, 'r') as output:
        result = output.read()
    
    return result

def get_dot_pos(content):
    node_re = re.compile(r'"(.*?)" \[pos="([0-9.e+-]+),([0-9.e+-]+)"')
    pos = {}
    for match in node_re.finditer(content):
        node, x, y = match.group(1), match.group(2), match.group(3)
        x, y = float(x), float(y)
        pos[node] = (x, y)
    # normalize coordinates to [0,1]
    x_min = min(x for x, y in pos.values())
    x_max = max(x for x, y in pos.values())
    y_min = min(y for x, y in pos.values())
    y_max = max(y for x, y in pos.values())
    for node, (x, y) in pos.iteritems():
        pos[node] = ((x-x_min) / (x_max-x_min), (y-y_min) / (y_max-y_min))
    return pos
    
def graphpositions():
    print "Load graph"
    graph_file = '../graph/graph.dot'
    if not os.path.exists(graph_file):
        G = PickledData.objects.get(settings.INSTANCE, 'graph')
        print "Create GraphViz graph"
        edges = G.edges()
        P = pydot.graph_from_edges(edges, directed=True)
        print "Export graph"
        # It seems that nx.write_dot doesn't finish execution => we bypass it
        with open(graph_file, 'w') as file:
            content = P.to_string()
            file.write(content)
    
    print "Layout"
    for layout, key, dot_prog in settings.LAYOUTS:
        print layout
        out_filename = '../graph/positions_%s.dot' % key
        
        if not os.path.exists(out_filename):
            result = call_dot(dot_prog, graph_file, ['-Groot=' + ROOT_CATEGORY],
                temp_output=out_filename)
        
            if not result:
                print "Graphviz layout with %s failed" % dot_prog
                return
            
        else:
            with open(out_filename, 'r') as output:
                result = output.read()
        
        print " Get positions"
        pos = get_dot_pos(result)
        print " Got %d positions" % len(pos)
        
        print " Save"
        PickledData.objects.set(settings.INSTANCE, 'graph_positions_original_%s' % key, pos)
        print " Done"
        
def adjust_positions():
    print "Correct positions to (-1, 1) range with root in center"
    for layout, key, dot_prog in settings.LAYOUTS:
        print layout
        
        pos = PickledData.objects.get(settings.INSTANCE, 'graph_positions_original_%s' % key)
        root_x, root_y = pos[ROOT_CATEGORY]
        pos = dict((node, (x - root_x, y - root_y)) for node, (x, y) in pos.iteritems())
        max_abs_x = max(abs(x) for node, (x, y) in pos.iteritems())
        max_abs_y = max(abs(y) for node, (x, y) in pos.iteritems())
        max_abs = max(max_abs_x, max_abs_y)
        pos = dict((node, (x / max_abs, y / max_abs)) for node, (x, y) in pos.iteritems())
        PickledData.objects.set(settings.INSTANCE, 'graph_positions_%s' % key, pos)
    print "Done"
    
def store_positions():
    print "Store positions"
    categories = list(Category.objects.filter(instance=settings.INSTANCE).select_related('change_component'))
    category_metrics = list(CategoryMetrics.objects.filter(instance=settings.INSTANCE).order_by('category').select_related('category'))
    author_category_metrics = list(AuthorCategoryMetrics.objects.filter(instance=settings.INSTANCE).order_by('category', 'author').select_related('category'))
    pos = {}
    for layout, key, dot_prog in settings.LAYOUTS:
        print layout
        pos[key] = PickledData.objects.get(settings.INSTANCE, 'graph_positions_%s' % key)
        
    for name, items, key_func in [("Category", categories, lambda item: item.name),
        ("CategoryMetrics", category_metrics, lambda item: item.category.name),
        ("AuthorCategoryMetrics", author_category_metrics, lambda item: item.category.name)]:
        print name
        for index, category in enumerate(items):
            if index % 1000 == 0:
                print " %d: %s" % (index, category)
            for layout, key, dot_prog in settings.LAYOUTS:
                try:
                    x, y = pos[key][key_func(category)]
                    setattr(category, 'x_' + key, x)
                    setattr(category, 'y_' + key, y)
                    category.save()
                except KeyError:
                    pass
    print "Done"
    
def exportnetwork():
    G = PickledData.objects.get(settings.INSTANCE, 'graph')
    nx.write_graphml(G, 'graph.graphml', prettyprint=True)
    
def lineargraphs():
    linearizations = LinearizationSpec.objects.values_list('linearization', flat=True).distinct()
    linearizations = list(linearizations)
    print linearizations
    categories = Category.objects.select_related('change_component')
    categories = list(categories)
    graphs = {}
    for linearization in linearizations:
        print linearization
        G = nx.DiGraph()
        for index, category in enumerate(categories):
            if index % 100 == 0:
                print " %d: %s" % (index, category)
            try:
                parent = category.linearizations_child.get(linearization=linearization).parent
            except (Category.DoesNotExist, LinearizationSpec.DoesNotExist):
                parents_count = category.parents.count()
                for parent in category.parents.all():
                    break
            G.add_edge(category.name, parent.name)
        graphs[linearization] = G
            
    PickledData.objects.set(settings.INSTANCE, 'graphs_linear', graph)
    
def first(items):
    for item in items:
        if item is not None:
            return item
    return None

CAMEL_RE = re.compile(r'([a-z])([A-Z])')

def normalize_property(name):
    name = name.replace("'", '')
    name = CAMEL_RE.sub(lambda m: '%s %s' % (m.group(1), m.group(2)), name)
    name = name.lower()
    if name in ('inclusion', 'exclusion'):
        name += 's'
    if name in ('synonyms',):
        name = name[:-1]
    if name == 'definition':
        name = 'short definition'
    return name
    
def compute_extra_change_data():
    print "Compute extra change data for composite changes"
    
    def compile(exprs):
        if not isinstance(exprs, (list, tuple)):
            exprs = [exprs]
        return [re.compile('^' + expr + '$', flags=re.DOTALL) for expr in exprs]
    
    change_kinds = [(kind, compile(exprs)) for kind, exprs in Change.kinds.iteritems()]
    change_kinds = sorted(change_kinds, key=lambda (k, e): (-len(k), k))
    
    changes = Change.objects.filter(_instance=settings.INSTANCE)
    changes = changes.filter(composite=settings.INSTANCE, type="Composite_Change")
    changes = changes.order_by('_name')

    for index, change in enumerate(changes):
        if index % 1000 == 0:
            print "%d: %s" % (index, change._name)
        if change.action == 'Composite_Change':
            for kind, exprs in change_kinds:
                match = first(expr.match(change.browser_text) for expr in exprs)
                if match is not None:
                    change.kind = kind
                    for attr in ('property', 'for_property', 'old_value', 'new_value', 'additional_info', 'apply_to_url'):
                        value = ''
                        try:
                            value = match.group(attr) or ''
                            value = value.strip()
                        except IndexError:
                            pass
                        setattr(change, attr, value)
                    change.property_original = change.property
                    change.property = normalize_property(change.property)
                    change.save()
                    break
    print "Done"
    
def compute_extra_author_data():
    print "Compute extra author data"
    authors = Author.objects.filter(instance=settings.INSTANCE).order_by('name')
    for author in authors:
        print author.name
        author.sessions_count = author.changes.filter(ends_session=True).count()
        author.overrides_count = author.overrides.filter(ends_session=True).count()
        author.overridden_count = author.changes.filter(ends_session=True, override__isnull=False).count()
        author.overridden_rel = author.overridden_count * 1.0 / author.sessions_count if author.sessions_count > 0 else 0
        author.save()
    print "Done"
    
def compute_follow_ups():
    print "Compute follow-ups"
    follow_ups = {None: {}, 3: {}}
    changes = Change.objects.filter(_instance=settings.INSTANCE).filter(Change.relevant_filter).order_by('_name')
    for index, change in enumerate(changes):
        if index % 1000 == 0:
            print "%d: %s" % (index, change._name)
        if change.property:
            following = Change.objects.filter(apply_to=change.apply_to_id, timestamp__gte=change.timestamp)
            overrides = following.filter(property=change.property).exclude(author=change.author_id)
            try:
                change.override = overrides.order_by('timestamp')[0]
                change.override_by = change.override.author
                change.save()
            except IndexError:
                pass
            for timespan, follows in follow_ups.iteritems():
                following_timespan = following
                if timespan is not None:
                    following_timespan = following_timespan.filter(timestamp__lte=change.timestamp + timedelta(hours=timespan))
                other_properties = following_timespan.values_list('property', flat=True)
                for property in other_properties:
                    key = (change.property, property)
                    follows[key] = follows.get(key, 0) + 1
    PickledData.objects.set(settings.INSTANCE, 'follow_ups', follow_ups)
    print "Done"
    
def compute_sessions():
    print "Compute sessions"
    all_changes = Change.objects.filter(_instance=settings.INSTANCE).exclude(property='').order_by('apply_to', 'property', 'timestamp')
    last = None
    last_change = None
    for apply_to_property, changes in group(debug_iter(all_changes), lambda change: (change.apply_to_id, change.property)):
        for author, author_changes in group(changes, lambda change: change.author_id):
            last_change = author_changes[-1]
            last_change.ends_session = True
            last_change.save()
    print "Done"
    
def compute_author_reverts():
    print "Compute author reverts"
    
    from django.db import connection
    
    cursor = connection.cursor()

    reverts = {}
    cursor.execute("""
select author_id, override_by_id, count(*) from icd_change
where _instance=%s and ends_session and override_by_id is not null
group by author_id, override_by_id;
""", [settings.INSTANCE])
    rows = cursor.fetchall()
    for author, revert_by, count in rows:
        reverts[(revert_by, author)] = count
        
    print "Save"
    PickledData.objects.set(settings.INSTANCE, 'author_overrides', reverts)
    print "Done"
    
def find_annotation_components():
    print "Find annotation components"
    annotations = Annotation.objects.filter(instance=settings.INSTANCE).select_related('annotates').order_by('name')
    print str(len(annotations))
    for index, annotation in enumerate(annotations):
        #if index < 7700:
        # continue
        if index % 1000 == 0:
            print "%d: %s" % (index, annotation.name)
        component = annotation
        while True:
            try:
                component = component.annotates
            except AnnotatableThing.DoesNotExist:
                component = None
                break
            try:
                component = component.ontologycomponent
                break
            except AnnotatableThing.DoesNotExist:
                try:
                    component = component.annotation
                except:
                    print component.name
        annotation.component = component
        annotation.save()
        
def find_change_categories():
    print "Find change categories"
    changes = Change.objects.filter(instance=settings.INSTANCE).order_by('pk') #.select_related('composite').order_by('name')
    #changes = changes.filter(pk__gte=settings.INSTANCE + "_4_annotation_Thesaurus_Class211442")
    #changes = changes.only('composite', 'name', 'apply_to')
    for index, change in enumerate(changes):
        if index % 1000 == 0:
            print "%d: %s" % (index, change.name)
        composite = change
        while composite.composite_id:
            try:
                composite = composite.composite
            except Change.DoesNotExist:
                break
        if change != composite:
            try:
                change.apply_to = composite.apply_to
            except OntologyComponent.DoesNotExist:
                print "No apply_to: %s (composite: %s) -> %s" % (change, composite, composite.apply_to_id)
                change.apply_to = None
            change.save()
        
def calc_author_metrics(from_name=None, to_name=None):
    print "Calculate author metrics"
    all_categories = Category.objects.filter(instance=settings.INSTANCE)
    categories = all_categories.select_related('chao')
    categories = list(categories)
    authors = Author.objects.filter(instance=settings.INSTANCE).order_by('name')
    authors = list(authors)
    G = PickledData.objects.get(settings.INSTANCE, 'graph')
    print "Get existing metrics"
    all_metrics_instances = AuthorCategoryMetrics.objects.filter(instance=settings.INSTANCE)
    all_metrics_instances = dict(((metrics.author.pk, metrics.category.pk), metrics) for metrics in all_metrics_instances)
    for author in authors:
        if from_name is not None and author.name < from_name:
            continue
        if to_name is not None and author.name >= to_name:
            continue
        print author.name
        annotated_changes = all_categories.filter(chao__changes__author=author)
        if settings.IS_ICD:
            annotated_changes = annotated_changes.filter(chao__changes__action="Composite_Change")
        annotated_changes = annotated_changes.exclude(chao__changes__kind="Automatic").annotate(changes_count=Count('chao__changes'))
        annotated_changes = dict((c.pk, c.changes_count) for c in annotated_changes)
        annotated_annotations = all_categories.filter(chao__annotations__author=author).annotate(annotations_count=Count('chao__annotations'))
        annotated_annotations = dict((c.pk, c.annotations_count) for c in annotated_annotations)
        all_metrics = {}
        any_activity = False
        for index, category in enumerate(categories):
            try:
                metrics = all_metrics_instances[(author.pk, category.pk)]
            except KeyError:
                metrics = AuthorCategoryMetrics(author=author, category=category, instance=settings.INSTANCE)
                all_metrics_instances[(author.pk, category.pk)] = metrics
                metrics.set_pos(category)
            metrics.changes = annotated_changes.get(category.pk, 0)
            metrics.annotations = annotated_annotations.get(category.pk, 0)
            metrics.activity = metrics.changes + metrics.annotations
            metrics.acc_changes = metrics.acc_annotations = metrics.acc_activity = 0
            if metrics.activity > 0:
                metrics.save()
                any_activity = True
            all_metrics[category.name] = metrics.get_metrics_dict()
        if any_activity:
            print " Accumulate"
            for index, category in enumerate(categories):
                try:
                    metrics = all_metrics_instances[(author.pk, category.pk)]
                except KeyError:
                    metrics = AuthorCategoryMetrics(author=author, category=category, instance=settings.INSTANCE)
                    metrics.changes = metrics.annotations = metrics.activity = 0
                    metrics.set_pos(category)
                calculate_accumulated(metrics, all_metrics, G)
                if metrics.acc_activity > 0:
                    metrics.save()
    print "Done"
   
     
def calc_weights():
    all_categories = Category.objects.filter(instance=settings.INSTANCE)
    categories = all_categories.select_related('chao')
    categories = list(categories)
    authors = Author.objects.order_by('instance_name')
    authors = list(author.instance_name for author in authors)
    G = PickledData.objects.get(settings.INSTANCE, 'graph')
    weights = {}
    for author in authors + [None]:
        print author
        weights[author] = {}
        for weight_id, weight_name, weight_func in settings.WEIGHTS:
            print " " + weight_name
            weights[author][weight_id] = [{}, {}] # single / accumulated
            weight = weights[author][weight_id]
            filter_changes = {} if author is None else {'chao__changes__author': author}
            annotated_changes = all_categories.filter(**filter_changes).annotate(changes_count=Count('chao__changes'))
            annotated_changes = dict((c.pk, c.changes_count) for c in annotated_changes)
            filter_annotations = {} if author is None else {'chao__annotations__author': author}
            annotated_annotations = all_categories.filter(**filter_annotations).annotate(annotations_count=Count('chao__annotations'))
            annotated_annotations = dict((c.pk, c.annotations_count) for c in annotated_annotations)
            for index, category in enumerate(categories):
                w = weight_func(annotated_changes.get(category.pk, 0), annotated_annotations.get(category.pk, 0))
                if w > 0:
                    weight[0][category.name] = w
            for index, category in enumerate(categories):
                all_children = set()
                def include(node):
                    if node not in all_children:
                        all_children.add(node)
                        for child in G.predecessors_iter(node):
                            include(child)
                include(category.name)
                childs_weight = sum(weight[0].get(child, 0) for child in all_children)
                if childs_weight > 0:
                    weight[1][category.name] = childs_weight
    print "Save"
    PickledData.objects.set(settings.INSTANCE, 'weights', weights)
    print "Done"

def compact_weights():
    weights = PickledData.objects.get(settings.INSTANCE, 'weights')
    for author in weights:
        print author
        for id in weights[author]:
            for acc in (0, 1):
                weights[author][id][acc] = dict((c, w) for c, w in weights[author][id][acc].iteritems() if w > 0)
    print "Save"
    PickledData.objects.set(settings.INSTANCE, 'weights', weights)
    print "Done"

    
def get_indirect_children(G, all_children, node):
    if node not in all_children:
        all_children.add(node)
        for child in G.predecessors_iter(node):
            get_indirect_children(G, all_children, child)
    
def get_indirect_parents(G, all_parents, node):
    if node not in all_parents:
        all_parents.add(node)
        for parent in G.successors_iter(node):
            get_indirect_parents(G, all_parents, parent)

def calculate_accumulated(metrics, all_metrics, G):
    all_children = set()
                
    get_indirect_children(G, all_children, metrics.category.name)
    for key, value, description in metrics.get_metrics():
        if key.startswith('acc_'):
            childs_sum = sum(all_metrics.get(child, {}).get(key[4:], 0) for child in all_children)
            setattr(metrics, key, childs_sum)
    
def calc_metrics(accumulate_only=False, compute_centrality=True):
    print "Construct graph"
    G = PickledData.objects.get(settings.INSTANCE, 'graph')
    print "Nodes: %d" % len(G)
    print "Edges: %d" % G.size()
    if ROOT_CATEGORY in G:
        print "Level 1: %d" % len(G.predecessors(node_name(ROOT_CATEGORY)))
    G_undirected = G.to_undirected()
    print "Calc metrics"
    categories = Category.objects.filter(instance=settings.INSTANCE).order_by('name') #.select_related('chao')
    categories = list(categories)
    if compute_centrality:
        print "Betweenness centrality"
        centrality = nx.betweenness_centrality(G)
        print "Betweenness undirected"
        centrality_undirected = nx.betweenness_centrality(G_undirected)
        print "Pagerank"
        pageranks = nx.pagerank(G)
        print "Closeness centrality"
        closeness_centrality = nx.closeness_centrality(G_undirected)
        print "Clustering"
        clustering = nx.clustering(G_undirected)
    all_metrics = {}
    for index, category in enumerate(categories):
        node = node_name(category)
        if settings.IS_WIKI or index % 1000 == 0:
            print '%d: %s' % (index, node)
        try:
            metrics = category.metrics
        except CategoryMetrics.DoesNotExist:
            metrics = CategoryMetrics(category=category)
        metrics.instance = settings.INSTANCE
        if not accumulate_only:
            changes = []
            annotations = []
            for chao in category.chao.all():
                changes += list(chao.changes.filter(Change.relevant_filter).order_by('timestamp').only('property', 'author'))
                annotations += list(chao.annotations.filter(Annotation.relevant_filter))
            metrics.changes = len(changes)
            metrics.annotations = len(annotations)
            metrics.activity = metrics.changes + metrics.annotations
            authors_changes = set()
            authors_annotations = set()
            authors = {}
            authors_by_property = {}
            for change in changes:
                author = change.author_id
                authors_changes.add(author)
                authors[author] = authors.get(author, 0) + 1
                if change.property:
                    if change.property not in authors_by_property:
                        authors_by_property[change.property] = [author]
                    if authors_by_property[change.property][-1] != author:
                        authors_by_property[change.property].append(author)
            for annotation in annotations:
                author = annotation.author_id
                authors_annotations.add(author)
                authors[author] = authors.get(author, 0) + 1
            metrics.authors_changes = len(authors_changes)
            metrics.authors_annotations = len(authors_annotations)
            metrics.authors = len(authors)
            metrics.authors_gini = calculate_gini(authors)
            metrics.overrides = sum(len(prop) - 1 for prop in authors_by_property.itervalues())
            metrics.edit_sessions = sum(len(prop) for prop in authors_by_property.itervalues())
            metrics.authors_by_property = sum(len(set(prop)) for prop in authors_by_property.itervalues())
            try:
                if ROOT_CATEGORY in G:
                    metrics.depth = nx.shortest_path_length(G, source=node, target=node_name(ROOT_CATEGORY))
                else:
                    metrics.depth = 0
            except nx.exception.NetworkXError:
                metrics.depth = 0
            if compute_centrality:
                metrics.pagerank = pageranks[node]
                metrics.betweenness_centrality = centrality[node]
                metrics.betweenness_centrality_undirected = centrality_undirected[node]
                metrics.closeness_centrality = closeness_centrality[node]
                metrics.clustering = clustering[node]
            metrics.parents = category.parents.count()
            metrics.children = category.children.count()
            
            for key, value, descriptin in metrics.get_metrics():
                if key.startswith('acc_'):
                    setattr(metrics, key, 0)
            
            metrics.save()
            
        all_metrics[category.name] = metrics.get_metrics_dict()
    
    print "Accumulate"
    
    for index, category in enumerate(categories):
        if index % 1000 == 0:
            print '%d: %s' % (index, category.name)
        calculate_accumulated(category.metrics, all_metrics, G)
        category.metrics.save()
        
    print "Done"
    
def calc_timespan_metrics():
    print "Calculate timespan metrics"
    MINMAX_CHANGES_DATE = Change.objects.filter(instance=settings.INSTANCE).aggregate(min=Min('timestamp'), max=Max('timestamp'))
    MIN_CHANGES_DATE = MINMAX_CHANGES_DATE['min'] #.date()
    MAX_CHANGES_DATE = MINMAX_CHANGES_DATE['max'] #.date() + timedelta(days=1)
    
    split = datetime(2011, 04, 21)
    timespans = [
        Timespan.objects.get_or_create(instance=settings.INSTANCES[1], start=split,
            stop=datetime(2011, 07, 28))[0], # gets rid of initial WHO changes
        Timespan.objects.get_or_create(instance=settings.INSTANCES[0], start=MIN_CHANGES_DATE,
            stop=split)[0]
    ]
    
    timespans[1].following.add(timespans[0])
    
    for timespan in timespans:
        timespan.save()
        
    for timespan in timespans[:1]:
        print (timespan.start, timespan.stop)
        #timespan.save()
        instance = timespan.instance
        print "Load categories"
        categories = Category.objects.filter(instance=instance).order_by('name').select_related('chao')
        categories = list(categories)
        CATEGORIES = dict((category.name, category) for category in categories)
        print "Load graph"
        G = PickledData.objects.get(instance, 'graph')
        print "Graph loaded"
        for index, category in enumerate(categories):
            if index % 1000 == 0:
                print '%d: %s' % (index, category.name)
            try:
                metrics = category.timespan_metrics.get(timespan=timespan)
            except TimespanCategoryMetrics.DoesNotExist:
                metrics = TimespanCategoryMetrics(category=category, timespan=timespan)
            # TODO: change this for multiple chaos, as in calc_metrics
            chao = category.chao
            if chao is not None:
                changes = chao.changes.filter(Change.relevant_filter, timestamp__range=(timespan.start, timespan.stop))
                annotations = chao.annotations.filter(Annotation.relevant_filter, created__range=(timespan.start, timespan.stop))
                changes, annotations = list(changes), list(annotations)
                
                metrics.changes = len(changes)
                metrics.annotations = len(annotations)
                authors_changes = set()
                authors_annotations = set()
                authors = {}
                for change in changes:
                    author = change.author_id
                    authors_changes.add(author)
                    authors[author] = authors.get(author, 0) + 1
                for annotation in annotations:
                    author = annotation.author_id
                    authors_annotations.add(author)
                    authors[author] = authors.get(author, 0) + 1
                metrics.authors_changes = len(authors_changes)
                metrics.authors_annotations = len(authors_annotations)
                metrics.authors = len(authors)
                metrics.authors_gini = calculate_gini(authors)
                
                metrics.days_after_last_change = min_null((days(timespan.stop - change.timestamp) for change in changes))
                metrics.days_before_first_change = min_null((days(change.timestamp - timespan.start) for change in changes))
                metrics.days_after_median_change = median(days(timespan.stop - change.timestamp) for change in changes)
                metrics.days_after_last_annotation = min_null((days(timespan.stop - annotation.created) for annotation in annotations))
                metrics.days_before_first_annotation = min_null((days(annotation.created - timespan.start) for annotation in annotations))
                metrics.days_after_median_annotation = median(days(timespan.stop - annotation.created) for annotation in annotations)
                
                parents = [CATEGORIES[succ] for succ in G.successors(category.name)]
                children = [CATEGORIES[pred] for pred in G.predecessors(category.name)]
                metrics.changes_parents = sum(parent.chao.changes.filter(timestamp__range=(timespan.start, timespan.stop)).count()
                    if parent.chao else 0 for parent in parents)
                metrics.annotations_parents = sum(parent.chao.annotations.filter(created__range=(timespan.start, timespan.stop)).count()
                    if parent.chao else 0 for parent in parents)
                metrics.changes_children = sum(child.chao.changes.filter(timestamp__range=(timespan.start, timespan.stop)).count()
                    if child.chao else 0 for child in children)
                metrics.annotations_children = sum(child.chao.annotations.filter(created__range=(timespan.start, timespan.stop)).count()
                    if child.chao else 0 for child in children)
            else:
                metrics.changes = metrics.annotations = 0
                metrics.authors_changes = metrics.authors_annotations = metrics.authors = 0
                metrics.authors_gini = 0
                metrics.changes_parents = 0
                metrics.annotations_parents = 0
                metrics.changes_children = 0
                metrics.annotations_children = 0
            metrics.save()
    #PickledData.objects.set(settings.INSTANCE, 'weights', weights)
    
def value_to_csv(value, na="NA"):
    if value is None:
        return na
    if isinstance(value, (int, basestring)):
        return unicode(value)
    else:
        return '%f' % value

def write_csv(filename, values, na="NA"):
    content = u'\n'.join(u'\t'.join(value_to_csv(value, na) for value in row) for row in values)
    with open(filename, 'w') as file:
        file.write(content.encode('utf-8'))

def createquadtree():
    categories = dict((category.name, category) for category in Category.objects.filter(instance=settings.INSTANCE).select_related('chao'))
    G = PickledData.objects.get(settings.INSTANCE, 'graph')
    weights = PickledData.objects.get(settings.INSTANCE, 'weights')
    for layout, dot_prog, dummy in settings.LAYOUTS:
        if layout == "Radial":
            continue
        print layout
        positions = PickledData.objects.get(settings.INSTANCE, 'graph_positions_%s' % dot_prog)
        
        for author in sorted(weights.keys()):
            if author < "2011-11-24_04h02mTomris Turmen":
                continue
            print "Build tree for '%s'" % author
            qt = dict(((id, acc), QuadTree(-1, 1, -1, 1)) for id, name, f in settings.WEIGHTS for acc in (0, 1))
            for index, (name, pos) in enumerate(positions.iteritems()):
                if index % 1000 == 0:
                    print (index, name)
                x, y = pos
                category = categories[name]
                #count = hashtags.get(tag, 0)
                try:
                    depth = nx.shortest_path_length(G, source=name, target=ROOT_CATEGORY)
                except nx.exception.NetworkXError:
                    continue
                for weight_id, weight_name, weight_func in settings.WEIGHTS:
                    for accumulate in (0, 1):
                        #activity = G.node[name]['weight']
                        #weight = weight_func(category)
                        weight = weights[author][weight_id][accumulate].get(category.name, 0)
                        #weight = weights.get((weight_id, category.name), 0)
                        #if weight > 0:
                        # print name
                        if weight > 0:
                            qt[(weight_id, accumulate)].insert(x, y, name, (-depth, weight))
                
            print "Save"
            #with open(settings.DATA_DIR + 'hashtags_positions_tree', 'wb') as data_file:
            # pickle.dump(qt, data_file, protocol=pickle.HIGHEST_PROTOCOL)
            PickledData.objects.set(settings.INSTANCE, 'graph_positions_tree_%s_%s' % (dot_prog, author or ''), qt)
            print "Saved"
        
        #del qt
        del positions

      
def corr2latex():
    tables = [r"""changes & 1.00 & 0.70 & 0.87 & 0.88 & 0.68 & 0.94 & 0.35 & 0.19 & -0.09 & 0.08 & 0.21 & 0.32 & 0.20 & 0.17 \\
annotations & 0.70 & 1.00 & 0.66 & 0.65 & 0.97 & 0.77 & 0.45 & 0.15 & -0.05 & 0.09 & 0.16 & 0.30 & 0.15 & 0.13 \\
authors & 0.87 & 0.66 & 1.00 & 0.99 & 0.67 & 0.93 & 0.32 & 0.21 & -0.08 & 0.08 & 0.23 & 0.30 & 0.22 & 0.15 \\
authors\_changes & 0.88 & 0.65 & 0.99 & 1.00 & 0.67 & 0.93 & 0.32 & 0.21 & -0.07 & 0.08 & 0.23 & 0.30 & 0.22 & 0.15 \\
authors\_annotations & 0.68 & 0.97 & 0.67 & 0.67 & 1.00 & 0.77 & 0.37 & 0.15 & 0.01 & 0.08 & 0.16 & 0.27 & 0.16 & 0.06 \\
authors\_gini & 0.94 & 0.77 & 0.93 & 0.93 & 0.77 & 1.00 & 0.52 & 0.38 & -0.23 & 0.14 & 0.40 & 0.50 & 0.39 & 0.31 \\
parents & 0.35 & 0.45 & 0.32 & 0.32 & 0.37 & 0.52 & 1.00 & 0.15 & -0.22 & 0.18 & 0.15 & 0.49 & 0.15 & 0.29 \\
children & 0.19 & 0.15 & 0.21 & 0.21 & 0.15 & 0.38 & 0.15 & 1.00 & -0.27 & 0.09 & 1.00 & 0.89 & 1.00 & 0.31 \\
depth & -0.09 & -0.05 & -0.08 & -0.07 & 0.01 & -0.23 & -0.22 & -0.27 & 1.00 & -0.09 & -0.26 & -0.31 & -0.27 & -0.90 \\
clustering & 0.08 & 0.09 & 0.08 & 0.08 & 0.08 & 0.14 & 0.18 & 0.09 & -0.09 & 1.00 & 0.09 & 0.08 & 0.09 & 0.10 \\
betweenness\_centrality & 0.21 & 0.16 & 0.23 & 0.23 & 0.16 & 0.40 & 0.15 & 1.00 & -0.26 & 0.09 & 1.00 & 0.89 & 1.00 & 0.31 \\
betweenness\_centrality\_undirected & 0.32 & 0.30 & 0.30 & 0.30 & 0.27 & 0.50 & 0.49 & 0.89 & -0.31 & 0.08 & 0.89 & 1.00 & 0.89 & 0.38 \\
pagerank & 0.20 & 0.15 & 0.22 & 0.22 & 0.16 & 0.39 & 0.15 & 1.00 & -0.27 & 0.09 & 1.00 & 0.89 & 1.00 & 0.31 \\
closeness\_centrality & 0.17 & 0.13 & 0.15 & 0.15 & 0.06 & 0.31 & 0.29 & 0.31 & -0.90 & 0.10 & 0.31 & 0.38 & 0.31 & 1.00""",
    r"""changes & 1.00 & 0.50 & 0.49 & 0.49 & 0.39 & 0.70 & 0.27 & 0.06 & -0.15 & 0.06 & 0.07 & 0.10 & 0.09 & 0.22 \\
annotations & 0.50 & 1.00 & 0.57 & 0.56 & 0.85 & 0.60 & 0.55 & 0.07 & -0.16 & 0.06 & 0.11 & 0.08 & 0.04 & 0.30 \\
authors & 0.49 & 0.57 & 1.00 & 0.99 & 0.64 & 0.79 & 0.37 & 0.12 & -0.11 & 0.04 & 0.14 & 0.18 & 0.15 & 0.24 \\
authors\_changes & 0.49 & 0.56 & 0.99 & 1.00 & 0.63 & 0.78 & 0.36 & 0.12 & -0.10 & 0.04 & 0.14 & 0.19 & 0.15 & 0.24 \\
authors\_annotations & 0.39 & 0.85 & 0.64 & 0.63 & 1.00 & 0.61 & 0.41 & 0.06 & -0.01 & 0.05 & 0.06 & 0.04 & 0.03 & 0.15 \\
authors\_gini & 0.70 & 0.60 & 0.79 & 0.78 & 0.61 & 1.00 & 0.40 & 0.13 & -0.18 & 0.08 & 0.11 & 0.08 & 0.04 & 0.32 \\
parents & 0.27 & 0.55 & 0.37 & 0.36 & 0.41 & 0.40 & 1.00 & 0.08 & -0.22 & 0.10 & 0.10 & 0.06 & 0.01 & 0.35 \\
children & 0.06 & 0.07 & 0.12 & 0.12 & 0.06 & 0.13 & 0.08 & 1.00 & -0.17 & -0.00 & 0.42 & 0.38 & 0.24 & 0.23 \\
depth & -0.15 & -0.16 & -0.11 & -0.10 & -0.01 & -0.18 & -0.22 & -0.17 & 1.00 & -0.05 & -0.10 & -0.09 & -0.06 & -0.88 \\
clustering & 0.06 & 0.06 & 0.04 & 0.04 & 0.05 & 0.08 & 0.10 & -0.00 & -0.05 & 1.00 & -0.00 & -0.00 & -0.00 & 0.06 \\
betweenness\_centrality & 0.07 & 0.11 & 0.14 & 0.14 & 0.06 & 0.11 & 0.10 & 0.42 & -0.10 & -0.00 & 1.00 & 0.78 & 0.50 & 0.16 \\
betweenness\_centrality\_undirected & 0.10 & 0.08 & 0.18 & 0.19 & 0.04 & 0.08 & 0.06 & 0.38 & -0.09 & -0.00 & 0.78 & 1.00 & 0.78 & 0.15 \\
pagerank & 0.09 & 0.04 & 0.15 & 0.15 & 0.03 & 0.04 & 0.01 & 0.24 & -0.06 & -0.00 & 0.50 & 0.78 & 1.00 & 0.10 \\
closeness\_centrality & 0.22 & 0.30 & 0.24 & 0.24 & 0.15 & 0.32 & 0.35 & 0.23 & -0.88 & 0.06 & 0.16 & 0.15 & 0.10 & 1.00"""
    ]
    names = ["ch", "ann", "auth", "a\\_ch", "a\\_ann", "a\\_gini", "par", "child", "dep", "cl", "bc", "bcu", "pr", "cc"]
    for table in tables:
        values = [row.split('&') for row in table.split(r'\\')]
        result = []
        for index, row in enumerate(values):
            row = row[1:]
            row[index] = names[index]
            result.append(row)
        print ""
        print "\\\\ \n".join("&".join('%8s' % value for value in row) for row in result)
        print ""
        
class CachedQuery(object):
    def __init__(self, model):
        self.model = model
        self.cache = {}
        
    def get(self, pk, **fields):
        try:
            return self.cache[pk]
        except KeyError:
            instance, created = model.objects.get_or_create(pk, **fields)
            self.cache[pk] = instance
            return instance
        
    def __iter__(self):
        return self.cache.itervalues()
        
def create_authors():
    from django.db import connection
    
    cursor = connection.cursor()
    
    authors = CachedQuery(Author)
    
    print "Changes"
    """changes = cursor.execute(""select icd_change.author_id, count(*) as c
from icd_change
where icd_change._instance=%s
and ((icd_change.action = "Composite_Change" and kind != "Automatic")
or (icd_change.action = ""))
group by icd_change.author_id
order by c desc"", [settings.INSTANCE])"""

    #for row in cursor.fetchall():
    changes = Change.objects.filter(instance=settings.INSTANCE).filter(Change.relevant_filter)
    author_ids = changes.values_list('author_id', flat=True)
    #for change in debug_iter(changes):
    for author_id in debug_iter(author_ids):
        author = authors.get(author_id, instance=settings.INSTANCE,
            name=author_id[len(settings.INSTANCE):])
        author.changes_count += 1
        """name, count = row
author, created = Author.objects.get_or_create(instance_name=name,
instance=settings.INSTANCE, name=name[len(settings.INSTANCE):])
author.changes_count = count
author.save()"""
    for author in debug_iter(authors):
        author.save()

    print "Annotations"
    annotations = cursor.execute("""select icd_annotation.author_id, count(*) as c
from icd_annotation
where icd_annotation._instance=%s
group by icd_annotation.author_id
order by c desc""", [settings.INSTANCE])
    for row in cursor.fetchall():
        name, count = row
        author, created = Author.objects.get_or_create(instance_name=name,
            instance=settings.INSTANCE, name=name[len(settings.INSTANCE):])
        author.annotations_count = count
        author.save()
    
    print "Done"
    
def load_extra_authors_data():
    print "Load extra authors data"
    
    if settings.IS_ICD:
        with open(settings.INPUT_DIR + 'metaproject_users_2_group_exported.csv', 'rb') as f:
            reader = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
            reader.next()
            for row in reader:
                name, groups = row
                author, created = Author.objects.get_or_create(instance_name=settings.INSTANCE + name,
                    instance=settings.INSTANCE, name=name)
                groups = groups.split(',')
                for group_name in groups:
                    group_name = group_name.strip().strip('"')
                    group, created = Group.objects.get_or_create(instance=settings.INSTANCE, name=group_name)
                    author.groups.add(group)
    
    """csv = open('../input/users.csv', 'r')
authors = Author.objects.filter(instance=settings.INSTANCE).order_by('name')
authors_by_name = {}
for author in authors:
name = author.name
if name in AUTHOR_SUBS:
name = AUTHOR_SUBS[name]
if name not in authors_by_name:
authors_by_name[name] = []
authors_by_name[name].append(author)
for index, row in enumerate(csv):
if index < 1:
continue # skip header line
values = row.split(',')
print values
#name = pop(values)
#email = pop(values)
name, email, affiliation, tag_member, managing_editor = pop_values(values, 5, default='')
corresponding_authors = authors_by_name.get(name, [])
for author in corresponding_authors:
author.email = email
author.affiliation = affiliation
author.tag_member = {'yes': True, 'no': False}.get(tag_member.strip().lower(), None)
author.managing_editor = managing_editor.strip().lower() == 'yes'
author.save()"""
    
def calc_cooccurrences():
    print "Calculate co-occurrences"
    result = {}
    categories = Category.objects.filter(instance=settings.INSTANCE).order_by('name').select_related('chao')
    print "Changes"
    changes = Change.objects.filter(instance=settings.INSTANCE).filter(Change.relevant_filter).select_related('apply_to')
    changes_by_category = defaultdict(set)
    for change in debug_iter(changes):
        #changes = dict((change.apply_to.category_id, change) for change in changes)
        if change.apply_to is not None:
            changes_by_category[change.apply_to.category_id].add(change.author_id)
    del changes
    print "Annotations"
    annotations = Annotation.objects.filter(instance=settings.INSTANCE).select_related('component')
    annotations_by_category = defaultdict(set)
    for annotation in debug_iter(annotations):
        if annotation.component is not None:
            annotations_by_category[annotation.component.category_id].add(annotation.author_id)
    del annotations
    
    print "Categories"
    for index, category in enumerate(categories):
        if index % 1000 == 0:
            print (index, category)
        authors = set()
        for change in changes_by_category.get(category.pk, []):
            authors.add(change)
        for annotation in annotations_by_category.get(category.pk, []):
            authors.add(annotation)
        for author in authors:
            for other in authors:
                if author != other:
                    result[(author, other)] = result.get((author, other), 0) + 1
    print "Result:"
    print result
            
    print "Save"
    PickledData.objects.set(settings.INSTANCE, 'author_cooccurrences', result)

    print "Done"
    
def create_properties_network():
    print "Create properties network"
    follow_ups = PickledData.objects.get(settings.INSTANCE, 'follow_ups')
    G = nx.DiGraph()
    #print follow_ups
    #for node in
    for (u, v), count in follow_ups[None].iteritems():
        if u and v:
            G.add_edge(u, v, count=count)
    """for node in G:
author = Author.objects.get(instance_name=node)
print "%s: %d" % (author.name, author.changes_count)
G.node[node]['name'] = author.name
G.node[node]['changes'] = int(author.changes_count)
G.node[node]['annotations'] = int(author.annotations_count)
G.node[node]['activity'] = int(author.changes_count + author.annotations_count)"""
    #del G['WHO']
    #print "Save"
    #PickledData.objects.set(settings.INSTANCE, 'author_graph', G)
    #print G.nodes()
    print "Positions"
    pos = nx.spring_layout(G, scale=2)
    pos = dict((node, (p[0] - 1, p[1] - 1)) for node, p in pos.iteritems())
    PickledData.objects.set(settings.INSTANCE, 'properties_graph_positions', pos)
    
    print "Done"
    
def create_authors_network():
    print "Create authors network"
    cooccurrences = PickledData.objects.get(settings.INSTANCE, 'author_cooccurrences')
    G = nx.Graph()
    #for node in
    for (u, v), count in cooccurrences.iteritems():
        if u and v:
            G.add_edge(u, v, count=count)
    for node in G:
        G.node[node]['name'] = node[len(settings.INSTANCE):]
        try:
            author = Author.objects.get(instance_name=node)
            #print "%s: %d" % (author.name, author.changes_count)
            G.node[node]['changes'] = author.changes_count
            G.node[node]['annotations'] = author.annotations_count
            G.node[node]['activity'] = author.changes_count + author.annotations_count
        except Author.DoesNotExist:
            G.node[node]['changes'] = G.node[node]['annotations'] = G.node[node]['activity'] = 0
        print G.node[node]
    #del G['WHO']
    print "Save"
    PickledData.objects.set(settings.INSTANCE, 'author_graph', G)
    print "Positions"
    pos = nx.spring_layout(G, scale=2)
    pos = dict((node, (p[0] - 1, p[1] - 1)) for node, p in pos.iteritems())
    PickledData.objects.set(settings.INSTANCE, 'author_graph_positions', pos)
    
    if settings.IS_NCI:
        return
    
    print "Create directed graph"
    G = nx.DiGraph()
    overrides = PickledData.objects.get(settings.INSTANCE, 'author_overrides')
    for (u, v), count in overrides.iteritems():
        G.add_edge(u, v, count=count)
    """for node in G:
author = Author.objects.get(instance_name=node)
print "%s: %d" % (author.name, author.changes_count)
G.node[node]['name'] = author.name"""
    print "Save"
    PickledData.objects.set(settings.INSTANCE, 'author_graph_directed', G)
    
    #print "Export"
    #nx.write_graphml(G, '../output/social.graphml', prettyprint=True)
    #print "Plot"
    #nx.plot()
    print "Done"
        
def create_properties():
    from django.db import connection
    
    cursor = connection.cursor()
    
    print "Create properties"
    changes = cursor.execute("""select property, count(*) as c
from icd_change
where _instance=%s
group by property
order by c desc""", [settings.INSTANCE])
    for row in cursor.fetchall():
        name, count = row
        property, created = Property.objects.get_or_create(instance=settings.INSTANCE, name=name)
        property.count = count
        property.save()
    
    print "Done"
    
def print_sql_indexes():
    " Copy the printed results to icd/sql/categorymetrcs.sql and icd/sql/authorcategorymetrics.sql before running syncdb "
    
    features = [(name, description) for name, value, description in CategoryMetrics.objects.all()[0].get_metrics()]
    author_features = [(name, description) for name, value, description in AuthorCategoryMetrics.objects.all()[0].get_metrics()]
    print "/* generated by precalc.print_sql_indexes() */"
    print "ALTER TABLE icd_categorymetrics"
    """
# MySQL cannot handle more than 64 indexes
for feature, description in features:
print "ADD INDEX index_%(feature)s (instance, %(feature)s, category_id)," % {
'feature': feature,
}
"""
    indexes = []
    for layout_name, layout, dot_prog in settings.LAYOUTS:
        for feature, description in features:
            indexes.append("ADD INDEX index_pos_%(layout)s_%(feature)s (instance, x_%(layout)s, y_%(layout)s, %(feature)s, category_id)" % {
                'layout': layout,
                'feature': feature,
            })
    print ",\n".join(indexes) + ";"
    print ""
    print "/* generated by precalc.print_sql_indexes() */"
    print "ALTER TABLE icd_authorcategorymetrics"
    #for feature, description in features:
    # print "ADD INDEX index_%(feature)s (instance, %(feature)s, category_id)," % {
    # 'feature': feature,
    # }
    indexes = []
    for layout_name, layout, dot_prog in settings.LAYOUTS:
        for feature, description in author_features:
            indexes.append("ADD INDEX index_pos_%(layout)s_%(feature)s (instance, author_id, x_%(layout)s, y_%(layout)s, %(feature)s, category_id)" % {
                'layout': layout,
                'feature': feature,
            })
    print ",\n".join(indexes) + ";"
    print ""

def calc_author_metrics_split():
    #steps = [chr(n) for n in range(ord('A'), ord('Z'))]
    steps = ['A', 'G', 'M', 'R', 'Z']
    steps = [None] + steps + [None]
    for start, stop in zip(steps[:-1], steps[1:]):
        print "Split %s - %s" % (start, stop)
        calc_author_metrics(start, stop)
        print "Run gc"
        unreachable = gc.collect()
        print " %d unreachable objects" % unreachable
        
def calc_edit_distances():
    print "Calc edit distances"
    changes = Change.objects.filter(_instance=settings.INSTANCE).filter(Change.relevant_filter)
    #changes = changes.filter()
    #changes = changes.exclude(old_value="").exclude(new_value="")
    #changes = queryset_generator(changes)
    changes = queryset_generator(changes, reverse=True)
    #changes = changes[:100]
    for change in debug_iter(changes, n=100):
        old_value = change.old_value
        if old_value == '(empty)': old_value = ''
        new_value = change.new_value
        if new_value == '(empty)': new_value = ''
        #if old_value or new_value:
        changed = False
        if change.levenshtein_distance is None:
            change.levenshtein_distance = ld = levenshtein(old_value, new_value)
            if old_value == new_value == "":
                change.levenshtein_distance_norm = 0
                change.levenshtein_distance_rel = 0
            else:
                change.levenshtein_distance_norm = 2.0 * ld / (len(old_value) + len(new_value) + ld)
                change.levenshtein_distance_rel = 1.0 * change.levenshtein_distance / max(len(change.old_value),
                    len(change.new_value))
            change.levenshtein_similarity = 1.0 / (1 + ld)
            changed = True
        if change.lcs is None:
            change.lcs = longest_common_subsequence(old_value, new_value)
            change.lcs_rel = 1.0 * change.lcs / max(len(old_value), 1)
            changed = True
        if changed:
            change.save()
    print "Done"
    
def calc_extra_properties_data():
    print "Calc extra properties data"
    properties = Property.objects.filter(instance=settings.INSTANCE)
    for property in properties:
        print property
        changes = Change.objects.filter(_instance=settings.INSTANCE, property=property.name).filter(Change.relevant_filter)
        authors = {}
        for change in changes:
            authors[change.author_id] = authors.get(change.author_id, 0) + 1
        property.authors_count = len(authors)
        property.authors_gini = calculate_gini(authors)
        property.save()
    print "Done"
    
def calc_hierarchy():
    print "Calculate hierarchy"
    categories = Category.objects.filter(instance=settings.INSTANCE)
    categories = dict((category.name, category) for category in categories)
    G = PickledData.objects.get(settings.INSTANCE, 'graph')
    for category in debug_iter(categories.itervalues()):
        parents = set()
        get_indirect_parents(G, parents, category.name)
        level1 = []
        for parent in parents:
            if ROOT_CATEGORY in G.successors(parent):
                level1.append(categories[parent])
        if len(level1) > 1:
            level1_all = level1
            level1 = [parent for parent in level1
                if not parent.display.strip().strip("'").startswith(('Special', 'NCI_Administrative_', 'Retired_'))]
            if not level1 or len(level1) > 1:
                print "No unambigous level 1 parents for %s: %s -> %s" % (category, level1_all, level1)
        if level1:
            category.hierarchy = level1[0]
        else:
            category.hierarchy = None
        category.save()
    print "Done"
        
def preprocess_incremental():
    #calc_edit_distances()
    #calc_extra_properties_data()
    
    #computecalc_cooccurrences()
    #compute_author_reverts()
    #create_authors_network()
    
    #calc_hierarchy()
    
    #graphpositions()
    
    compute_extra_author_data()
    
def preprocess_nci():
    #find_annotation_components()
    """find_change_categories()
compute_extra_change_data()
create_authors()
#compute_follow_ups()
#load_extra_authors_data()
#create_properties()
createnetwork()
calc_metrics(compute_centrality=False)"""
    
    #calc_author_metrics_split()
    #calc_weights()
    #compact_weights()
    
    #graphpositions()
    #adjust_positions()
    #createquadtree()
    #store_positions()
    
    #compute_follow_ups()
    #compute_sessions()
    
    #compute_extra_author_data()
    #compute_author_reverts()
    
    calc_cooccurrences()
    create_authors_network()
    
    calc_hierarchy()
    
    #create_properties_network()

def preprocess():
    """find_annotation_components()
compute_extra_change_data()
create_authors()
if not settings.IS_WIKI:
compute_follow_ups() # too slow for wiki data
load_extra_authors_data()
create_properties()
createnetwork()"""
    
    calc_edit_distances()
    """
    if not settings.IS_WIKI:
        calc_metrics()
        calc_author_metrics_split()
        
        calc_weights()
        compact_weights()
        graphpositions()
        
        adjust_positions()
        createquadtree()
        store_positions()
        compute_sessions()
        compute_author_reverts()
        calc_cooccurrences()
        create_authors_network()
        create_properties_network()
        calc_hierarchy()
    """
    #print_sql_indexes()
    
    """
#calc_timespan_metrics()
#export_r_categories()
#export_r_timeseries()
#corr2latex()
#calc_cooccurrences()
#learn_changes()
#return
"""
def main():
    #preprocess_incremental()
    #preprocess_nci()
    preprocess()
    
    #foo = ['', 'http://who.int/icd#DS_Yellow', 'http://who.int/icd#DS_Blue', 'http://who.int/icd#DS_Red']
    #from random import choice
    
    #c = Category.objects.get(instance_name="mainhttp://who.int/icd#XIII")
    #categories = Category.objects.filter(instance="main")
    #for category in categories:
    # category.display_status = choice(foo)
    # category.hierarchy_id = c.instance_name
    # category.save()
    
    """argc = len(sys.argv)
if argc not in (2, 3):
print "Wrong usage. Please specify a function to call!"
return
command = sys.argv[1]
f = globals()[command]
if argc == 3:
f(sys.argv[2])
else:
f()"""

if __name__ == '__main__':
    main()