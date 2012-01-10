"""
ICDexplorer
Django views.

(c) 2011 Jan Poeschko
jan@poeschko.com
"""

from __future__ import division

from django.shortcuts import render_to_response, redirect
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.http import Http404, HttpResponse
from django.template import RequestContext
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.db.models import Min, Max
from django.utils import simplejson
from inspect import getmembers

from models import Category, Change, Annotation, BasicOntologyStatistics, CATEGORY_NAME_PREFIX, DISPLAY_STATUS, CategoryMetrics, OntologyComponent, Author, AuthorCategoryMetrics, AccumulatedCategoryMetrics, MultilanguageCategoryMetrics, TimespanCategoryMetrics
from data import (#GRAPH, CATEGORIES, #GRAPH_POSITIONS, GRAPH_POSITIONS_TREE, WEIGHTS,
    MIN_CHANGES_DATE, MAX_CHANGES_DATE, CATEGORIES, FEATURES, AUTHOR_FEATURES,
    AUTHORS, GRAPH_AUTHORS, GRAPH_AUTHORS_DIRECTED, GRAPH_AUTHORS_POSITIONS,
    CHANGES_COUNT, ANNOTATIONS_COUNT, GROUPS,
    PROPERTIES, GRAPH_PROPERTIES_POSITIONS, ACCUMULATED_FEATURES, MULTILANGUAGE_FEATURES,
    FOLLOW_UPS, MULTILANGUAGE_FILTER, ACCUMULATED_FILTER, AUTHOR_FILTER, TIMESPAN_FILTER, CATEGORY_FEATURES, TIMESPAN_FEATURES, CATEGORYMETRICS_FILTER)
from util import get_week, week_to_date, get_weekly, counts, group, calculate_gini
from icdexplorer.storage.models import PickledData

"""def start(request):
    return render_to_response('start.html', {
        'instances': INSTANCES,
        'instance': '',
    }, context_instance=RequestContext(request))"""
    
def json_response(data):
    return HttpResponse(simplejson.dumps(data), mimetype='application/json')

@login_required
def network(request):
    return render_to_response('network.html', {
        'layouts': settings.LAYOUTS,
        'authors': [('(All)', '')] + [(author.name, author.to_slug()) for id, author in sorted(AUTHORS.iteritems())],
        'weights': [(name, id) for id, name, f in settings.WEIGHTS],
        'features': [(name, id) for id, name in FEATURES],
        'author_features': [(name, id) for id, name in AUTHOR_FEATURES],
    }, context_instance=RequestContext(request))

    
