"""
ICDexplorer

(c) 2011 Jan Poeschko
jan@poeschko.com

Change History
---
2012-26-01-Daniel extended _name and name fields in classes Annotatablething and
                  its derivations to 150 characters to allow for longer wiki titles
"""

from django.db import models
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.conf import settings

import urllib

from util import days, get_color

class LinearizationSpec(models.Model):
    instance = models.CharField(max_length=30, db_index=True)
    linearization = models.CharField(max_length=100)
    parent = models.ForeignKey('Category', related_name='linearizations_parent')
    child = models.ForeignKey('Category', related_name='linearizations_child')
    label = models.CharField(max_length=250)
    is_included = models.NullBooleanField() #(null=True)
    #class Meta:
    #    unique_together = (['instance', 'linearization', 'parent', 'child'])
        
CATEGORY_NAME_PREFIX = 'http://who.int/icd#'

DISPLAY_STATUS = {
            'http://who.int/icd#DS_Blue': 'blue',
            'http://who.int/icd#DS_Yellow': 'yellow',
            'http://who.int/icd#DS_Red': 'red',
        }

class Category(models.Model):
    instance_name = models.CharField(max_length=130, primary_key=True)
    instance = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=150, db_index=True)
    display = models.CharField(max_length=250, db_index=True)
    sorting_label = models.CharField(max_length=250)
    definition = models.TextField()
    children = models.ManyToManyField('self', related_name='parents', symmetrical=False)
    branches = models.ManyToManyField('self', symmetrical=False)
    linearization_parents = models.ManyToManyField('self', related_name='linearization_children',
        symmetrical=False, through=LinearizationSpec)
    
    # Overhead if coming from category: 
    #   Always going over chao then changes then categories
    # Overhead if coming from author:
    #   Always going over changes then apply_to then category
    change_authors = models.ManyToManyField('Author', related_name="change_categories")
    annotation_authors = models.ManyToManyField('Author', related_name="annotation_categories")
    
    display_status = models.CharField(max_length=250)
    primary_tag = models.CharField(max_length=250)
    secondary_tag = models.CharField(max_length=250)

    x_twopi = models.FloatField(null=True)
    y_twopi = models.FloatField(null=True)
    x_sfdp = models.FloatField(null=True)
    y_sfdp = models.FloatField(null=True)
    
    hierarchy = models.ForeignKey('self', related_name='sub_categories', null=True)
        # point to superclass with depth 1 (None for root category)
        # if there are multiple, choose the one that has a sorting label
    
    def __unicode__(self):
        #return '%s (%s)' % (self.name, self.display)
        if self.display.strip():
            return self.display
        return u'<%s>' % self.name
    
    def get_key(self):
        id = self.name
        if id.startswith(CATEGORY_NAME_PREFIX):
            id = id[len(CATEGORY_NAME_PREFIX):]
        return id
    
    def get_absolute_url(self):
        id = self.get_key()
        return reverse('icd.views.category', kwargs={'name': urllib.quote(id)})
    
    def get_short_display(self):
        display = unicode(self).strip(" '")
        parts = display.split(' ')
        if parts:
            return parts[0]
        else:
            return self.display
        
    def get_display_status(self):
        """return {
            'DS_Blue': 'blue',
            'DS_Yellow': 'yellow',
            'DS_Red': 'red',
        }.get(self.metrics.display_status, '')"""
        return DISPLAY_STATUS.get(self.display_status, '')
        
    def get_pos(self, layout):
        return (getattr(self, 'x_' + layout), getattr(self, 'y_' + layout))

    def get_multilingual_status(self, feature):
        colors = ["", "yellow", "orange", "red", "blue", "darkblue"]
        number = {
            'mlm_titles': self.multilanguage_metrics.mlm_titles,
            'mlm_title_languages': self.multilanguage_metrics.mlm_title_languages,
            'mlm_definitions': self.multilanguage_metrics.mlm_definitions,
            'mlm_definition_languages': self.multilanguage_metrics.mlm_definition_languages
        }[feature]
        
        return colors[number] if number+1 < len(colors) else colors[-1]

    def get_tags(self):
        r = []
        if self.primary_tag != '':
            r.append(self.primary_tag)
        if self.secondary_tag != '':
            r.append(self.secondary_tag)
        r.extend(self.involved_tags.values_list("name", flat=True))
        
        #special case for Internal_Medicine
        if len([x for x in r if x.startswith("http://who.int/icd#TAG_IM_")]) > 0: 
            r.append("http://who.int/icd#TAG_Internal_Medicine")

        if len([x for x in r if x.startswith("http://who.int/icd#TAG_Internal_Medicine")]) > 0:
            r.extend(Group.objects.filter(name__contains="http://who.int/icd#TAG_IM_").values_list("name", flat=True))
        
        return set(r)
    
    def get_heatmap_status(self, heatmap_feature):
        colors = ["h_blackblue", "h_darkestblue", "h_darkblue", "h_blue", "h_yellow", "h_orange", "h_red"]
        limits = [356, 180, 30, 14, 7, 3]
        
        for idx, limit in enumerate(limits):
            if heatmap_feature < limit:
                continue
            else:
                return colors[idx]
        # return hottest
        return colors[-1]
        
    class Meta:
        unique_together = [('instance', 'name')]
    
    """def get_network_url(self, layout):
        from data import GRAPH_POSITIONS
        
        x, y = GRAPH_POSITIONS[layout][self.name]
        return reverse('icd.views.network') + '#x=%f&y=%f&z=6' % (x, y)"""

