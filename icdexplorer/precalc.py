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

import random
import math
import pydot
import os
from collections import defaultdict
from django.db import connection
    
#from bulk_insertion import BulkInsertion
import csv
import gc
import numpy
import operator
from collections import defaultdict

#import scipy.stats

from django.db.models import Q, Min, Max, Count
from django.conf import settings
from settings_site import (INSTANCES)
from operator import itemgetter
import itertools

from icd.models import (Category, OntologyComponent, LinearizationSpec, AnnotatableThing,
    Change, Annotation, CategoryMetrics, User, Timespan, TimespanCategoryMetrics, Author,
    AuthorCategoryMetrics, AccumulatedCategoryMetrics, MultilanguageCategoryMetrics,
    Property, Group, Session, SessionChange, BasicOntologyStatistics, CategoriesTagRecommendations,
    UserTagRecommendations, UserDistanceRecommendations, UserUserTagRecommendations, UserCoBehaviourRecommendations)
from storage.models import PickledData
from quadtree import QuadTree
from icd.util import *
#from bulk_insertion import *

if settings.IS_NCI:
    ROOT_CATEGORY = 'http://www.w3.org/2002/07/owl#Thing'
elif settings.IS_ICTM:
    ROOT_CATEGORY = 'http://who.int/ictm#ICTMCategory'
elif settings.IS_WIKI:
    ROOT_CATEGORY = 'ICD-10'
else:
    ROOT_CATEGORY = 'http://who.int/icd#ICDCategory'
    
def node_name(category):
    if isinstance(category, basestring):
        return category.encode('utf-8')
    return category.name.encode('utf-8')

"""AUTHOR_SUBS = {
    'ttania': 'Tania Tudorache',
    'Molly Robinson': 'Molly Meri Robinson',
}"""
 
def createnetwork():
    print "Create network"
    G = nx.DiGraph()
    categories = Category.objects.filter(instance=settings.INSTANCE) #.select_related('change_component')
    print "%d categories" % len(categories)
    for index, category in enumerate(categories):
        if index % 1000 == 0:
            print "  %d: %s" % (index, category)
        G.add_node(node_name(category), display=category.display) #, weight=activity)
        parents = category.parents.values_list('name', flat=True)
        if not (parents or category.name == ROOT_CATEGORY):
            print category.name
        for parent_name in parents:
            G.add_edge(node_name(category), node_name(parent_name))
            
    print "Nodes: %d" % len(G)
    print "Edges: %d" % G.size()
            
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
    node_re = re.compile(r'(\S+?|"[^"]+?") \[pos="([0-9.e+-]+),([0-9.e+-]+)"')
    pos = {}
    for match in node_re.finditer(content):
        node, x, y = match.group(1), match.group(2), match.group(3)
        if node.startswith('"') and node.endswith('"'):
            node = node[1:-1]
        #print node
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
    #if not os.path.exists(graph_file):
    G = PickledData.objects.get(settings.INSTANCE, 'graph')
    print "Nodes: %d" % len(G)
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
        
        #if not os.path.exists(out_filename):
        result = call_dot(dot_prog, graph_file, ['-Groot=' + ROOT_CATEGORY],
            temp_output=out_filename)
    
        if not result:
            print "Graphviz layout with %s failed" % dot_prog
            return
            
        #else:
        #    with open(out_filename, 'r') as output:
        #        result = output.read()
        
        print "  Get positions"
        pos = get_dot_pos(result)
        print "  Got %d positions" % len(pos)
        
        print "  Save"
        PickledData.objects.set(settings.INSTANCE, 'graph_positions_original_%s' % key, pos)
        print "  Done"
        
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
    accumulated_category_metrics = list(AccumulatedCategoryMetrics.objects.filter(instance=settings.INSTANCE).order_by('category').select_related('category'))
    multilanguage_category_metrics = list(MultilanguageCategoryMetrics.objects.filter(instance=settings.INSTANCE).order_by('category').select_related('category'))
    author_category_metrics = list(AuthorCategoryMetrics.objects.filter(instance=settings.INSTANCE).order_by('category', 'author').select_related('category'))
    timespan_category_metrics = list(TimespanCategoryMetrics.objects.filter(instance=settings.INSTANCE).order_by('category').select_related('category'))
    
    pos = {}
    for layout, key, dot_prog in settings.LAYOUTS:
        print layout
        pos[key] = PickledData.objects.get(settings.INSTANCE, 'graph_positions_%s' % key)
        
    for name, items, key_func in [("Category", categories, lambda item: item.name),
        ("CategoryMetrics", category_metrics, lambda item: item.category.name),
        ("AuthorCategoryMetrics", author_category_metrics, lambda item: item.category.name),
        ("AccumulatedCategoryMetrics", accumulated_category_metrics, lambda item: item.category.name),
        ("MultilanguageCategoryMetrics", multilanguage_category_metrics, lambda item: item.category.name),
        ("TimespanCategoryMetrics", timespan_category_metrics, lambda item: item.category.name)]:
        print name
        for index, category in enumerate(items):
            if index % 1000 == 0:
                print "  %d: %s" % (index, category)
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
                print "  %d: %s" % (index, category)
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
        print author.name.encode("utf8")
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
        #if index < 101999:
        #    continue
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
        #    continue
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
        # There must be some memory leak in here, so we have to split up calls to calc_author_metrics
        # into several ranges of authors
        if from_name is not None and author.name < from_name:
            continue
        if to_name is not None and author.name >= to_name:
            continue
        #print author.name
        annotated_changes = all_categories.filter(chao__changes__author=author)
        if settings.IS_ICD:
            annotated_changes = annotated_changes.filter(chao__changes__action="Composite_Change")
        annotated_changes = annotated_changes.exclude(chao__changes__kind="Automatic").annotate(changes_count=Count('chao__changes'))
        print author.name.encode("utf8")
        """weights[author] = {}
        for weight_id, weight_name, weight_func in settings.WEIGHTS:
            print "  " + weight_name
            weights[author][weight_id] = [{}, {}] # single / accumulated
            weight = weights[author][weight_id]"""
        #filter_changes = {'chao__changes__author': author}
        annotated_changes = all_categories.filter(chao__changes__author=author, chao__changes__action="Composite_Change").exclude(chao__changes__kind="Automatic").annotate(changes_count=Count('chao__changes'))
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
            metrics.acc_changes = metrics.acc_annotations = metrics.acc_activity =  0
            metrics.authors = metrics.authors_changes = metrics.authors_annotations = 0
            
            if metrics.activity > 0:
                metrics.save()
                any_activity = True
            all_metrics[category.name] = metrics.get_metrics_dict()
        if any_activity:
            print "  Accumulate"
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
    for author in authors:
        print author.encode("utf-8")
        weights[author] = {}
        for weight_id, weight_name, weight_func in settings.WEIGHTS:
            print "  " + weight_name
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
        print author.encode("utf8")
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