@login_required
def dashboard(request):

    bos = BasicOntologyStatistics.objects.get(instance=settings.INSTANCE)
    colors = {'blue':"#137FAE", 'yellow':"#FDC605", 'red':"#B20912", 'grey':"#999999"}
    colored_categories = [{'label': 'Blue Categories', 'data': bos.blue_category_count, 'color': colors['blue']}, 
                          {'label': 'Yellow Categories', 'data': bos.yellow_category_count, 'color': colors['yellow']}, 
                          {'label': 'Red Categories', 'data': bos.red_category_count, 'color': colors['red']}, 
                          {'label': 'Grey Categories', 'data': bos.grey_category_count, 'color': colors['grey']}]
    
    colored_category_changes = [{'label': 'Blue Category Changes', 'data': bos.blue_changes, 'color': colors['blue']}, 
                          {'label': 'Yellow Category Changes', 'data': bos.yellow_changes, 'color': colors['yellow']}, 
                          {'label': 'Red Category Changes', 'data': bos.red_changes, 'color': colors['red']}, 
                          {'label': 'Grey Category Changes', 'data': bos.grey_changes, 'color': colors['grey']}]

    colored_category_average_changes = [{'label': 'Blue Category Changes', 'data': bos.blue_changes/bos.blue_category_count, 'color': colors['blue']}, 
                          {'label': 'Yellow Category Changes', 'data': bos.yellow_changes/bos.yellow_category_count, 'color': colors['yellow']}, 
                          {'label': 'Red Category Changes', 'data': bos.red_changes/bos.red_category_count, 'color': colors['red']}, 
                          {'label': 'Grey Category Changes', 'data': bos.grey_changes/bos.grey_category_count, 'color': colors['grey']}]
    
    outside = 100.0-(bos.primary_activity_per_category + bos.secondary_activity_per_category + bos.involved_activity_per_category + bos.who_activity_per_category)
    all_category_tag_changes = [{'label': '% Primary TAG Changes', 'data': bos.primary_activity_per_category}, 
                          {'label': '% Secondary TAG Changes', 'data': bos.secondary_activity_per_category}, 
                          {'label': '% Involved TAG Changes', 'data': bos.involved_activity_per_category}, 
                          {'label': '% WHO Team TAG Changes', 'data': bos.who_activity_per_category},
                          {'label': '% Outside TAG Changes', 'data': outside}]

    outside = 100.0-(bos.primary_activity_per_blue_category + bos.secondary_activity_per_blue_category + bos.involved_activity_per_blue_category + bos.who_activity_per_blue_category)
    blue_category_tag_changes = [{'label': '% Primary TAG Changes', 'data': bos.primary_activity_per_blue_category}, 
                          {'label': '% Secondary TAG Changes', 'data': bos.secondary_activity_per_blue_category}, 
                          {'label': '% Involved TAG Changes', 'data': bos.involved_activity_per_blue_category}, 
                          {'label': '% WHO Team TAG Changes', 'data': bos.who_activity_per_blue_category},
                          {'label': '% Outside TAG Changes', 'data': outside}]
    
    outside = 100.0-(bos.primary_activity_per_yellow_category + bos.secondary_activity_per_yellow_category + bos.involved_activity_per_yellow_category + bos.who_activity_per_yellow_category)
    yellow_category_tag_changes = [{'label': '% Primary TAG Changes', 'data': bos.primary_activity_per_yellow_category}, 
                          {'label': '% Secondary TAG Changes', 'data': bos.secondary_activity_per_yellow_category}, 
                          {'label': '% Involved TAG Changes', 'data': bos.involved_activity_per_yellow_category}, 
                          {'label': '% WHO Team TAG Changes', 'data': bos.who_activity_per_yellow_category},
                          {'label': '% Outside TAG Changes', 'data': outside}]
    
    outside = 100.0-(bos.primary_activity_per_red_category + bos.secondary_activity_per_red_category + bos.involved_activity_per_red_category + bos.who_activity_per_red_category)
    red_category_tag_changes = [{'label': '% Primary TAG Changes', 'data': bos.primary_activity_per_red_category}, 
                          {'label': '% Secondary TAG Changes', 'data': bos.secondary_activity_per_red_category}, 
                          {'label': '% Involved TAG Changes', 'data': bos.involved_activity_per_red_category}, 
                          {'label': '% WHO Team TAG Changes', 'data': bos.who_activity_per_red_category},
                          {'label': '% Outside TAG Changes', 'data': outside}]
    
    outside = 100.0-(bos.primary_activity_per_grey_category + bos.secondary_activity_per_grey_category + bos.involved_activity_per_grey_category + bos.who_activity_per_grey_category)
    grey_category_tag_changes = [{'label': '% Primary TAG Changes', 'data': bos.primary_activity_per_grey_category}, 
                          {'label': '% Secondary TAG Changes', 'data': bos.secondary_activity_per_grey_category}, 
                          {'label': '% Involved TAG Changes', 'data': bos.involved_activity_per_grey_category}, 
                          {'label': '% WHO Team TAG Changes', 'data': bos.who_activity_per_grey_category},
                          {'label': '% Outside TAG Changes', 'data': outside}]
    
    return render_to_response('dashboard.html', {
        'basic_ontology_stats': bos,
        'colored_categories': colored_categories,
        'colored_category_changes': colored_category_changes,
        'colored_category_average_changes': colored_category_average_changes,
        'grey_category_tag_changes': grey_category_tag_changes,
        'all_category_tag_changes': all_category_tag_changes,
        'blue_category_tag_changes': blue_category_tag_changes,
        'yellow_category_tag_changes': yellow_category_tag_changes,
        'red_category_tag_changes': red_category_tag_changes,
    }, context_instance=RequestContext(request))

@login_required 
def search(request):
    query = request.GET.get('search', '')
    
    categories = Category.objects.filter(name__icontains=query) | Category.objects.filter(display__icontains=query)
    categories = categories.order_by('display')
    
    if len(categories) == 1:
        return redirect(categories[0].get_absolute_url())
    
    return render_to_response('search.html', {
        'search': query,
        'result': categories,
    }, context_instance=RequestContext(request))
    
def about(request):
    return render_to_response('about.html', {
        'instance': settings.INSTANCE,
    }, context_instance=RequestContext(request))
    