class InvolvedTag(models.Model):
    category = models.ForeignKey('Category', related_name='involved_tags')
    instance = models.CharField(max_length=250, db_index=True)
    name = models.CharField(max_length=250, db_index=True)
    class Meta:
        unique_together = [('instance', 'name', 'category')]

        
class CategoryTitles(models.Model):
    category = models.ForeignKey('Category', related_name='category_titles')
    title = models.CharField(max_length=250, db_index=True)
    language_code = models.CharField(max_length=250, db_index=True)
    def __unicode__(self):
        if self.title.strip():
            return self.title

class CategoryDefinitions(models.Model):
    category = models.ForeignKey('Category', related_name='category_definitions')
    definition = models.TextField()
    language_code = models.CharField(max_length=250, db_index=True)
    def __unicode__(self):
        if self.definition.strip():
            return self.definition

class Timespan(models.Model):
    instance = models.CharField(max_length=30, db_index=True)
    start = models.DateTimeField()
    stop = models.DateTimeField()
    following = models.ManyToManyField('self', symmetrical=False, related_name='preceding')
    
class Metrics(models.Model):
    non_metrics = ['x_twopi', 'y_twopi', 'x_sfdp', 'y_sfdp']
    # redundant copy from category
    x_twopi = models.FloatField(null=True)
    y_twopi = models.FloatField(null=True)
    x_sfdp = models.FloatField(null=True)
    y_sfdp = models.FloatField(null=True)

    class Meta:
        abstract = True
        
    def sanitize(self, name, value):
        if value is None and name == 'authors_gini':
            return 0
        return value
    
    def get_metrics(self):
        result = []
        for field in self._meta.fields:
            if isinstance(field, (models.IntegerField, models.FloatField)) and field.name not in self.non_metrics:
                #result[field.name] = getattr(self, field.name)
                result.append((field.name, self.sanitize(field.name, getattr(self, field.name)), field.help_text))
        #result = [()]
        #result.sort(key=lambda (name, value, description): (not name.startswith('acc_'), description))
        result = [item for item in result if not item[0].startswith('acc_')] + \
            [item for item in result if item[0].startswith('acc_')]
        return result
    
    def get_metrics_dict(self):
        return dict((key, value) for key, value, description in self.get_metrics())
        
    def get_pos(self, layout):
        return (getattr(self, 'x_' + layout), getattr(self, 'y_' + layout))
        
    def set_pos(self, category):
        for layout, key, dot_prog in settings.LAYOUTS:
            for attr in ('x_' + key, 'y_' + key):
                setattr(self, attr, getattr(category, attr))
    
    def get_filter_metrics(self):
        result = []
        for field in self._meta.fields:
            result.append(field.name)
        return result
    
class ChAOMetrics(Metrics):
    #display_status = models.CharField(max_length=30, db_index=True, null=True, help_text="Display status")
    changes = models.IntegerField(help_text="Number of changes")
    annotations = models.IntegerField(help_text="Number of notes")
    activity = models.IntegerField(help_text="Changes + notes")
    class Meta:
        abstract = True
    
