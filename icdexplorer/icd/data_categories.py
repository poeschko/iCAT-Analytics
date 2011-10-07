"""
ICDexplorer

(c) 2011 Jan Poeschko
jan@poeschko.com
"""

from django.conf import settings

from icdexplorer.icd.models import Category
from icdexplorer.storage.models import PickledData

print "Load categories"

GRAPH = PickledData.objects.get(settings.INSTANCE, 'graph')
CATEGORIES = dict((category.name, category) for category in Category.objects.filter(instance=settings.INSTANCE))

print "Categories loaded"