@login_required
def categories(request):
    features = []
    category_metrics = CategoryMetrics.objects.filter(instance=settings.INSTANCE)
    for name, description in CATEGORY_FEATURES:
        categories = [metrics.category for metrics in category_metrics.order_by('-' + name)[:10]]
        categories += reversed([metrics.category for metrics in category_metrics.filter(**{name + '__isnull': False}).order_by(name)[:3]])
        features.append((name, description, categories))
    
    accumulated_features = []
    category_metrics = AccumulatedCategoryMetrics.objects.filter(instance=settings.INSTANCE)
    for name, description in ACCUMULATED_FEATURES:
        print name
        categories = [metrics.category for metrics in category_metrics.order_by('-' + name)[:10]]
        categories += reversed([metrics.category for metrics in category_metrics.filter(**{name + '__isnull': False}).order_by(name)[:3]])
        accumulated_features.append((name, description, categories))
    
    multilanguage_features = []
    category_metrics = MultilanguageCategoryMetrics.objects.filter(instance=settings.INSTANCE)
    for name, description in MULTILANGUAGE_FEATURES:
        categories = [metrics.category for metrics in category_metrics.order_by('-' + name)[:10]]
        categories += reversed([metrics.category for metrics in category_metrics.filter(**{name + '__isnull': False}).order_by(name)[:3]])
        multilanguage_features.append((name, description, categories))
    
    timespan_features = []
    category_metrics = TimespanCategoryMetrics.objects.filter(instance=settings.INSTANCE)
    for name, description in TIMESPAN_FEATURES:
        categories = [metrics.category for metrics in category_metrics.order_by('-' + name)[:10]]
        categories += reversed([metrics.category for metrics in category_metrics.filter(**{name + '__isnull': False}).order_by(name)[:3]])
        timespan_features.append((name, description, categories))
    
    return render_to_response('categories.html', {
        'features': features,
        'accumulated_features': accumulated_features,
        'multilanguage_features': multilanguage_features,
        'timespan_features': timespan_features,
    }, context_instance=RequestContext(request))
    
@login_required
def categorylisting(request, attribute, page_index=1):

    if attribute in ACCUMULATED_FILTER:
        metric_table = "accumulated_metrics."
        categories = Category.objects.all().filter(instance=settings.INSTANCE).order_by("-accumulated_metrics__%s" % attribute)
        detail = AccumulatedCategoryMetrics._meta.get_field(attribute).help_text
    elif attribute in MULTILANGUAGE_FILTER:
        metric_table = "multilanguage_metrics."
        categories = Category.objects.all().filter(instance=settings.INSTANCE).order_by("-multilanguage_metrics__%s" % attribute)
        detail = MultilanguageCategoryMetrics._meta.get_field(attribute).help_text
    elif attribute in CATEGORYMETRICS_FILTER:
        categories = Category.objects.all().filter(instance=settings.INSTANCE).order_by("-metrics__%s" % attribute)
        metric_table = "metrics."
        detail = CategoryMetrics._meta.get_field(attribute).help_text
    elif attribute in TIMESPAN_FILTER:
        categories = Category.objects.all().filter(instance=settings.INSTANCE).order_by("-timespan_metrics__%s" % attribute)
        metric_table = "timespanmetrics."
        detail = TimespanCategoryMetrics._meta.get_field(attribute).help_text
    else:
        raise Http404

    paginator = Paginator(categories, 100, 5)
    try:
        page = paginator.page(page_index)
    except (EmptyPage, InvalidPage), e:
        page = paginator.page(paginator.num_pages)
    
    return render_to_response('listing.html', {
        'attribute': attribute,
        'objects': page.object_list,
        'page': page,
        'model': 'Category',
        'listing_type': 'category',
        'description': detail,
        'metric_table': metric_table,
    }, context_instance=RequestContext(request))

@login_required
def authorlisting(request, attribute, page_index=1):
    if not attribute in AUTHOR_FILTER:
        raise Http404

    authors = Author.objects.all().filter(instance=settings.INSTANCE).order_by("-%s" % attribute)
    detail = Author._meta.get_field(attribute).help_text
    metric_table = ""
    paginator = Paginator(authors, 100, 5)
    try:
        page = paginator.page(page_index)
    except (EmptyPage, InvalidPage), e:
        page = paginator.page(paginator.num_pages)
    return render_to_response('listing.html', {
        'attribute': attribute,
        'objects': page.object_list,
        'page': page,
        'model': 'Author',
        'listing_type': 'author',
        'description': detail,
        'metric_table': metric_table,
    }, context_instance=RequestContext(request))