class TimespanCategoryMetrics(Metrics):
    #timespan = models.ForeignKey(Timespan, related_name='metrics')
    category = models.OneToOneField(Category, related_name='timespan_metrics')
    instance = models.CharField(max_length=30, db_index=True)
    
    days_after_last_change = models.FloatField(default=0, null=True, help_text="Days after last change")
    #days_before_first_change = models.FloatField(default=0, null=True, help_text="Days before first change")
    #days_after_median_change = models.FloatField(default=0, null=True, help_text="Days after median change")
    days_after_last_annotation = models.FloatField(default=0, null=True, help_text="Days after last note")
    #days_before_first_annotation = models.FloatField(default=0, null=True, help_text="Days before first note")
    #days_after_median_annotation = models.FloatField(default=0, null=True, help_text="Days after median note")
    days_after_last_activity = models.FloatField(default=0, null=True, help_text="Days after last activity")
    """
    changes_parents = models.IntegerField(db_index=True)
    annotations_parents = models.IntegerField(db_index=True)
    changes_children = models.IntegerField(db_index=True)
    annotations_children = models.IntegerField(db_index=True)
    
    class Meta:
        unique_together = [('timespan', 'category')]
        
    def sanitize(self, name, value):
        if value is None:
            value = super(TimespanCategoryMetrics, self).sanitize(name, value)
            if name.startswith('days_after_'):
                return days(self.timespan.stop - self.timespan.start)
            if name.startswith('days_before_'):
                return 0
        return value
    """
        
class CategoryMetrics(ChAOMetrics):
    category = models.OneToOneField(Category, related_name='metrics')
    instance = models.CharField(max_length=30, db_index=True)
    authors = models.IntegerField(db_index=True, help_text="Distinct authors of changes and annotations")
    authors_changes = models.IntegerField(db_index=True, help_text="Distinct authors of changes")
    authors_annotations = models.IntegerField(db_index=True, help_text="Distinct authors of annotations")
    authors_gini = models.FloatField(db_index=True, null=True, help_text="Authors Gini coefficient")
    parents = models.IntegerField(help_text="Number of parents")
    children = models.IntegerField(help_text="Number of children")
    depth = models.IntegerField(null=True, help_text="Depth in network")
    clustering = models.FloatField(null=True, help_text="Clustering coefficient")
    betweenness_centrality = models.FloatField(null=True, help_text="Betweenness centrality (directed)")
    betweenness_centrality_undirected = models.FloatField(null=True, help_text="Betweenness centrality (undirected)")
    pagerank = models.FloatField(null=True, help_text="Pagerank")
    #authority = models.FloatField(null=True)
    #hub = models.FloatField(null=True)
    closeness_centrality = models.FloatField(null=True, help_text="Closeness centrality")
    #eigenvector_centrality = models.FloatField(null=True)
    overrides = models.IntegerField(help_text="Overrides by different authors")
    edit_sessions = models.IntegerField(help_text="Edit sessions")
    authors_by_property = models.IntegerField(help_text="Distinct authors by property")
    
    """primary_tag_changes = models.IntegerField(null=True, help_text="Number of changes by primary TAG")
    secondary_tag_changes = models.IntegerField(null=True, help_text="Number of changes by secondary TAG")
    involved_tag_changes = models.IntegerField(null=True, help_text="Number of changes by involved TAG")
    who_tag_changes = models.IntegerField(null=True, help_text="Number of changes by who TAG")
    outside_tag_changes = models.IntegerField(null=True, help_text="Number of changes outside assigned TAGs")
    """
    
    def __unicode__(self):
        return self.category.name


class AccumulatedCategoryMetrics(Metrics):
    category = models.OneToOneField(Category, related_name='accumulated_metrics')
    instance = models.CharField(max_length=30, db_index=True)
    acc_overrides = models.IntegerField(help_text="Accumulated Overrides by different authors", default=0)
    acc_edit_sessions = models.IntegerField(help_text="Accumulated Edit sessions", default=0)
    acc_authors_by_property = models.IntegerField(help_text="Accumulated Distinct authors by property", default=0)
    acc_authors = models.IntegerField(default=0, help_text="Accumulated Distinct authors of changes and notes")
    acc_authors_changes = models.IntegerField(default=0, help_text="Accumulated Distinct authors of changes")
    acc_authors_annotations = models.IntegerField(default=0, help_text="Accumulated Distinct authors of notes")
    acc_changes = models.IntegerField(default=0, help_text="Accumulated Number of changes")
    acc_annotations = models.IntegerField(default=0, help_text="Accumulated Number of notes")
    acc_activity = models.IntegerField(default=0, help_text="Accumulated Changes + notes")

    def __unicode__(self):
        return self.category.name

        