def get_tag_changes(category, changes):
    primary = secondary = involved = who = outside = 0
    # prepare list of all tags assigned to category
    involved_tags = []
    involved_tags.extend(category.involved_tags.values_list('name', flat=True))
    # Note: Could just include Internal_Medicine Tag if any with TAG_IM is included!
    #       If Internal_Medicine is included, include all TAG_IM TAGs (?)
    #       Verify with Csongor/Tania/Natasha if that is reasonable!
    
    change_counter = len(changes)
    for change in changes:
        to_append = []
        groups = list(change.author.groups.values_list('name', flat=True))
        #Special case for Internal_Medicine :-/
        if len([x for x in groups if x.startswith("http://who.int/icd#TAG_IM_")]) > 0: 
            to_append.append("http://who.int/icd#TAG_Internal_Medicine")

        if len([x for x in groups if x.startswith("http://who.int/icd#TAG_Internal_Medicine")]) > 0:
            to_append.extend(Group.objects.filter(name__contains="http://who.int/icd#TAG_IM_").values_list("name", flat=True))

        groups.extend(to_append)
        if category.primary_tag in groups:
            primary += 1
        elif category.secondary_tag in groups:
            secondary += 1
        elif any(item in involved_tags for item in groups):
            involved += 1
        elif any(item.startswith("WHO") for item in groups):
            who += 1
        else:
            outside += 1
    return [primary, secondary, involved, who, outside]

def calc_metrics_counts_depth():
    # fast metrics calculation for Wikipedia, only calculating change counts and depth
    
    print "Load graph"
    G = PickledData.objects.get(settings.INSTANCE, 'graph')
    
    print "Load categories"
    categories = Category.objects.filter(instance=settings.INSTANCE).order_by('name') #.select_related('chao')
    categories = list(categories)
    
    for index, category in enumerate(categories):
        if index % 100 == 0:
            print "%d: %s" % (index, category)
        node = node_name(category)
        try:
            metrics = category.metrics
        except CategoryMetrics.DoesNotExist:
            metrics = CategoryMetrics(category=category)
        metrics.instance = settings.INSTANCE
        changes = 0
        for chao in category.chao.all():
            changes += chao.changes.filter(Change.relevant_filter).count()
        metrics.changes = changes
        metrics.annotations = 0
        try:
            if ROOT_CATEGORY in G:
                metrics.depth = nx.shortest_path_length(G, source=node, target=node_name(ROOT_CATEGORY))
            else:
                metrics.depth = 0
        except nx.exception.NetworkXError:
            metrics.depth = 0
        metrics.activity = changes
        metrics.authors = 0
        metrics.authors_changes = 0
        metrics.authors_annotations = 0
        metrics.parents = 0
        metrics.children = 0
        metrics.overrides = 0
        metrics.edit_sessions = 0
        metrics.authors_by_property = 0
        metrics.save()

def calc_metrics(accumulate_only=False, compute_centrality=False):
    #DISPLAY_STATUS_RE = re.compile(r'.*set to: (.*?)\(.*')
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
            #chao = category.chao
            #if chao is not None:
            #    changes = chao.changes.filter(Change.relevant_filter).order_by('timestamp')
            #    annotations = chao.annotations.filter(Annotation.relevant_filter)
            
            tag_changes = get_tag_changes(category, changes)
            metrics.primary_tag_changes = tag_changes[0]
            metrics.secondary_tag_changes = tag_changes[1]
            metrics.involved_tag_changes = tag_changes[2]
            metrics.who_tag_changes = tag_changes[3]
            metrics.outside_tag_changes = tag_changes[4]
            #metrics.save()
            
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
            
            """else:
                metrics.activity = metrics.changes = metrics.annotations = 0
                metrics.authors_changes = metrics.authors_annotations = metrics.authors = 0
                metrics.authors_gini = 0
                metrics.overrides = metrics.edit_sessions = metrics.authors_by_property = 0"""
            
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
    
    # TODO: Refactor - is ugly and slow
    #       Make one loop over all categories to store all metrics!
    print "Accumulate"
    
    for index, category in enumerate(categories):
        if index % 1000 == 0:
            print '%d: %s' % (index, category.name)
        try:
            accumulated_metrics = category.accumulated_metrics
        except AccumulatedCategoryMetrics.DoesNotExist:
            accumulated_metrics = AccumulatedCategoryMetrics(category=category)
        
        try:
            metrics = category.metrics
        except CategoryMetrics.DoesNotExist:
            metrics = CategoryMetrics(category=category)
            
        accumulated_metrics.instance = settings.INSTANCE
        metrics.instance = settings.INSTANCE
        calculate_accumulated(metrics, all_metrics, G)
        calculate_accumulated(accumulated_metrics, all_metrics, G)
        accumulated_metrics.save()
        metrics.save()
    print "Multilanguage"
    for index, category in enumerate(categories):
        if index % 1000 == 0:
            print "%d: %s" % (index, category.name)
        try:
            metrics = category.multilanguage_metrics
        except MultilanguageCategoryMetrics.DoesNotExist:
            metrics = MultilanguageCategoryMetrics(category=category)
        metrics.instance = settings.INSTANCE
        metrics.mlm_titles = category.category_titles.all().values('title').exclude(title='').distinct().count()
        metrics.mlm_title_languages = category.category_titles.all().values('language_code').distinct().exclude(language_code='').count()
        metrics.mlm_definitions = category.category_definitions.all().values('definition').distinct().exclude(definition='').count()
        metrics.mlm_definition_languages = category.category_definitions.all().values('language_code').distinct().exclude(language_code='').count()
        metrics.save()
    print "Done"