@login_required
def properties(request):
    properties = PROPERTIES.values()
    properties.sort(key=lambda property: property.count, reverse=True)
    
    from django.db import connection
    
    cursor = connection.cursor()

    language_codes = []
    changes = cursor.execute("""select language_code, count(*) as c
        from icd_categorytitles
        where category_id LIKE %s
        group by language_code
        order by language_code asc""", [settings.INSTANCE+"%"])
    for row in cursor.fetchall():
        language_code, count = row
        language_codes.append({
            'id': language_code,
            'name': language_code,
            'count': count,
        })
    
    definition_language_codes = []
    changes = cursor.execute("""select language_code, count(*) as c
        from icd_categorydefinitions
        where category_id LIKE %s
        group by language_code
        order by language_code asc""", [settings.INSTANCE+"%"])
    for row in cursor.fetchall():
        language_code, count = row
        definition_language_codes.append({
            'id': language_code,
            'name': language_code,
            'count': count,
        })
    
    display_status = []
    changes = cursor.execute("""select display_status, count(*) as c
        from icd_category
        where instance=%s
        group by display_status
        order by c desc""", [settings.INSTANCE])
    for row in cursor.fetchall():
        name, count = row
        display_status.append({
            'id': name,
            'name': DISPLAY_STATUS.get(name, '(None)'),
            'count': count,
            #'__unicode__': name,
        })
    
    titles = []
    changes = cursor.execute("""select mlm_titles, count(*) as c
        from icd_multilanguagecategorymetrics
        where instance=%s
        group by mlm_titles
        order by mlm_titles desc""", [settings.INSTANCE])
    for row in cursor.fetchall():
        mlm_titles, count = row
        titles.append({
            'id': mlm_titles,
            'name': mlm_titles,
            'count': count,
            #'__unicode__': name,
        })
        
    title_languages = []
    changes = cursor.execute("""select mlm_title_languages, count(*) as c
        from icd_multilanguagecategorymetrics
        where instance=%s
        group by mlm_title_languages
        order by mlm_title_languages desc""", [settings.INSTANCE])
    for row in cursor.fetchall():
        mlm_title_languages, count = row
        title_languages.append({
            'id': mlm_title_languages,
            'name': mlm_title_languages,
            'count': count,
            #'__unicode__': name,
        })    
    definitions = []
    changes = cursor.execute("""select mlm_definitions, count(*) as c
        from icd_multilanguagecategorymetrics
        where instance=%s
        group by mlm_definitions
        order by mlm_definitions desc""", [settings.INSTANCE])
    for row in cursor.fetchall():
        mlm_definitions, count = row
        definitions.append({
            'id': mlm_definitions,
            'name': mlm_definitions,
            'count': count,
            #'__unicode__': name,
        })
    
    definition_languages = []
    changes = cursor.execute("""select mlm_definition_languages, count(*) as c
        from icd_multilanguagecategorymetrics
        where instance=%s
        group by mlm_definition_languages
        order by mlm_definition_languages desc""", [settings.INSTANCE])
    for row in cursor.fetchall():
        mlm_definition_languages, count = row
        definition_languages.append({
            'id': mlm_definition_languages,
            'name': mlm_definition_languages,
            'count': count,
            #'__unicode__': name,
        })
    
    return render_to_response('properties.html', {
        'properties': properties,
        'display_status': display_status,
        'titles': titles,
        'definitions': definitions,
        'title_languages': title_languages,
        'definition_languages': definition_languages,
        'language_codes': language_codes,
        'definition_language_codes': definition_language_codes,
    }, context_instance=RequestContext(request))

@login_required
def property(request):
    pass

@login_required
def authors(request):
    metrics = Author.objects.all()[0].get_metrics()
    all_authors = Author.objects.filter(instance=settings.INSTANCE)
    features = []
    for name, value, description in metrics:
        authors = list(all_authors.order_by('-' + name)[:10])
        authors += reversed(all_authors.filter(**{name + '__isnull': False}).order_by(name)[:3])
        features.append((name, description, authors))
    #tags_authors = group(all_authors.order_by('affiliation'), lambda author: author.affiliation)
    for group in GROUPS:
        group.changes = sum(author.changes_count for author in group.authors_list)
        group.annotations = sum(author.annotations_count for author in group.authors_list)
        distribution = dict((author, author.changes_count + author.annotations_count) for author in group.authors_list)
        group.gini = calculate_gini(distribution)
        activity_sum = 0
        for author in group.authors_list:
            author.inactive = not author.changes_count and not author.annotations_count
            author.majority = activity_sum < 0.5 * (group.changes + group.annotations) and not author.inactive
            activity_sum += author.changes_count + author.annotations_count
    """tags = []
    for tag, authors in tags_authors:
        changes = sum(author.changes_count for author in authors)
        annotations = sum(author.annotations_count for author in authors)
        distribution = dict((author, author.changes_count + author.annotations_count) for author in authors)
        gini = calculate_gini(distribution)
        tags.append({'affiliation': tag, 'authors': authors, 'gini': gini,
            'changes': changes, 'annotations': annotations})"""
    #print features
    return render_to_response('authors.html', {
        'features': features,
        #'tags': tags,
        'groups': GROUPS,
    }, context_instance=RequestContext(request))