class MultilanguageCategoryMetrics(Metrics):
    category = models.OneToOneField(Category, related_name='multilanguage_metrics')
    instance = models.CharField(max_length=30, db_index=True)
    mlm_titles = models.IntegerField(help_text="Number of titles", default=0)
    mlm_title_languages = models.IntegerField(help_text="Number of title languages", default=0)
    mlm_definitions = models.IntegerField(help_text="Number of definitions", default=0)
    mlm_definition_languages = models.IntegerField(help_text="Number of definition languages", default=0)
    
    def __unicode__(self):
        return self.category.name
        

class AuthorCategoryMetrics(ChAOMetrics):
    category = models.ForeignKey(Category, related_name='author_metrics')
    instance = models.CharField(max_length=30, db_index=True)
    author = models.ForeignKey('Author', related_name='category_metrics')
    acc_changes = models.IntegerField(default=0, help_text="Accumulated Number of changes")
    acc_annotations = models.IntegerField(default=0, help_text="Accumulated Number of notes")
    acc_activity = models.IntegerField(default=0, help_text="Accumulated Changes + notes")
    
    def __unicode__(self):
        return '%s: %s' % (self.author.name, self.category.name)
    
    class Meta:
        unique_together = [('category', 'author')]

class AnnotatableThing(models.Model):
    instance_name = models.CharField(max_length=130, primary_key=True)
    instance = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=150, db_index=True)
    
    class Meta:
        unique_together = [('instance', 'name')]
        
        #abstract = True
    
class OntologyComponent(AnnotatableThing):
    #id = models.CharField(max_length=250, primary_key=True)
    #children = models.ManyToManyField('self', related_name='parents', symmetrical=False)
    
    #current_name = models.CharField(max_length=250)
    
    _instance = models.CharField(max_length=30, db_index=True)
    _name = models.CharField(max_length=150, db_index=True)
    
    type = models.CharField(max_length=250, db_index=True)
    #category = models.OneToOneField(Category, related_name='chao')
    category = models.ForeignKey(Category, related_name='chao')
    
    def __unicode__(self):
        return self._name

class User(models.Model):
    #pass
    instance_name = models.CharField(max_length=130, primary_key=True)
    instance = models.CharField(max_length=30, db_index=True)
    id = models.CharField(max_length=100)
    type = models.CharField(max_length=250)
    name = models.CharField(max_length=100, db_index=True)
    #browser_text = models.TextField()
    domain_of_interest = models.ManyToManyField(OntologyComponent, related_name='domain_of_interest_by',
        db_table='icd_user_domain_of_interest')
    watched_branches = models.ManyToManyField(OntologyComponent, related_name='watched_branch_by',
        db_table='icd_user_watched_branches')
    watched_entities = models.ManyToManyField(OntologyComponent, related_name='watched_entity_by',
        db_table='icd_user_watched_entities')
    
    class Meta:
        unique_together = [('instance', 'name')]
    
