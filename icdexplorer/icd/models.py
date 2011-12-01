"""
ICDexplorer

(c) 2011 Jan Poeschko
jan@poeschko.com
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
        
CATEGORY_NAME_PREFIX = 'http://who.int/ictm#'

DISPLAY_STATUS = {
            'http://who.int/ictm#DS_Blue': 'blue',
            'http://who.int/ictm#DS_Yellow': 'yellow',
            'http://who.int/ictm#DS_Red': 'red',
        }

class Category(models.Model):
    instance_name = models.CharField(max_length=130, primary_key=True)
    instance = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    display = models.CharField(max_length=250, db_index=True)
    sorting_label = models.CharField(max_length=250)
    definition = models.TextField()
    children = models.ManyToManyField('self', related_name='parents', symmetrical=False)
    linearization_parents = models.ManyToManyField('self', related_name='linearization_children',
        symmetrical=False, through=LinearizationSpec)
    
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
            'titles': self.metrics.titles,
            'title_languages': self.metrics.title_languages,
            'definitions': self.metrics.definitions,
            'definition_languages': self.metrics.definition_languages
        }[feature]
        
        return colors[number] if number+1 < len(colors) else colors[-1]

    class Meta:
        unique_together = [('instance', 'name')]
    
    """def get_network_url(self, layout):
        from data import GRAPH_POSITIONS
        
        x, y = GRAPH_POSITIONS[layout][self.name]
        return reverse('icd.views.network') + '#x=%f&y=%f&z=6' % (x, y)"""

class CategoryTitles(models.Model):
    category = models.ForeignKey('Category', related_name='category_title')
    title = models.CharField(max_length=250, db_index=True)
    language_code = models.CharField(max_length=250, db_index=True)
    
    def __unicode__(self):
        #return '%s (%s)' % (self.name, self.display)
        if self.title.strip():
            return self.title
        return u'<%s>' % self.name

class CategoryDefinitions(models.Model):
    category = models.ForeignKey('Category', related_name='category_definition')
    definition = models.TextField()
    language_code = models.CharField(max_length=250, db_index=True)
    
    def __unicode__(self):
        #return '%s (%s)' % (self.name, self.display)
        if self.definition.strip():
            return self.definition
        return u'<%s>' % self.name

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
    
    changes = models.IntegerField(help_text="Number of changes")
    annotations = models.IntegerField(help_text="Number of notes")
    activity = models.IntegerField(help_text="Changes + notes")
    
    acc_changes = models.IntegerField(help_text="Accumulated Number of changes")
    acc_annotations = models.IntegerField(help_text="Accumulated Number of notes")
    acc_activity = models.IntegerField(help_text="Accumulated Changes + notes")
    
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
    
class ChAOMetrics(Metrics):
    authors = models.IntegerField(help_text="Distinct authors of changes and notes")
    authors_changes = models.IntegerField(help_text="Distinct authors of changes")
    authors_annotations = models.IntegerField(help_text="Distinct authors of notes")
    authors_gini = models.FloatField(null=True, help_text="Authors Gini coefficient")
    
    acc_authors = models.IntegerField(help_text="Accumulated Distinct authors of changes and notes")
    acc_authors_changes = models.IntegerField(help_text="Accumulated Distinct authors of changes")
    acc_authors_annotations = models.IntegerField(help_text="Accumulated Distinct authors of notes")
    
    #display_status = models.CharField(max_length=30, db_index=True, null=True, help_text="Display status")
    
    class Meta:
        abstract = True
    
class TimespanCategoryMetrics(ChAOMetrics):
    timespan = models.ForeignKey(Timespan, related_name='metrics')
    category = models.ForeignKey(Category, related_name='timespan_metrics')
    
    days_after_last_change = models.FloatField(null=True, help_text="Days after last change")
    days_before_first_change = models.FloatField(null=True, help_text="Days before first change")
    days_after_median_change = models.FloatField(null=True, help_text="Days after median change")
    days_after_last_annotation = models.FloatField(null=True, help_text="Days after last note")
    days_before_first_annotation = models.FloatField(null=True, help_text="Days before first note")
    days_after_median_annotation = models.FloatField(null=True, help_text="Days after median note")
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
        
class CategoryMetrics(ChAOMetrics):
    category = models.OneToOneField(Category, related_name='metrics')
    instance = models.CharField(max_length=30, db_index=True)
    
    #changes = models.IntegerField(db_index=True, help_text="Number of changes")
    #annotations = models.IntegerField(db_index=True, help_text="Number of annotations")
    #authors = models.IntegerField(db_index=True, help_text="Distinct authors of changes and annotations")
    #authors_changes = models.IntegerField(db_index=True, help_text="Distinct authors of changes")
    #authors_annotations = models.IntegerField(db_index=True, help_text="Distinct authors of annotations")
    #authors_gini = models.FloatField(db_index=True, null=True, help_text="Authors Gini coefficient")
    
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

    acc_overrides = models.IntegerField(help_text="Accumulated Overrides by different authors", default=0)
    acc_edit_sessions = models.IntegerField(help_text="Accumulated Edit sessions", default=0)
    acc_authors_by_property = models.IntegerField(help_text="Accumulated Distinct authors by property", default=0)
    
    titles = models.IntegerField(help_text="Number of different titles", default=0)
    title_languages = models.IntegerField(help_text="Number of different title languages", default=0)
    definitions = models.IntegerField(help_text="Number of different definitions", default=0)
    definition_languages = models.IntegerField(help_text="Number of different definition languages", default=0)
    
    def __unicode__(self):
        return self.category.name
    
class AuthorCategoryMetrics(Metrics):
    category = models.ForeignKey(Category, related_name='author_metrics')
    instance = models.CharField(max_length=30, db_index=True)
    author = models.ForeignKey('Author', related_name='category_metrics')
    
    def __unicode__(self):
        return '%s: %s' % (self.author.name, self.category.name)
    
    class Meta:
        unique_together = [('category', 'author')]

class AnnotatableThing(models.Model):
    instance_name = models.CharField(max_length=130, primary_key=True)
    instance = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    
    class Meta:
        unique_together = [('instance', 'name')]
        
        #abstract = True
    
class OntologyComponent(AnnotatableThing):
    #id = models.CharField(max_length=250, primary_key=True)
    #children = models.ManyToManyField('self', related_name='parents', symmetrical=False)
    
    #current_name = models.CharField(max_length=250)
    
    _instance = models.CharField(max_length=30, db_index=True)
    _name = models.CharField(max_length=100, db_index=True)
    
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
    else:
        relevant_filter = Q(action="Composite_Change") & ~Q(context__startswith="Automatic")
    
    _instance = models.CharField(max_length=30, db_index=True)
    _name = models.CharField(max_length=100, db_index=True)
    
    #id = models.CharField(max_length=250, primary_key=True)
    type = models.CharField(max_length=250)
    author = models.ForeignKey('Author', related_name='changes')
    timestamp = models.DateTimeField(db_index=True)
    apply_to = models.ForeignKey(OntologyComponent, related_name='changes', null=True)
    composite = models.ForeignKey('self', related_name='parts')
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
    _name = models.CharField(max_length=100, db_index=True)
    
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
    
class Group(models.Model):
    tag_prefix = 'http://who.int/ictm#TAG_'
    
    instance = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=100)
    
    def __unicode__(self):
        name = self.name
        if name.startswith(Group.tag_prefix):
            name = name[len(Group.tag_prefix):]
        return name
    
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