@login_required
def author(request, name):
    #name = name.replace('-', ' ')
    #author = Author.objects.get(instance=settings.INSTANCE, name=name)
    try:
        author = AUTHORS[settings.INSTANCE + name]
    except KeyError:
        raise Http404
    
    G = GRAPH_AUTHORS
    try:
        co_authors = G[author.instance_name]
    except KeyError:
        co_authors = {}
    co_authors = sorted(((AUTHORS[name], data['count']) for name, data in co_authors.iteritems()), key=lambda (author, count): count, reverse=True)
    #author_co_changes = sum(data['count'] for data in G[author.instance_name].values())
    author_co_changes = sum(count for name, count in co_authors)
    all_co_changes = sum(data['count'] for u, v, data in G.edges_iter(data=True))
    
    similarity_categories = [x.recommend for x in author.text_recommendations.all().order_by("-tag_similarity")[:10]]
    distance_categories = [x.recommend for x in author.distance_recommendations.all().order_by("-explicit_link_score")[:10]]
    coedit_categories = [x.recommend for x in author.cobehaviour_recommendations.all().order_by("-tag_similarity")[:10]]
    
    #print [author_co_changes, all_co_changes]
    co_authors = [(co_author, count, 100.0 * count / \
        #((author.changes_count + author.annotations_count) * (co_author.changes_count + co_author.annotations_count) / \
        #    (CHANGES_COUNT + ANNOTATIONS_COUNT)))
        (author_co_changes * sum(data['count'] for data in G[co_author.instance_name].values()) / all_co_changes))
        for co_author, count in co_authors]
    
    x, y = GRAPH_AUTHORS_POSITIONS.get(author.instance_name, (None, None))
    if x is None or y is None:
        network_url = None
    else:
        network_url = reverse('icd.views.network') + '#g=authors&x=%f&y=%f&z=2' % (x, y)
    
    reverts = author.overrides.filter(ends_session=True).order_by('-timestamp')
    reverted = author.changes.filter(ends_session=True).filter(override__isnull=False).order_by('-timestamp')
    
    return render_to_response('author.html', {
        'author': author,
        'co_authors': co_authors,
        'network_url': network_url,
        'reverts': reverts,
        'reverted': reverted,
        'similarity_categories': similarity_categories,
        'distance_categories': distance_categories,
        'coedit_categories': coedit_categories,
    }, context_instance=RequestContext(request))
   
@login_required 
def category(request, name):
    from data_categories import CATEGORIES
    
    name = CATEGORY_NAME_PREFIX + name
    category = CATEGORIES.get(name)
    if not category:
        raise Http404
    #print category.get_absolute_url()
    
    parents = category.parents.order_by('display')
    children = category.children.order_by('display')
    try:
        changes = []
        annotations = []
        for chao in category.chao.all():
            for change in chao.changes.filter(Change.relevant_filter).order_by('-timestamp'):
                changes.append(change)
            for annotation in chao.annotations.filter(Annotation.relevant_filter).order_by('-created'):
                annotations.append(annotation)
        #print changes
        #print annotations
    except OntologyComponent.DoesNotExist:
        changes = annotations = []
    
    tag_activity = [{'label': '% Primary TAG Changes', 'data': category.metrics.primary_tag_changes}, 
                    {'label': '% Secondary TAG Changes', 'data': category.metrics.secondary_tag_changes}, 
                    {'label': '% Involved TAG Changes', 'data': category.metrics.involved_tag_changes}, 
                    {'label': '% WHO Team TAG Changes', 'data': category.metrics.who_tag_changes},
                    {'label': '% Outside TAG Changes', 'data': category.metrics.outside_tag_changes}]
    
    
    timeline_changes = get_weekly(changes, lambda c: c.timestamp.date() if c.timestamp else None, to_ordinal=True,
        min_date=MIN_CHANGES_DATE, max_date=MAX_CHANGES_DATE)
    timeline_annotations = get_weekly(annotations, lambda a: a.created.date() if a.created else None, to_ordinal=True,
        min_date=MIN_CHANGES_DATE, max_date=MAX_CHANGES_DATE)
    
    authors = counts(change.author_id for change in changes + annotations)
    authors = [{'label': name[len(settings.INSTANCE):], 'data': count} for name, count in sorted(authors.iteritems(),
        key=lambda (n, c): c, reverse=True)]
    
    titles = category.category_titles.all()
    definitions = category.category_definitions.all()
    
    involved_tags = category.involved_tags.all()
    
    #x, y = GRAPH_POSITIONS[settings.DEFAULT_LAYOUT][category.name]
    x, y = category.get_pos(settings.DEFAULT_LAYOUT)
    network_url = reverse('icd.views.network') + '#x=%f&y=%f&z=2' % (x, y)
    recommendations = [x.recommend for x in category.similarity_recommendations.all().order_by("-tag_similarity")[:10]]
    return render_to_response('category.html', {
        'category': category,
        'parents': parents,
        'children': children,
        'changes': changes,
        'annotations': annotations,
        'network_url': network_url,
        'timeline_changes': timeline_changes,
        'timeline_annotations': timeline_annotations,
        'authors': authors,
        'titles': titles,
        'tag_activity': tag_activity,
        'recommendations': recommendations,
        'definitions': definitions,
        'involved_tags': involved_tags,
    }, context_instance=RequestContext(request))
    