class Change(AnnotatableThing):
    #relevant_filter = ~Q(action="Export") & ~Q(context__startswith="Automatic")
    if settings.IS_NCI:
        relevant_filter = ~Q(action="Composite_Change")
    elif settings.IS_WIKI:
        relevant_filter = Q()
    else:
        relevant_filter = Q(action="Composite_Change") & ~Q(context__startswith="Automatic")
    
    _instance = models.CharField(max_length=30, db_index=True)
    _name = models.CharField(max_length=150, db_index=True)   # extended to 150 characters to allow for longer wiki titles
    
    #id = models.CharField(max_length=250, primary_key=True)
    type = models.CharField(max_length=250)
    author = models.ForeignKey('Author', related_name='changes')
    timestamp = models.DateTimeField(db_index=True)
    apply_to = models.ForeignKey(OntologyComponent, related_name='changes', null=True)
    #session_component = models.ForeignKey('SessionChange', related_name="changes", null=True)
    composite = models.ForeignKey('self', related_name='parts', null=True)
    #context = models.CharField(max_length=250)
    context = models.TextField()
    action = models.CharField(max_length=250)
    browser_text = models.TextField()
    
    kind = models.CharField(max_length=100)
    property_original = models.CharField(max_length=100)
    property = models.CharField(max_length=100, db_index=True)
    for_property = models.CharField(max_length=100)
    old_value = models.TextField()
    new_value = models.TextField()
    additional_info = models.TextField()
    apply_to_url = models.CharField(max_length=250)
    
    #revert = models.ForeignKey('Change', null=True)
    override = models.ForeignKey('Change', null=True, related_name='overriding')
    #session_revert = models.ForeignKey('Change', null=True, related_name='reverting_session')
    override_by = models.ForeignKey('Author', null=True, related_name='overrides')
    ends_session = models.BooleanField(default=False)
    
    levenshtein_distance = models.IntegerField(null=True)
    levenshtein_distance_rel = models.FloatField(null=True)
    levenshtein_distance_norm = models.FloatField(null=True)
    levenshtein_similarity = models.FloatField(null=True)
    lcs = models.IntegerField(null=True)
    lcs_rel = models.FloatField(null=True)
    
    #category = models.ForeignKey(Category, null=True, related_name='changes')
    
    #Replaced diagnosticCriteriaText for diagnosticCriteria of F22.0 Delusional disorder. Old value: (empty) . New value: Comments: In evaluating the presence of the these abnormal subjective experiences and behaviour, special care
    #Set condition at V01-X59 Accidents to Retired -- Apply to: http://who.int/icd#V01-X59

    kinds = {
        'Property': r'Property: (?P<property>.*?) for instance: .*? set to: (?P<new_value>.*?)\(Old values:(?P<old_value>.*?)\)',
        'Set': r'Set (?P<property>.*?) for .*?\. Old value: (?P<old_value>.*?)\. New value: (?P<new_value>.*?) -- Apply to: (?P<apply_to_url>.*?)',
        'Replaced': r"Replaced (?P<property>.*?) of .*?\. Old value: (?P<old_value>.*?)\. New value: (?P<new_value>.*?) -- Apply to: (?P<apply_to_url>.*?)",
        'ReplacedProperty': r"Replaced (?P<for_property>.*?) for (?P<property>.*?) of .*?\. Old value: (?P<old_value>.*?)\. New value: (?P<new_value>.*?) -- Apply to: (?P<apply_to_url>.*?)",
        'Hierarchy': r"Change in hierarchy for class: .*?\.(?: Parents added: \( (?P<new_value>.*?)\)\.)?(?: Parents removed: \( (?P<old_value>.*?)\)\.)? -- Apply to: (?P<apply_to_url>.*?)",
        'Added': r"Added a new (?P<property>.*?) to .*? -- Apply to: (?P<apply_to_url>.*?)",
        'AddedNewValue': r"Added a new (?P<property>.*?) to .*?\. Added value: (?P<new_value>.*?) -- Apply to: (?P<apply_to_url>.*?)",
        'AddedAs': r"Added (?P<new_value>.*?) as (?P<property>.*?) to .*? -- Apply to: (?P<apply_to_url>.*?)",
        'AddedValue': r"Added value(?P<new_value>.*?) for property (?P<property>.*?) for .*? -- Apply to: (?P<apply_to_url>.*?)",
        'AddDirectType': r"Add to .*? direct type : (?P<new_value>.*?) -- Apply to: (?P<apply_to_url>.*?)",
        'RemoveDirectType': r"Remove from .*? direct type : (?P<old_value>.*?) -- Apply to: (?P<apply_to_url>.*?)",
        'Removed': r"Removed value (?P<old_value>.*?) for property (?P<property>.*?) from .*? -- Apply to: (?P<apply_to_url>.*?)",
        'RemovedSuperclass': "Remove superclass (?P<old_value>.*?) from .*? -- Apply to: (?P<apply_to_url>.*?)",
        'RemoveDeprecationFlag': r"Remove deprecation flag from .*? -- Apply to: (?P<apply_to_url>.*?)",
        'Deleted': r"Deleted (?P<property>.*?) from .*?\. Deleted value: (?P<old_value>.*?) -- Apply to: (?P<apply_to_url>.*?)",
        'DeleteCondition': r"Delete condition (?P<old_value>.*?) from .*? -- Apply to: (?P<apply_to_url>.*?)",
        'SetCondition': r"Set condition at .*? to (?P<new_value>.*?) -- Apply to: (?P<apply_to_url>.*?)",
        'Moved': r"Moved class:? (?P<additional_info>.*?). Old parent: (?P<old_value>.*?), [Nn]ew parent: (?P<new_value>.*?)",
        'CreatedReference': r"Created reference on .*? (?P<new_value>[^\s]*) -- Apply to: (?P<apply_to_url>.*?)",
        'ImportedReference': r"Imported reference for .*? Reference: (?P<new_value>.*?) -- Apply to: (?P<apply_to_url>.*?)",
        'ImportedReferenceProperty': r"Imported reference for .*? and property (?P<property>.*?)\. Reference: (?P<new_value>.*?) -- Apply to: (?P<apply_to_url>.*?)",
        'ReplacedReference': r"Replaced reference for .*? New reference: (?P<new_value>.*?) -- Apply to: (?P<apply_to_url>.*?)",
        'CreateReference': r"Create a (?P<property>.*?) reference on .*? (?P<new_value>[^\s]*) -- Apply to: (?P<apply_to_url>.*?)",
        'ModifiedClassDescription': r"Modify .*? class description",
        'Export': r"Exported branch .*? to a spreadsheet\. Download spreadsheet from: (?P<new_value>.*?)",
        'RetireClass': r"Retire classes: (?P<old_value>.*?)\. Children of retired classes are also retired\.",
        'RetireClassMoveChildren': r"Retire classes: (?P<old_value>.*?)\. Children of retired classes are moved under new parent: (?P<new_value>.*?)",
        'CreateClass': [r"create class",
            r"Created class (?P<new_value>.*?)",
            r"Create class with name: (?P<new_value>.*?), parents: (?P<additional_info>.*?)"],
        'DeleteClass': r"Delete class (?P<old_value>.*?) -- Apply to: (?P<apply_to_url>.*?)",
        'Automatic': r"Automatic (?P<additional_info>.*?)",
        'AnnotationChange': r"Annotation change for (?P<property>.*?), property: (?P<for_property>.*?)",
    }
    
    def __unicode__(self):
        return self._name
    