def calc_timespan_metrics():
    print "Calculate timespan metrics"
    MINMAX_CHANGES_DATE = Change.objects.filter(instance=settings.INSTANCE).aggregate(min=Min('timestamp'), max=Max('timestamp'))
    MIN_CHANGES_DATE = MINMAX_CHANGES_DATE['min'] #.date()
    MAX_CHANGES_DATE = MINMAX_CHANGES_DATE['max'] #.date() + timedelta(days=1)
    
    """
    split = datetime(2011, 04, 21)
    timespans = [
        Timespan.objects.get_or_create(instance=settings.INSTANCES[1], start=split,
            stop=datetime(2011, 07, 28))[0],   # gets rid of initial WHO changes
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
    """
    
    current_date = datetime.strptime(settings.INSTANCE, "icd%Y-%m-%d_%Hh%Mm") if settings.INSTANCE.startswith("icd") else datetime.strptime(settings.INSTANCE, "ictm%Y-%m-%d_%Hh%Mm") if settings.INSTANCE.startswith("ictm") else datetime.datetime.now()
    #print current_date
    #print MIN_CHANGES_DATE
    #td = current_date - MIN_CHANGES_DATE
    #days = float(td.days) + float(td.seconds)/60.0/60.0/24.0
    #print days
    
    print "Load categories"
    categories = Category.objects.filter(instance=settings.INSTANCE).order_by('name').select_related('chao')
    categories = list(categories)
    CATEGORIES = dict((category.name, category) for category in categories)
    print "Load graph"
    G = PickledData.objects.get(settings.INSTANCE, 'graph')
    print "Graph loaded"
    
    for index, category in enumerate(categories):
        if index % 1000 == 0:
            print '%d: %s' % (index, category.name)
        try:
            metrics = category.timespan_metrics
        except TimespanCategoryMetrics.DoesNotExist:
            metrics = TimespanCategoryMetrics(category=category, instance=settings.INSTANCE)

        chaos = category.chao.all()
        for chao in chaos:
            if chao is not None:
                changes = chao.changes.filter(Change.relevant_filter)
                annotations = chao.annotations.filter(Annotation.relevant_filter, created__isnull=False)
                changes, annotations = list(changes), list(annotations)
                
                # TODO: Other than days_after_last_change and days_after_last_annotation none work correctly!!!x
                metrics.days_after_last_change = min_null((days(current_date - change.timestamp) for change in changes))
                metrics.days_after_last_annotation = min_null((days(current_date - annotation.created) for annotation in annotations))
                metrics.days_after_last_activity = min(metrics.days_after_last_change, metrics.days_after_last_annotation)
                #metrics.days_before_first_change = min_null((days(change.timestamp - current_date) for change in changes))
                #metrics.days_after_median_change = median(days(current_date - change.timestamp) for change in changes)
                #try:
                #    metrics.days_after_last_annotation = min_null((days(current_date - annotation.created) for annotation in annotations))
                #    metrics.days_before_first_annotation = min_null((days(annotation.created - current_date) for annotation in annotations))
                #    metrics.days_after_median_annotation = median(days(current_date - annotation.created) for annotation in annotations)
                #except TypeError as e:
                #    print e
                #parents = [CATEGORIES[succ] for succ in G.successors(category.name)]
                #children = [CATEGORIES[pred] for pred in G.predecessors(category.name)]
                #metrics.changes_parents = sum(parent.chao.all().changes.filter(timestamp__range=(timespan.start, timespan.stop)).count()
                #    if parent.chao else 0 for parent in parents)
                #metrics.annotations_parents = sum(parent.chao.all().annotations.filter(created__range=(timespan.start, timespan.stop)).count()
                #    if parent.chao else 0 for parent in parents)
                #metrics.changes_children = sum(child.chao.all().changes.filter(timestamp__range=(timespan.start, timespan.stop)).count()
                #    if child.chao else 0 for child in children)
                #metrics.annotations_children = sum(child.chao.all().annotations.filter(created__range=(timespan.start, timespan.stop)).count()
                #    if child.chao else 0 for child in children)
            else:
                metrics.changes = metrics.annotations = 0
                #metrics.authors_changes = metrics.authors_annotations = metrics.authors = 0
                #metrics.authors_gini = 0
                #metrics.changes_parents = 0
                #metrics.annotations_parents = 0
                #metrics.changes_children = 0
                #metrics.annotations_children = 0
            metrics.save()


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
        #if layout == "Radial":
        #    continue
        print layout
        positions = PickledData.objects.get(settings.INSTANCE, 'graph_positions_%s' % dot_prog)
        for author in sorted(weights.keys()):
            #if author < "icd2011-08-30_04h02mSam Notzon":
            #    continue
            print "Build tree for '%s'" % author.encode("utf8")
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
                        #    print name
                        if weight > 0:
                            qt[(weight_id, accumulate)].insert(x, y, name, (-depth, weight))
                
            print "Save"
            #with open(settings.DATA_DIR + 'hashtags_positions_tree', 'wb') as data_file:
            #    pickle.dump(qt, data_file, protocol=pickle.HIGHEST_PROTOCOL)
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
            continue    # skip header line
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
    print "Get relevant authors"
    relevant_authors = Author.objects.filter(instance=settings.INSTANCE)
    if settings.IS_WIKI:
        relevant_authors = relevant_authors.filter(changes_count__gt=300)
    relevant_authors = relevant_authors.values_list('instance_name', flat=True)
    relevant_authors = set(relevant_authors)
    print relevant_authors
    
    print "Calculate co-occurrences"
    result = {}
    categories = Category.objects.filter(instance=settings.INSTANCE).order_by('name').select_related('chao')
    
    IP_RE = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
    
    if True:
        changes_by_category = PickledData.objects.get(settings.INSTANCE, 'author_changes_by_category')
    else:
        print "Changes"
        changes = Change.objects.filter(_instance=settings.INSTANCE).filter(Change.relevant_filter).select_related('apply_to')
        changes = changes.defer('old_value', 'new_value')
        changes = queryset_generator(changes)
        changes_by_category = defaultdict(set)
        for change in debug_iter(changes):
            #changes = dict((change.apply_to.category_id, change) for change in changes)
            author_name = change.author_id[len(settings.INSTANCE):]
            #print author_name
            if change.apply_to is not None and IP_RE.match(change.author_id) is None:
                #print "Add"
                changes_by_category[change.apply_to.category_id].add(change.author_id)
        del changes
            
        print "Save authors"
        PickledData.objects.set(settings.INSTANCE, 'author_changes_by_category', changes_by_category)
    
    print "Annotations"
    annotations = Annotation.objects.filter(instance=settings.INSTANCE).select_related('component')
    annotations_by_category = defaultdict(set)
    for annotation in debug_iter(annotations):
        if annotation.component is not None:
            annotations_by_category[annotation.component.category_id].add(annotation.author_id)
    del annotations
    
    print "Categories"
    for index, category in enumerate(categories):
        if index % 100 == 0:
            print (index, category)
        """authors = set()
        for change in changes_by_category.get(category.pk, []):
            authors.add(change)
        for annotation in annotations_by_category.get(category.pk, []):
            authors.add(annotation)"""
        authors = changes_by_category.get(category.pk, [])
        #print authors
        authors = [author for author in authors if author in relevant_authors]
        #print authors
        for author in authors:
            for other in authors:
                if author != other:
                    result[(author, other)] = result.get((author, other), 0) + 1
    #print "Result:"
    #print result
            
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
    print "Nodes: %d" % len(G)
    print "Edges: %d" % G.size()
    print "Save"
    PickledData.objects.set(settings.INSTANCE, 'author_graph', G)
    print "Positions"
    pos = nx.spring_layout(G, scale=2)
    pos = dict((node, (p[0] - 1, p[1] - 1)) for node, p in pos.iteritems())
    PickledData.objects.set(settings.INSTANCE, 'author_graph_positions', pos)
    
    if settings.IS_NCI or settings.IS_WIKI:
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