def ajax_graph_properties(request):
    def slugify(value):
        return value.replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '')
    
    show = request.GET.get('showProperties')
    
    if show == 'follow_ups':
        adj = FOLLOW_UPS[None]
    else:
        adj = FOLLOW_UPS[3]
    pos = GRAPH_PROPERTIES_POSITIONS
    nodes = []
    edges = []
    for property_name in pos:
        property = PROPERTIES[property_name]
        x, y = pos[property.name]
        nodes.append([x, y, slugify(property.name), property.count, property.name, property.name, property.get_absolute_url(), None])
    for (u, v), count in adj.iteritems():
        if u in pos and v in pos and u != v:
            edges.append([slugify(u), slugify(v), count])
        
    return json_response({
        'nodes': nodes,
        'edges': edges,
        'minValue': min(node[3] for node in nodes),
        'maxValue': max(node[3] for node in nodes),
        'minEdge': min(edge[2] for edge in edges),
        'maxEdge': max(edge[2] for edge in edges),
    })
    
def ajax_graph_authors(request):
    show = request.GET.get('show')
    
    if show == 'overrides':
        G = GRAPH_AUTHORS_DIRECTED
    else:
        G = GRAPH_AUTHORS
    pos = GRAPH_AUTHORS_POSITIONS
    
    #weight_id = request.GET.get('weight')
    
    nodes = []
    edges = []
    for node in G:
        #data = G.node[node]
        x, y = pos[node]
        author = AUTHORS[node]
        if show == 'overrides':
            #weight = author.reverts_count + author.reverted_count
            weight = author.overridden_rel
        else:
            weight = author.changes_count + author.annotations_count
        nodes.append([x, y, node, weight, author.name, author.name, author.get_absolute_url(), author.affiliation_color()])
    for u, v, data in G.edges_iter(data=True):
        edges.append([u, v, data['count']])
        """for node in nodes:
            if node[2] == v:
                break
        else:
            print v"""
    
    return json_response({
        'nodes': nodes,
        'edges': edges,
        'minValue': min(node[3] for node in nodes),
        'maxValue': max(node[3] for node in nodes),
        'minEdge': min(edge[2] for edge in edges),
        'maxEdge': max(edge[2] for edge in edges),
    })
    