class Annotation(AnnotatableThing):
    relevant_filter = Q()
    
    _instance = models.CharField(max_length=30, db_index=True)
    _name = models.CharField(max_length=150, db_index=True)
    
    #id = models.CharField(max_length=250, primary_key=True)
    type = models.CharField(max_length=250)
    author = models.ForeignKey('Author', related_name='annotations')
    created = models.DateTimeField(null=True)
    modified = models.DateTimeField(null=True)
    annotates = models.ForeignKey(AnnotatableThing, related_name='annotations_direct')
    subject = models.CharField(max_length=250)
    body = models.TextField()
    context = models.CharField(max_length=250)
    #related = models.ForeignKey('self', related_name='replies')
    related = models.CharField(max_length=250)
    archived = models.NullBooleanField()
    browser_text = models.TextField()
    #change = models.ForeignKey(Change, related_name='annotations')
    #annotates = models.GenericForeignKey()  # to Concept, Change, or Annotation itself
    
    component = models.ForeignKey(OntologyComponent, related_name='annotations', null=True)
    
class Author(models.Model):
    non_metrics = []
    
    instance_name = models.CharField(max_length=130, primary_key=True)
    instance = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=100)
    
    changes_count = models.IntegerField(db_index=True, default=0, help_text="Number of changes")
    annotations_count = models.IntegerField(db_index=True, default=0, help_text="Number of notes")
    
    sessions_count = models.IntegerField(default=0, help_text="Property edit sessions")
    overrides_count= models.IntegerField(default=0, help_text="Overrides done by author")
    overridden_count = models.IntegerField(default=0, help_text="Changes overridden by others")
    overridden_rel = models.FloatField(default=0, help_text="Overridden changes relative to all edits") 
    
    #email = models.CharField(max_length=100, null=True)
    #affiliation = models.CharField(max_length=50, null=True)
    #tag_member = models.NullBooleanField(null=True)
    #managing_editor = models.NullBooleanField(null=True)
    
    groups = models.ManyToManyField('Group', related_name='authors')
    
    def get_absolute_url(self):
        return reverse('icd.views.author', kwargs={'name': urllib.quote(self.name.encode('utf-8'))})
    
    def __unicode__(self):
        return self.name
    
    def to_slug(self):
        return self.instance_name.replace(' ', '_')

    @staticmethod
    def from_slug(slug):
        #print slug
        slug = slug[:len(settings.INSTANCE)] + slug[len(settings.INSTANCE):].replace('_', ' ')
        #print slug
        return Author.objects.get(instance_name=slug)
    
    def affiliation_color(self):
        #return get_color(self.affiliation)
        for group in self.groups_list:
            if group.name.startswith(Group.tag_prefix):
                return get_color(group.name[len(Group.tag_prefix):])
        return None
    
    def get_metrics(self):
        result = []
        for field in self._meta.fields:
            if isinstance(field, (models.IntegerField, models.FloatField)) and field.name not in self.non_metrics:
                result.append((field.name, getattr(self, field.name), field.help_text))
        result = [item for item in result if not item[0].startswith('acc_')] + \
            [item for item in result if item[0].startswith('acc_')]
        return result
    
    def get_filter_metrics(self):
        result = []
        for field in self._meta.fields:
            result.append(field.name)
        return result