# TODO: Refactor - is ugly and slow
def print_sql_indexes():
    " Copy the printed results to icd/sql/categorymetrcs.sql and icd/sql/authorcategorymetrics.sql before running syncdb "
    
    features = [(name, description) for name, value, description in CategoryMetrics.objects.all()[0].get_metrics()]
    multilanguage_features = [(name, description) for name, value, description in MultilanguageCategoryMetrics.objects.all()[0].get_metrics()]
    accumulated_features = [(name, description) for name, value, description in AccumulatedCategoryMetrics.objects.all()[0].get_metrics()]
    author_features = [(name, description) for name, value, description in AuthorCategoryMetrics.objects.all()[0].get_metrics()]
    timespan_features = [(name, description) for name, value, description in TimespanCategoryMetrics.objects.all()[0].get_metrics()]

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
    print "ALTER TABLE icd_accumulatedcategorymetrics"
    indexes = []
    for layout_name, layout, dot_prog in settings.LAYOUTS:
        for feature, description in accumulated_features:
            indexes.append("ADD INDEX index_pos_%(layout)s_%(feature)s (instance, x_%(layout)s, y_%(layout)s, %(feature)s, category_id)" % {
                'layout': layout,
                'feature': feature,
            })
    print ",\n".join(indexes) + ";"
    print ""
    
    print "/* generated by precalc.print_sql_indexes() */"
    print "ALTER TABLE icd_multilanguagecategorymetrics"
    indexes = []
    for layout_name, layout, dot_prog in settings.LAYOUTS:
        for feature, description in multilanguage_features:
            indexes.append("ADD INDEX index_pos_%(layout)s_%(feature)s (instance, x_%(layout)s, y_%(layout)s, %(feature)s, category_id)" % {
                'layout': layout,
                'feature': feature,
            })
    print ",\n".join(indexes) + ";"
    print ""
    
    
    print "/* generated by precalc.print_sql_indexes() */"
    print "ALTER TABLE icd_authorcategorymetrics"
    #for feature, description in features:
    #    print "ADD INDEX index_%(feature)s (instance, %(feature)s, category_id)," % {
    #        'feature': feature,
    #    }
    indexes = []
    for layout_name, layout, dot_prog in settings.LAYOUTS:
        for feature, description in author_features:
            indexes.append("ADD INDEX index_pos_%(layout)s_%(feature)s (instance, author_id, x_%(layout)s, y_%(layout)s, %(feature)s, category_id)" % {
                'layout': layout,
                'feature': feature,
            })
    print ",\n".join(indexes) + ";"
    print ""
    
    print "/* generated by precalc.print_sql_indexes() */"
    print "ALTER TABLE icd_timespancategorymetrics"
    
    # MySQL cannot handle more than 64 indexes
    for feature, description in timespan_features:
        print "ADD INDEX index_%(feature)s (instance, %(feature)s, category_id)," % {
            'feature': feature,
        }
    
    indexes = []
    for layout_name, layout, dot_prog in settings.LAYOUTS:
        for feature, description in timespan_features:
            indexes.append("ADD INDEX index_pos_%(layout)s_%(feature)s (instance, x_%(layout)s, y_%(layout)s, %(feature)s, category_id)" % {
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
    
def compute_language_metrics():
    categories = Category.objects.filter(instance=settings.INSTANCE).order_by('name') #.select_related('chao')
    for index, category in enumerate(categories):
        if index % 1000 == 0:
            print "%d: %s" % (index, category.name)
        try:
            metrics = category.mutlilanguage_metrics
        except MultilanguageCategoryMetrics.DoesNotExist:
            metrics = MultilanguageCategoryMetrics(category=category)
        
        metrics.titles = category.category_titles.all().values('title').exclude(title='').distinct().count()
        metrics.title_languages = category.category_titles.all().values('language_code').distinct().exclude(language_code='').count()
        metrics.definitions = category.category_definitions.all().values('definition').distinct().exclude(definition='').count()
        metrics.definition_languages = category.category_definitions.all().values('language_code').distinct().exclude(language_code='').count()
        #if metrics.titles != metrics.title_languages or metrics.definitions != metrics.definition_languages:
        #    print category.name
        metrics.save()

def propagate_branch_info():
    G = PickledData.objects.get(settings.INSTANCE, 'graph')
    #graph_branches = G.predecessors('http://who.int/icd#ICDCategory')
    category_branches = []
    tmp_categories = Category.objects.filter(instance=settings.INSTANCE)
    categories = {}
    for cat in tmp_categories:
        categories[cat.name] = cat
    category_branches = Category.objects.filter(metrics__depth=1, instance=settings.INSTANCE)
    for idx, branch in enumerate(category_branches):
        print "[{0}/{1}]Propagating Branch {2}".format(idx+1, len(category_branches), branch.name)
        if branch.name == "http://who.int/icd#ICDCategory":
            continue
        predecessors = G.predecessors(branch.name)
        for node in predecessors:
            recursive_propagation(branch, node, G, categories)

def recursive_propagation(branch, node, G, categories):
    categories[node].branches.add(branch)
    predecessors = G.predecessors(node)
    for idx3, predecessor in enumerate(predecessors):
        recursive_propagation(branch, predecessor, G, categories)
    categories[node].save()

def tag_activity_per_category(color):
    #TODO: Refactor to make code more readable :)
    print "Calculating TAG Activity per category"
    if color == "all":
        categories = Category.objects.select_related("3").filter(instance=settings.INSTANCE)
    else:
        categories = Category.objects.select_related("3").filter(instance=settings.INSTANCE, display_status=color)
    result = [0,0,0,0,0,0]
    for idx, category in enumerate(categories):
        if idx % 1000 == 0:
            print "%d/%d: %s" % (idx+1, len(categories), category.name)
        for chao in category.chao.all():
            for change in chao.changes.all().filter(instance=settings.INSTANCE, type="Composite_Change", composite=settings.INSTANCE):
                try:
                    author = change.author
                except Author.DoesNotExist:
                    continue
                if len(author.groups.filter(name__contains="WHO")):
                    result[5] += 1
                    result[3] += 1
                    continue
                for group in author.groups.all():
                    if not group.name.startswith("http://"):
                        continue
                    result[5] += 1
                    tag = group.name
                    if tag == "http://who.int/icd#TAG_Internal_Medicine":
                        tag = "http://who.int/icd#TAG_IM"
                    if category.primary_tag.startswith(tag):
                        result[0] += 1
                    elif category.secondary_tag.startswith(tag):
                        result[1] += 1
                    else:
                        category_tags = category.involved_tags.all()
                        involved_tag_change_loop = 0
                        for category_tag in category_tags:
                            if category_tag.name.startswith(tag):
                                involved_tag_change_loop += 1
                                break
                        result[2] += involved_tag_change_loop
                        if involved_tag_change_loop == 0:
                            result[4] += 1
    return result

def basic_stats():
    
    print "Basic Ontology Stats"
    bos = BasicOntologyStatistics(instance=settings.INSTANCE)
    
    bos.author_count = Author.objects.filter(instance=settings.INSTANCE).count()
    bos.tag_count = Group.objects.filter(instance=settings.INSTANCE, name__contains="http://who.int/icd#").count()
    bos.change_count = Change.objects.filter(instance=settings.INSTANCE).count()
    bos.annotation_count = Annotation.objects.filter(instance=settings.INSTANCE).count()
    bos.category_count = Category.objects.filter(instance=settings.INSTANCE).count()
    bos.average_changes_per_category = bos.change_count / bos.category_count
    bos.average_annotations_per_category = bos.annotation_count / bos.category_count
    print "Basic Category Stats"
    bos.zero_change_categories_count = Category.objects.filter(instance=settings.INSTANCE, chao__changes__isnull=True).count()
    bos.avrg_change_categories_count = Category.objects.filter(instance=settings.INSTANCE, chao__changes__lte=bos.average_changes_per_category, chao__changes__gte=1).count()
    bos.gta_change_categories_count = Category.objects.filter(instance=settings.INSTANCE, chao__changes__gte=bos.average_changes_per_category).count()
    bos.zero_annotation_categories_count = Category.objects.filter(instance=settings.INSTANCE, chao__annotations__isnull=True).count()
    bos.avrg_annotation_categories_count = Category.objects.filter(instance=settings.INSTANCE, chao__annotations__lte=bos.average_annotations_per_category, chao__annotations__gte=1).count()
    bos.gta_annotation_categories_count = Category.objects.filter(instance=settings.INSTANCE, chao__annotations__gte=bos.average_annotations_per_category).count()
    #bos.average_changes_per_category = (bos.category_count - bos.zero_change_categories_count) / bos.change_count
    #bos.average_annotations_per_category = (bos.category_count - bos.zero_annotation_categories_count) / bos.annotation_count
    print "Colored Concept Stats"
    bos.blue_category_count = Category.objects.filter(instance=settings.INSTANCE, display_status="http://who.int/icd#DS_Blue").count()
    bos.yellow_category_count = Category.objects.filter(instance=settings.INSTANCE, display_status="http://who.int/icd#DS_Yellow").count()
    bos.red_category_count = Category.objects.filter(instance=settings.INSTANCE, display_status="http://who.int/icd#DS_Red").count()
    bos.grey_category_count = Category.objects.filter(instance=settings.INSTANCE, display_status="").count()
    bos.blue_changes = Change.objects.filter(instance=settings.INSTANCE, apply_to__category__display_status="http://who.int/icd#DS_Blue").count()
    bos.yellow_changes = Change.objects.filter(instance=settings.INSTANCE, apply_to__category__display_status="http://who.int/icd#DS_Yellow").count()
    bos.red_changes = Change.objects.filter(instance=settings.INSTANCE, apply_to__category__display_status="http://who.int/icd#DS_Red").count()
    bos.grey_changes = Change.objects.filter(instance=settings.INSTANCE, apply_to__category__display_status="").count()
    
    print "TAG Activity per Category"
    colors = [["_blue", "http://who.int/icd#DS_Blue"], ["_yellow", "http://who.int/icd#DS_Yellow"], ["_red", "http://who.int/icd#DS_Red"], ["", "all"], ["_grey", ""]]
    
    for color in colors:
        print color[1]
        result = tag_activity_per_category(color[1])
        setattr(bos, "primary_activity_per%s_category" % (color[0]), "%.2f" % (result[0]/result[5]*100))
        setattr(bos, "secondary_activity_per%s_category" % (color[0]), "%.2f" % (result[1]/result[5]*100))
        setattr(bos, "involved_activity_per%s_category" % (color[0]), "%.2f" % (result[2]/result[5]*100))
        setattr(bos, "who_activity_per%s_category" % (color[0]), "%.2f" % (result[3]/result[5]*100))
        setattr(bos, "outside_activity_per%s_category" % (color[0]), "%.2f" % (result[4]/result[5]*100))
    
    G = PickledData.objects.get(settings.INSTANCE, 'graph')
    tbd_categories = Category.objects.filter(instance=settings.INSTANCE, display__icontains="Deleted")
    tbd_children = []
    for tbd_category in tbd_categories:
        try:
            tbd_children.extend(G.predecessors(tbd_category.name))
        except nx.exception.NetworkXError:
            continue
    bos.tbd_concepts = len(set(tbd_children))
    dtbm_categories = Category.objects.filter(instance=settings.INSTANCE, display__icontains="Needing a decision to be made")
    dtbm_children = []
    for dtbm_category in dtbm_categories:
        try:
            dtbm_children.extend(G.predecessors(dtbm_category.name))
        except nx.exception.NetworkXError:
            continue
    bos.dtbm_concepts = len(set(dtbm_children))
    tbr_categories = Category.objects.filter(instance=settings.INSTANCE, display__icontains="To be retired")
    tbr_children = []
    for tbr_category in tbr_categories:
        try:
            tbr_children.extend(G.predecessors(tbr_category.name))
        except nx.exception.NetworkXError:
            continue
    bos.tbr_concepts = len(set(tbr_children))
    bos.save()
    print "Done"
    
def compute_extra_group_data():
    # Computes additional group data, needed for TAG Views
    groups = Group.objects.filter(instance=settings.INSTANCE)
    for group in groups:
        print group.name
        primary_categories = list(Category.objects.filter(instance=settings.INSTANCE, primary_tag=group.name))
        all_categories = list(Category.objects.filter(Q(instance=settings.INSTANCE), 
                (Q(primary_tag=group.name) | Q(secondary_tag=group.name) | Q(involved_tags__name = group.name))))
        group.category_count = len(all_categories)
        group.blue_categories = group.yellow_categories = group.red_categories = group.grey_categories = 0
        group.changes_in_primary = group.changes_in_secondary = group.changes_in_involved = 0
        changes = []
        for category in all_categories:
            if category.display_status == "http://who.int/icd#DS_Blue":
                group.blue_categories += 1
            elif category.display_status == "http://who.int/icd#DS_Yellow":
                group.yellow_categories += 1
            elif category.display_status == "http://who.int/icd#DS_Red":
                group.red_categories += 1
            else:
                group.grey_categories += 1
            #involved_taglist = category.involved_tags.values_list('name', flat=True)
            for chao in category.chao.all():
                for change in chao.changes.all():
                    changes.append(change)
                    if category.primary_tag == group.name:
                        group.changes_in_primary += 1
                    elif category.secondary_tag == group.name:
                        group.changes_in_secondary += 1
                    else:
                        group.changes_in_involved += 1
        group.change_count = len(set(changes))
        change_count = 1 if group.change_count < 1 else group.change_count
        group.progress = group.blue_categories/group.category_count if group.category_count > 0 else 0
        group.activity_in_primary = group.changes_in_primary/change_count
        group.activity_in_secondary = group.changes_in_secondary/change_count
        group.activity_in_involved = group.changes_in_involved/change_count
        group.save()
    print "Done"

def compute_session_data():
    # Generates basic Session Containers with start-, endtime and change count
    authors = Author.objects.filter(instance=settings.INSTANCE).order_by('name')
    for author in authors:
        #if author.name < "Linda Best":
        #    continue
        changes = author.changes.filter(apply_to__category__name__isnull=False).order_by("timestamp")
        print "%s: (%d)" % (author.name.encode("utf8"), len(changes))
        sessions = []
        current_session = []
        # Preparing change sessions
        for idx, change in enumerate(changes):
            current_session.append(change)
            if idx+1 >= len(changes):
                sessions.append(current_session)
                # end of list
                continue
            current_timestamp = change.timestamp
            next_timestamp = changes[idx+1].timestamp
            time_diff = next_timestamp - current_timestamp
            diff = time_diff.days*24*60+time_diff.seconds/60
            if diff > 30:
                sessions.append(current_session)
                current_session = []
        # Have to access every single change, takes time to store!
        # Not that much faster with manual query (stil has to update every single change)
        for idx, change_list in enumerate(sessions):
            print "    Session %d of %d (%d)" % (idx+1, len(sessions), len(change_list))
            session = Session(instance=settings.INSTANCE, author=author, change_count = len(change_list), annotation_count = 0, start_date=change_list[0].timestamp, end_date=change_list[-1].timestamp)
            session.save()
            sc = SessionChange(instance=settings.INSTANCE, name=session.id, session=session)
            sc.save()
            for change in change_list:
                change.session_component = sc
                change.save()
        sessions = None
    print "Done"

def compute_session_extra_data():
    G = PickledData.objects.get(settings.INSTANCE, 'graph')
    G = G.to_undirected()
    sessions = Session.objects.filter(instance=settings.INSTANCE)
    print "Total Sessions: "+str(len(sessions))
    for i, session in enumerate(sessions):
        print "[{1}/{2}]{0}".format(session.author.name, i+1, len(sessions))
        td = session.end_date - session.start_date
        session.duration = float(td.days*24*60+td.seconds/60)
        session.total_distance = 0
        session.total_depth = 0
        session_changes = session.session_component.changes.all().order_by('timestamp')
        branches = []
        if len(session_changes) == 1:
            session.total_depth = session_changes[0].apply_to.category.metrics.depth
            session.branches = float(len(session_changes[0].apply_to.category.branches.all()))
            session.save()
            continue
        for idx, change in enumerate(session_changes):
            if idx + 1 < len(session_changes):
                #Distance
                session.total_distance += nx.shortest_path_length(G, source=change.apply_to.category.name, target=session_changes[idx+1].apply_to.category.name)
            name = change.apply_to.category.name
            session.total_depth += change.apply_to.category.metrics.depth
            branches += change.apply_to.category.branches.all()
            session.branches = float(len(set(branches)))
        session.save()
    
def prepare_category_recommendation_dicts(all_categories):
    category_tags = {}
    tags = defaultdict(set)
    for i, category in enumerate(all_categories):
        category_tags[category] = category.get_tags()
        for c_tag in category_tags[category]:
            tags[c_tag].add(category)
    return tags, category_tags
    
def prepare_author_recommendation_dicts(authors, category_tags, all_category_names):
    author_tag_count = {}
    author_category_score = {}
    primary = set(Category.objects.exclude(primary_tag = '').values_list("primary_tag", flat=True).distinct())
    secondary = set(Category.objects.exclude(secondary_tag = '').values_list("secondary_tag", flat=True).distinct())
    involved = set(Category.objects.values_list("involved_tags__name", flat=True).distinct())
    groups = set(Group.objects.values_list("name", flat=True))
    groups = primary.union(secondary,involved,groups)
    
    for j, author in enumerate(authors):
        category_scores = dict((x, 0) for x in all_category_names)
        tag_count = dict((x, 0) for x in groups)
        categories = author.change_categories.all()
        for k, category in enumerate(categories):
            c_tags = category_tags[category]
            for tag_to_count in c_tags:
                tag_count[tag_to_count] += 1
            category_scores[category.name] += 1
        author_tag_count[author] = tag_count
        author_category_score[author] = category_scores
    return author_tag_count, author_category_score
    
def calculate_user_recommendations(calculate_text_similarity=True, calculate_explicit_links=True, calculate_co_author_behaviour=True):
    print "Calculating TAG Recommendations"
    authors = Author.objects.filter(instance=settings.INSTANCE).order_by("name")
    groups = Group.objects.filter(instance=settings.INSTANCE, name__contains="http://")
    all_categories = Category.objects.filter(instance=settings.INSTANCE)
    author_tags = {}
    print "Preparing category <-> tags & tag <-> categories dictionaries"
    tags, category_tags = prepare_category_recommendation_dicts(all_categories)
    print "Preparing author <-> tags & author <-> category scores"
    author_tag_count, author_category_score = prepare_author_recommendation_dicts(authors, category_tags, all_categories.values_list("name", flat="True"))
    for i, author in enumerate(authors):
        print "Calculating recommendations for %s" % (author.name.encode("utf8"))
        # TODO: See if prestored might boost performance! Problem with category_scores! 
        #       Need category.name for NetworkX
        categories = author.change_categories.all()
        #print "Calculating and storing TAG similarity"
        author_taglist = set([x for x,y in author_tag_count[author].iteritems() if y > 0 and x.startswith("http:")])
        
        # NOTE: concentrate on 7 most used TAGs -> helps improve performance...?
        categories_set = set(all_categories)-set(categories)
        most_overlap = set()
        range_limit = 7 if len(author_taglist) > 7 else len(author_taglist)
        
        #print "TextSimilarity Engine"
        # SuggestBot Engine 1
        if calculate_text_similarity:
            for k in reversed(range(1, range_limit+1)):
                #print k
                for other_tags in itertools.combinations(author_taglist, k):
                    #print other_tags
                    other_categories = reduce(operator.and_, (tags[tag] for tag in other_tags), categories_set)
                    for overlap_cat in other_categories:
                        similarity = float("%.2f" % (len(author_taglist.intersection(category_tags[overlap_cat]))/len(author_taglist.union(category_tags[overlap_cat]))))
                        most_overlap.add((overlap_cat, str(similarity)))
            most_overlap = sorted(most_overlap, key=itemgetter(1), reverse=True)
            for list in most_overlap[:100]:
                recommendation = UserTagRecommendations(instance=settings.INSTANCE, user=author, recommend=list[0], tag_similarity=list[1])
                recommendation.save()
        
        print "Link Engine"
        # SuggestBot Engine 2
        if calculate_explicit_links:
            # Try with "random similar concept"
            # G.reverse() => reverses the edges of the directed graph!
            # To prevent looping over already checked nodes
            already_checked_nodes = []
            G = PickledData.objects.get(settings.INSTANCE, 'graph')
            max_distance = 5
            user_scores = {}
            bl = set([x for x,y in author_category_score[author].iteritems() if y > 0])
            for category in bl:
                distance = 0
                while distance < max_distance:
                    if category not in already_checked_nodes:
                        neighbors = G.neighbors(category)
                        for node in neighbors:
                            if node in user_scores:
                                user_scores[node] += 1
                            else:
                                user_scores[node] = 1
                        already_checked_nodes.append(category)
                    distance += 1
            sorted_explicit_scores = sorted(user_scores.iteritems(), key=lambda (k,v):(v,k), reverse=True)#[:30]
            for k in sorted_explicit_scores:
                cdr = UserDistanceRecommendations(instance=settings.INSTANCE, user=author, recommend_id=settings.INSTANCE+k[0], explicit_link_score=k[1])
                cdr.save()
        print "Co-Author behaviour"
        if calculate_co_author_behaviour:
            user_similarity = {}
            user_similarity[author] = []
            tag_counter = [x for k,x in author_tag_count[author].iteritems()]
            for ca_index, ca_author in enumerate(authors):
                user_similarity[author].append([ca_author, scipy.stats.pearsonr(tag_counter, [x for k,x in author_tag_count[ca_author].iteritems()])])
                ts = 0 if math.isnan(user_similarity[author][ca_index][1][0]) else user_similarity[author][ca_index][1][0]
                uutr = UserUserTagRecommendations(instance=settings.INSTANCE, recommend=ca_author, user=author, tag_similarity=ts)
                uutr.save()
            # recommend concepts C to u where C have been edited by highest 
            #Get 5 most similar users that are not author itself
            recommender_counter = 0
            for s_author in author.author_recommendations.all().order_by("-tag_similarity"):
                if s_author.tag_similarity > 0:
                    for coedit_category in s_author.recommend.change_categories.all():
                        if coedit_category not in categories and recommender_counter < 100:
                            ucb = UserCoBehaviourRecommendations(instance=settings.INSTANCE, user=author, recommend=coedit_category, tag_similarity = s_author.tag_similarity)
                            ucb.save()
                            recommender_counter += 1
                if recommender_counter >= 100:
                    break
    print "Done"
    
def calculate_category_recommendations():
    print "Calculating TAG Recommendations"
    categories = Category.objects.filter(instance=settings.INSTANCE)
    groups = Group.objects.filter(instance=settings.INSTANCE)
    category_tags = {}
    tags = defaultdict(set)
    number_of_recommendations = 10
    tags, category_tags = prepare_category_recommendation_dicts(categories)
    cats_set = set(category_tags)
    for index, (cat, cat_tags) in enumerate(category_tags.iteritems()):
        if index % 1000 == 0:
            print "%d: %s" % (index, cat.name)
        most_overlap = []
        for k in reversed(range(1, len(cat_tags)+1)):
            if len(most_overlap) >= number_of_recommendations:
                break
            for other_tags in itertools.combinations(cat_tags, k):
                if len(most_overlap) >= number_of_recommendations:
                    break
                other_cats = reduce(operator.and_, (tags[tag] for tag in other_tags), cats_set)
                for overlap_cat in other_cats:
                    if overlap_cat == cat:
                        continue
                    most_overlap.append([overlap_cat, "%.2f" % (len(cat_tags & category_tags[overlap_cat])/len(cat_tags)*100.00)])
                    if len(most_overlap) >= number_of_recommendations:
                        break
        most_overlap = sorted(most_overlap, key=itemgetter(1), reverse=True)
        for list in most_overlap:
            recommendation = CategoriesTagRecommendations(instance=settings.INSTANCE, category=cat, recommend=list[0], tag_similarity=list[1])
            recommendation.save()
    print "Done"
    
def adding_categories_to_authors():
    # Boost Query Performance, as it skips needed "changes__apply_to__..." conditions on query
    print "Adding Categories to Authors"
    authors = Author.objects.filter(instance=settings.INSTANCE)
    for author in authors:
        print author.name.encode("utf8")
        for category in Category.objects.filter(instance=settings.INSTANCE, chao__changes__author = author).distinct():
            author.change_categories.add(category)
        for category in Category.objects.filter(instance=settings.INSTANCE, chao__annotations__author = author).distinct():
            author.change_categories.add(category)
    print "Done"
    
def preprocess_incremental():
    #calc_edit_distances()
    #calc_extra_properties_data()
    #computecalc_cooccurrences()
    #compute_author_reverts()
    #create_authors_network()
    #calc_hierarchy()
    #graphpositions()
    #compute_extra_author_data()
    
    # for Wikipedia:
    createnetwork()
    calc_metrics_counts_depth()
    graphpositions()
    adjust_positions()
    store_positions()
    #calc_cooccurrences()
    #create_authors_network()
    
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
    find_annotation_components()
    compute_extra_change_data()
    create_authors()
    if not settings.IS_WIKI:
        compute_follow_ups() # too slow for wiki data
    
    load_extra_authors_data()
    create_properties()
    createnetwork()
    
    calc_edit_distances()
    
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
    
    #print_sql_indexes()
    
    
    print settings.INSTANCE
    #find_annotation_components()
    #compute_extra_change_data()
    #create_authors()
    #compute_follow_ups()
    #load_extra_authors_data()
    #create_properties()
    #createnetwork()
    calc_metrics()
    #calc_author_metrics_split()
    #compute_extra_author_data()
    #calc_weights()
    #compact_weights()
    #graphpositions()
    #adjust_positions()
    #createquadtree()
    #store_positions()
    #compute_sessions()
    #compute_author_reverts()
    #calc_cooccurrences()
    #create_authors_network()
    #create_properties_network()
    #calc_hierarchy()
    #print_sql_indexes()
    
    #TODO:  Add (and make work) commented stuff from Jan
    #       Add additional activity metrics for heatmap!
    #calc_timespan_metrics()
    
    #adding_categories_to_authors()
    #basic_stats()
    #compute_extra_group_data()
    #adding_authors_to_categories()
    #calculate_category_recommendations()
    #calculate_user_recommendations()
    
    # Not needed for iCAT-Analytics Views 
    # or other precalc methods
    # Session Calculations are SLOW and
    # were primarily used for failed clustering
    #propagate_branch_info()
    #compute_session_data()
    #compute_session_extra_data()
    
    
    """
    #export_r_categories()
    #export_r_timeseries()
    #corr2latex()
    #calc_cooccurrences()
    #learn_changes()
    #return
    """
def main():
    preprocess_incremental()
    #preprocess_nci()
    #preprocess()
    
    #foo = ['', 'http://who.int/icd#DS_Yellow', 'http://who.int/icd#DS_Blue', 'http://who.int/icd#DS_Red']
    #from random import choice
    
    #c = Category.objects.get(instance_name="mainhttp://who.int/icd#XIII")
    #categories = Category.objects.filter(instance="main")
    #for category in categories:
    #    category.display_status = choice(foo)
    #    category.hierarchy_id = c.instance_name
    #    category.save()
    

    print "done"

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
