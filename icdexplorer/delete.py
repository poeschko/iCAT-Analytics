# -*- coding: UTF-8 -*-

"""
deletes falsely inserted wiki data from the database
"""

from django.core.management import setup_environ
import settings

setup_environ(settings)

from django.db.models import Q, Min, Max, Count
from django.conf import settings

from icd.models import (Category, OntologyComponent, LinearizationSpec, AnnotatableThing,
    Change, Annotation, CategoryMetrics, User, Timespan, TimespanCategoryMetrics, Author,
    AuthorCategoryMetrics,
    Property, Group)

import gc

def queryset_iterator(queryset, chunksize=1000):
    '''
    Iterate over a Django Queryset ordered by the primary key

    This method loads a maximum of chunksize (default: 1000) rows in it's
    memory at the same time while django normally would load all rows in it's
    memory. Using the iterator() method only causes it to not preload all the
    classes.

    Note that the implementation of the iterator does not support ordered query sets.
    '''
    counter = 0
    pk = 0
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            counter = counter + 1
            print counter
            yield row
        gc.collect()    

tobedeleted = ["Template talk:ICD10", "User talk:Brianhn1/Sandbox", "User talk:Coldplayforthewin", "User talk:Fainites/archive 4", "User talk:Hydrolix123", "User talk:Rosmoran/sandbox", "User talk:Yoninah/Archive 6", "Wikipedia talk:WikiProject Medicine/Archive 13", "Wikipedia talk:WikiProject Medicine/Archive 24", "Gastric lavage", "Parasitic pneumonia", "Hospitalism", "Small cleaved cells", "Questioning (sexuality and gender)", "Clutton's joints", "ICHD classification and diagnosis of migraine", "Querulant", "List of hematologic conditions",  "Homosexuality"]

"""
some database statistics before and after deletions...
annotatablething '1.161.418' --> '1.149.540' 
author '336.307' --> '334.067' --> '332.040'
category '3.504' --> '3.485' --> '3.454'
change '1.157.913' --> '1.146.054' --> '1.138.280'
"""

for category in tobedeleted:
    print category
    icname = settings.INSTANCE + category
    
    ca = Category.objects.filter(instance_name = icname).get()
    at = AnnotatableThing.objects.filter(instance_name = icname).get()
    ca.delete()
    at.delete()
    """
    # Note: It might be better to do this by executing the following SQL-Query after the deletion of the Categories and the AnnotatableThings
    # DELETE FROM wiki.icd_author WHERE
    instance_name NOT IN (SELECT author_id FROM wiki.icd_change);
    
    print "checking authors"
    # check if any authors need to be deleted as well
    for index, a in authors:
        print index, " of ", len(authors)
        if Change.objects.filter(author = settings.INSTANCE + a).count() == 0:
            print "deleting author " # ,a
            Author.objects.filter(instance_name = settings.INSTANCE + a).get().delete()
    """