class Group(models.Model):
    tag_prefix = 'http://who.int/icd#TAG_'
    instance = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=100)
    
    progress = models.FloatField(null=True, help_text="Percentage of blue categories")
    category_count = models.IntegerField(null=True, help_text="Number of categories")
    change_count = models.IntegerField(null=True, help_text="")
    blue_categories = models.IntegerField(null=True, help_text="")
    yellow_categories = models.IntegerField(null=True, help_text="")
    red_categories = models.IntegerField(null=True, help_text="")
    grey_categories = models.IntegerField(null=True, help_text="")
    
    changes_in_primary = models.IntegerField(null=True, help_text="")
    changes_in_secondary = models.IntegerField(null=True, help_text="")
    changes_in_involved = models.IntegerField(null=True, help_text="")
    
    activity_in_primary = models.FloatField(null=True, help_text="")
    activity_in_secondary = models.FloatField(null=True, help_text="")
    activity_in_involved = models.FloatField(null=True, help_text="")
    
    #subgroups = models.ForeignKey('self', related_name='sub_groups', null=True)
    
    def __unicode__(self):
        name = self.name
        if name.startswith(Group.tag_prefix):
            name = name[len(Group.tag_prefix):]
        return name

class SessionChange(models.Model):
    instance = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    session = models.OneToOneField('Session', related_name='session_component')
    
        
class Session(models.Model):
    #id = models.IntegerField(primary_key=True) 
    instance = models.CharField(max_length=30, db_index=True)
    author = models.ForeignKey('Author', related_name='sessions')
    start_date = models.DateTimeField(null=True, db_index=True)
    end_date = models.DateTimeField(db_index=True, null=True)
    #changes = models.ManyToManyField('Change', related_name='changes')
    #treshold = models.DateTimeField(db_index=True, null=True)
    #annotations = models.ManyToManyField('Annotation', related_name='annotations')
    change_count = models.IntegerField(null=True, db_index=True, default=0, help_text="Number of changes")
    annotation_count = models.IntegerField(null=True, db_index=True, default=0, help_text="Number of annotations")
    duration = models.FloatField(null=True, help_text="Duration of session in minutes")
    branches = models.FloatField(null=True, help_text="Number of branches")
    total_distance = models.IntegerField(null=True, help_text="Total distance between changes (chronologically)")
    total_depth = models.IntegerField(null=True, help_text="Total distance between nodes and root")
        
class Property(models.Model):
    instance = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=100)
    
    count = models.IntegerField(default=0)
    
    authors_count = models.IntegerField(null=True)
    authors_gini = models.FloatField(null=True)
    
    def __unicode__(self):
        name = self.name
        return name
    
    def get_absolute_url(self):
        return ''
        return reverse('icd.views.property', kwargs={'name': urllib.quote(self.name.encode('utf-8'))})