def ajax_graph(request):
    #instance = request.GET.get('instance', '')
    #if instance not in INSTANCES:
    #    raise Http404
    
    #instance = INSTANCES[settings.INSTANCE]
    
    #tag = request.GET.get('tag', '')
    #if not tag:
    
    network = request.GET.get('network')
    if network == 'authors':
        return ajax_graph_authors(request)
    elif network == 'properties':
        return ajax_graph_properties(request)
    
    from data_categories import CATEGORIES, GRAPH
    
    border_w = float(request.GET.get('borderW'))
    border_n = float(request.GET.get('borderN'))
    border_e = float(request.GET.get('borderE'))
    border_s = float(request.GET.get('borderS'))
    author_id = request.GET.get('author', '')
    layout_id = request.GET.get('layout')
    #weight_id = request.GET.get('weight')
    feature = request.GET.get('feature')
    heatmap = request.GET.get('heatmap')
    
    #if '_' in feature:
    #    raise Http404
    #accumulated = int(request.GET.get('accumulated'))
    #print "acc: '%s'" % accumulated
    #accumulated = 1 if accumulated and accumulated != "off" else 0
    """if tag:
        tag = instance.HASHTAGS.get(tag)
        if tag is None:
            raise Http404
        tags_levels = instance.get_environment(tag, True)
        tags = []
        for level in tags_levels[:-1]:
            tags.extend(level)
        network = instance.NETWORKS[tag.tag]
        clusters, positions = network
        edges = []
        for tag in tags:
            edges.append([tag.tag, sorted(((tag.tag, count) for tag, count in tag.co_tags.iteritems()),
                key=lambda (t, c): c, reverse=True)])   
            tag.x, tag.y = positions[tag.tag]
        tags = [[tag.x, tag.y, tag.tag, tag.count, clusters[tag.tag]] for tag in tags]
        sub_tags = []
    else:"""
    
    if layout_id not in [key for name, key, dot_prog in settings.LAYOUTS]:
        raise Http404
    if author_id == '':
        #author_id = None
        author = None
        if feature not in dict(FEATURES):
            raise Http404
    else:
        try:
            author = Author.from_slug(author_id)
        except Author.DoesNotExist:
            raise Http404
        #author_id = author.instance_name
        if feature not in dict(AUTHOR_FEATURES):
            raise Http404
        #print author_id
    """if author_id not in WEIGHTS:
        raise Http404
    if layout_id not in GRAPH_POSITIONS_TREE:
        raise Http404
    if author_id is None:
        tree = GRAPH_POSITIONS_TREE[layout_id]
    else:
        tree = PickledData.objects.get(settings.INSTANCE,
            'graph_positions_tree_%s_%s' % (layout_id, author_id))
    tree_id = (weight_id, accumulated)
    if tree_id not in tree:
        raise Http404
    tree = tree[tree_id]"""
    #print WEIGHTS[weight_id][accumulated].items()[:100]
    #print WEIGHTS[weight_id][accumulated]['http://who.int/icd#ICDCategory']
            
    STEP = 10
    categories = []
    sql = []
    sql_params = []
    for x in range(STEP):
        for y in range(STEP):
            """print (
                border_w + x * (border_e - border_w) / STEP,
                border_w + (x + 1) * (border_e - border_w) / STEP,
                border_n + y * (border_s - border_n) / STEP,
                border_n + (y + 1) * (border_s - border_n) / STEP
            )"""
            """categories_sub = tree.get(
                border_w + x * (border_e - border_w) / STEP,
                border_w + (x + 1) * (border_e - border_w) / STEP,
                border_n + y * (border_s - border_n) / STEP,
                border_n + (y + 1) * (border_s - border_n) / STEP
            )[-1:]"""
            x_range = (
                border_w + x * (border_e - border_w) / STEP,
                border_w + (x + 1) * (border_e - border_w) / STEP
            )
            y_range = (
                border_n + y * (border_s - border_n) / STEP,
                border_n + (y + 1) * (border_s - border_n) / STEP
            )
            if author is None:
                if feature in ACCUMULATED_FILTER:
                    table = 'icd_accumulatedcategorymetrics'
                elif feature in MULTILANGUAGE_FILTER:
                    table = 'icd_multilanguagecategorymetrics'
                elif feature in TIMESPAN_FILTER:
                    table = 'icd_timespancategorymetrics'
                else:
                    table = 'icd_categorymetrics'
                author_sql = ''
                author_params = []
            else:
                table = 'icd_authorcategorymetrics'
                author_sql = ' AND author_id = %s '
                author_params = [author.pk]
            
            if feature in MULTILANGUAGE_FILTER:
                sql.append("""SELECT category_id FROM %s USE INDEX (index_pos_%s_%s)
                    WHERE instance=%%s AND (x_%s BETWEEN %%s AND %%s) AND (y_%s BETWEEN %%s AND %%s)
                    AND %s >= 0
                    %s
                    ORDER BY %s DESC
                    LIMIT 1
                """ % (table, layout_id, feature, layout_id, layout_id, feature, author_sql, feature))
                sql_params += [settings.INSTANCE, x_range[0], x_range[1], y_range[0], y_range[1]] + author_params
            else:
                sql.append("""SELECT category_id FROM %s USE INDEX (index_pos_%s_%s)
                    WHERE instance=%%s AND (x_%s BETWEEN %%s AND %%s) AND (y_%s BETWEEN %%s AND %%s)
                    AND %s > 0
                    %s
                    ORDER BY %s DESC
                    LIMIT 1
                """ % (table, layout_id, feature, layout_id, layout_id, feature, author_sql, feature))
                sql_params += [settings.INSTANCE, x_range[0], x_range[1], y_range[0], y_range[1]] + author_params

            filter = {
                'instance': settings.INSTANCE,
                'x_' + str(layout_id) + '__range': x_range,
                'y_' + str(layout_id) + '__range': y_range,
            }
            
            """if author is None:
                categories_sub = CategoryMetrics.objects.filter(**filter)
            else:
                filter['author'] = author
                categories_sub = AuthorCategoryMetrics.objects.filter(**filter)
            #print filter
            categories_sub = categories_sub.order_by('-' + feature).select_related('category')[:1].values_list('category', flat=True)
            categories_sub = [name[len(settings.INSTANCE):] for name in categories_sub]
            #categories += [(category.category, category.get_pos(layout_id), getattr(category, feature)) for category in categories_sub]
            categories += categories_sub"""
    #USING INDEX pos_twopi_index1
    from django.db import connection #, transaction
    
    cursor = connection.cursor()

    sql = ' UNION '.join('(%s)' % statement for statement in sql)
    #print sql
    cursor.execute(sql, sql_params)
    rows = cursor.fetchall()
    #print rows
    categories = [row[0][len(settings.INSTANCE):] for row in rows]
    #print "categories..."
    #print categories
    if author is None:
        if feature in ACCUMULATED_FILTER:
            min_max = AccumulatedCategoryMetrics.objects
        elif feature in MULTILANGUAGE_FILTER:
            min_max = MultilanguageCategoryMetrics.objects
        elif feature in TIMESPAN_FILTER:
            min_max = TimespanCategoryMetrics.objects
        else:
            min_max = CategoryMetrics.objects
    else:
        min_max = AuthorCategoryMetrics.objects.filter(author=author)
    min_max = min_max.filter(instance=settings.INSTANCE).aggregate(min=Min(feature), max=Max(feature))
    min_value = min_max['min']
    max_value = min_max['max']
    
    #print (border_w, border_e, border_n, border_s)
    #categories = GRAPH_POSITIONS_TREE['twopi'].get(border_w, border_e, border_n, border_s)
    #for count, name, x, y in categories:
        #if name == 'http://who.int/icd#ICDCategory':
        #print (count, name, x, y)
    #names = set(name for count, name, x, y in categories)
    #names = set(category.name for category, pos, weight in categories)
    names = set(categories)
    #print names
    add_names = names.copy()
    while add_names:
        new_add_names = set()
        for name in add_names:
            new_add_names.update(succ for succ in GRAPH.successors(name) if succ not in names)
        names.update(new_add_names)
        add_names = new_add_names
    #print "NEW"
    #print names
    #print names
    #categories = [CATEGORIES[name] for count, name, x, y in categories]
    categories = [CATEGORIES[name] for name in names]
    
    #categories = categories[-100:]
    #categories = CATEGORIES.values()
    #print categories
    categories_list = []
    edges = []
    #for count, category, x, y in categories:
    #    category = CATEGORIES[category]
    #for category, pos, weight in categories:
    for category in categories:
        #x, y = GRAPH_POSITIONS[layout_id][category.name]
        #x, y = category.get_pos(layout_id)
        x, y = category.get_pos(layout_id)
        if author is None:
            if feature in ACCUMULATED_FILTER:
                metrics = category.accumulated_metrics
            elif feature in MULTILANGUAGE_FILTER:
                metrics = category.multilanguage_metrics
            elif feature in TIMESPAN_FILTER:
                metrics = category.timespan_metrics
            else:
                metrics = category.metrics
        else:
            metrics = category.author_metrics.get(author=author)
        weight = getattr(metrics, feature)
        #weight = GRAPH.node[category.name]['weight']
        #weight = WEIGHTS[author_id][weight_id][accumulated].get(category.name, 0)
        #category_edges = [[child.name, 1] for child in category.children.all()]
        neighbors = GRAPH.successors(category.name) #+ GRAPH.predecessors(category.name)
        category_edges = [name for name in neighbors if name in names]
        
        #print "Heatmap: %s" % heatmap
        # if heatmap is active, don't get status colors!
        if heatmap == "true":
            categories_list.append([x, y, category.name, weight, unicode(category),
                category.get_short_display(), category.get_absolute_url(), category.get_heatmap_status(category.timespan_metrics.days_after_last_change)])
        # If feature is from multilanguage, get multi language color codes
        elif feature in MULTILANGUAGE_FILTER:
            categories_list.append([x, y, category.name, weight, unicode(category),
                category.get_short_display(), category.get_absolute_url(), category.get_multilingual_status(feature)])
        # Otherwise get status colors
        else:
            categories_list.append([x, y, category.name, weight, unicode(category),
                category.get_short_display(), category.get_absolute_url(), category.get_display_status()])

        edges.append([category.name, category_edges])
    """tags = [tag for tag in tags[-100:] if tag[1] in instance.HASHTAGS]
    edges = []
    for count, item, x, y in tags:
        tag_edges = instance.CO_HASHTAGS_10[item]
        edges.append([item, tag_edges])"""
    
    #categories = [[x, y, item, count[1], -1] for count, item, x, y in categories]
    #sub_tags = []
    return json_response({
        'nodes': categories_list,
        'edges': edges,
        'minValue': min_value,
        'maxValue': max_value
        #'subTags': sub_tags,
    })