class BasicOntologyStatistics(models.Model):
    # Static Values, once inserted into DB
    # However needed for all instances
    instance = models.CharField(max_length=30, db_index=True)
    change_count = models.IntegerField(null=True, default=0, help_text="Number of changes")
    annotation_count = models.IntegerField(null=True, default=0, help_text="Number of annotations")
    author_count = models.IntegerField(null=True, default=0, help_text="Number of authors")
    category_count = models.IntegerField(null=True, default=0, help_text="Number of categories")
    tag_count = models.IntegerField(null=True, default=0, help_text="Number of TAGs")
    
    zero_change_categories_count = models.IntegerField(null=True, default=0, help_text="Number of categories with 0 changes")
    avrg_change_categories_count = models.IntegerField(null=True, default=0, help_text="Number of categories with < 5 changes")
    gta_change_categories_count = models.IntegerField(null=True, default=0, help_text="Number of categories with > 5 changes")
    
    zero_annotation_categories_count = models.IntegerField(null=True, default=0, help_text="Number of categories with 0 annotations")
    avrg_annotation_categories_count = models.IntegerField(null=True, default=0, help_text="Number of categories with < 5 annotations")
    gta_annotation_categories_count = models.IntegerField(null=True, default=0, help_text="Number of categories with > 5 annotations")
    
    average_changes_per_category = models.FloatField(null=True, default=0.0, help_text="Average changes per category")
    average_annotations_per_category = models.FloatField(null=True, default=0.0, help_text="Average annotations per category")
    blue_category_count = models.IntegerField(null=True, default=0, help_text="Number of categories with blue display status")
    yellow_category_count = models.IntegerField(null=True, default=0, help_text="Number of categories with yellow display status")
    red_category_count = models.IntegerField(null=True, default=0, help_text="Number of categories with red display status")
    grey_category_count = models.IntegerField(null=True, default=0, help_text="Number of categories with grey display status")
    
    blue_changes = models.IntegerField(null=True, default=0, help_text="Number of changes on blue categories")
    yellow_changes = models.IntegerField(null=True, default=0, help_text="Number of changes on yellow categories")
    red_changes = models.IntegerField(null=True, default=0, help_text="Number of changes on red categories")
    grey_changes = models.IntegerField(null=True, default=0, help_text="Number of changes on grey categories")

    primary_activity_per_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as primary tag")
    secondary_activity_per_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as secondary tag")
    involved_activity_per_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as involved tag")
    who_activity_per_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors from WHO")
    outside_activity_per_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors outside assigned TAGs")
    
    primary_activity_per_blue_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as primary tag")
    secondary_activity_per_blue_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as secondary tag")
    involved_activity_per_blue_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as involved tag")
    who_activity_per_blue_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors from WHO")
    outside_activity_per_blue_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors outside assigned TAGs")
    
    primary_activity_per_yellow_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as primary tag")
    secondary_activity_per_yellow_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as secondary tag")
    involved_activity_per_yellow_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as involved tag")
    who_activity_per_yellow_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors from WHO")
    outside_activity_per_yellow_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors outside assigned TAGs")
    
    primary_activity_per_red_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as primary tag")
    secondary_activity_per_red_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as secondary tag")
    involved_activity_per_red_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as involved tag")
    who_activity_per_red_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors from WHO")
    outside_activity_per_red_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors outside assigned TAGs")
    
    primary_activity_per_grey_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as primary tag")
    secondary_activity_per_grey_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as secondary tag")
    involved_activity_per_grey_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors with assigned tag on concepts with tag assigned as involved tag")
    who_activity_per_grey_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors from WHO")
    outside_activity_per_grey_category = models.FloatField(null=True, default=0.0, help_text="% of all changes done by authors outside assigned TAGs")
    
    tbd_concepts = models.IntegerField(null=True, default=0, help_text="Number of \"To be deleted\" categories")
    dtbm_concepts = models.IntegerField(null=True, default=0, help_text="Number of \"Decision to be made\" categories")
    tbr_concepts = models.IntegerField(null=True, default=0, help_text="Number of \"To be retired\" categories")

#class Recommender(models.Model):
#    instance=models.CharField(max_length=30, db_index=True)
    
class CategoriesTagRecommendations(models.Model):
    instance=models.CharField(max_length=30, db_index=True)
    category = models.ForeignKey('Category', related_name='similarity_recommendations')
    recommend = models.ForeignKey('Category', related_name='category_recommendations')
    tag_similarity = models.FloatField(null=True, default=0.0, help_text="Tag Similarity")

class UserTagRecommendations(models.Model):
    instance=models.CharField(max_length=30, db_index=True)
    user = models.ForeignKey('Author', related_name='text_recommendations')
    recommend = models.ForeignKey('Category', related_name='user_recommendations')
    tag_similarity = models.FloatField(null=True, default=0.0, help_text="Tag Similarity")

class UserDistanceRecommendations(models.Model):
    instance=models.CharField(max_length=30, db_index=True)
    user = models.ForeignKey('Author', related_name='distance_recommendations')
    recommend = models.ForeignKey('Category', related_name='similar_category')
    explicit_link_score = models.FloatField(null=True, default=0.0, help_text="Explicit link score")
    
class UserCoBehaviourRecommendations(models.Model):
    instance=models.CharField(max_length=30, db_index=True)
    user = models.ForeignKey('Author', related_name='cobehaviour_recommendations')
    recommend = models.ForeignKey('Category', related_name='cobehaviour_recommendation')
    tag_similarity = models.FloatField(null=True, default=0.0, help_text="TAG Similarity")

class UserUserTagRecommendations(models.Model):
    instance=models.CharField(max_length=30, db_index=True)
    user = models.ForeignKey('Author', related_name='author_recommendations')
    recommend = models.ForeignKey('Author', related_name='similar_author')
    tag_similarity = models.FloatField(null=True, default=0.0, help_text="Explicit link score")
    
