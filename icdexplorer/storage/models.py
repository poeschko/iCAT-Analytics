# -*- coding: UTF-8 -*-

"""
ICDexplorer

(c) 2011 Jan Poeschko
jan@poeschko.com
"""

import base64
import cPickle as pickle

from django.db import models, connection, transaction
from django.db.models import F

JUNK_SIZE = 500000

class DataModel(models.Model):
    #instance = models.ForeignKey(Instance)
    instance = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    
    class Meta:
        abstract = True
        #index_together = [('instance', 'name')]
        
class PickledDataManager(models.Manager):
    def set(self, instance, name, data):
        obj, created = self.get_or_create(instance=instance, name=name)
        obj.set_data(data)
        #obj.save()
        
    def get(self, instance, name):
        obj, created = self.get_or_create(instance=instance, name=name)
        return obj.get_data()
    
class DataJunk(models.Model):
    ref_model = models.CharField(max_length=250)
    ref_id = models.IntegerField()
    order = models.IntegerField()
    junk = models.TextField()
        
class AbstractPickledData(DataModel):

    def set_data(self, data):
        data = pickle.dumps(data)
        data = base64.encodestring(data)
        
        table_name = self._meta.db_table
        DataJunk.objects.filter(ref_model=table_name, ref_id=self.id).delete()
        order = 1
        while data:
            junk = data[:JUNK_SIZE]
            data = data[JUNK_SIZE:]
            junk = DataJunk(ref_model=table_name, ref_id=self.id, order=order, junk=junk)
            junk.save()
            order += 1

    def get_data(self):
        table_name = self._meta.db_table
        junks = DataJunk.objects.filter(ref_model=table_name, ref_id=self.id).order_by('order').values_list('junk', flat=True)
        data = ''.join(junks)
        
        data = base64.decodestring(data)
        data = pickle.loads(data)
        return data

    data = property(get_data, set_data)
    
    class Meta:
        abstract = True
    
class PickledData(AbstractPickledData):
    objects = PickledDataManager()

class Dict(AbstractPickledData):
    key = models.CharField(max_length=250)
    #value = models.TextField()
    
class StringDict(DataModel):
    key = models.CharField(max_length=250)
    value = models.CharField(max_length=250)
    
class CountDict(DataModel):
    key = models.CharField(max_length=250)
    other = models.CharField(max_length=250)
    count = models.IntegerField()
    
class AbstractDBDict(object):    
    def __init__(self, instance, name):
        self.instance = instance
        self.name = name
        
        self.lazy_items = []
        
    def get_query_set(self):
        return self.model.objects.filter(instance=self.instance, name=self.name)
    
    def commit(self):
        pass
    
class DBDict(AbstractDBDict):
    model = Dict    
 
    def __getitem__(self, key):
        try:
            item = self.get_query_set().get(key=key)
            return item.get_data()
        except Dict.DoesNotExist:
            raise KeyError(key)
 
    def __setitem__(self, key, value):
        item, created = Dict.objects.get_or_create(instance=self.instance, name=self.name, key=key)
        item.set_data(value)
        #item.save()
 
    def __delitem__(self, key):
        try:
            self.get_query_set().get(key=key).delete()
        except Dict.DoesNotExist:
            raise KeyError(key)
 
    def update(self, d):
        for k,v in d.iteritems():
            self.__setitem__(k, v)
 
    def __iter__(self):
        #return (self.__unpack(x[0]) for x in self.conn.execute('select key from %s;' % TABLE_NAME) )
        return (item.key for item in self.get_query_set())
    
    def keys(self):
        return (item.key for item in self.get_query_set())
    
    def values(self):
        return (item.get_data() for item in self.get_query_set())
    
    def items(self):
        return ((item.key, item.get_data()) for item in self.get_query_set())
    
    def iterkeys(self):
        return self.keys()
    def itervalues(self):
        return self.values()
    def iteritems(self):
        return self.items()
 
    def __contains__(self, key):
        try:
            item = self.get_query_set().get(key=key)
            return True
        except Dict.DoesNotExist:
            return False
 
    def __len__(self):
        return self.get_query_set().count()
    
class DBCountDict(AbstractDBDict):
    model = CountDict
        
    def add_item(self, key, other, count):
        #self.conn.execute('insert into %s (key, other, count) values (?, ?, ?);' % TABLE_NAME, (key, other, count))
        CountDict.objects.create(instance=self.instance, name=self.name,
            key=key, other=other, count=count)
        
    def add_items(self, items):
        #self.conn.executemany('insert into %s (key, other, count) values (?, ?, ?);' % TABLE_NAME, items)
        for key, other, count in items:
            self.add_item(key, other, count)
        
    def add_item_lazy(self, key, other, count):
        self.lazy_items.append((key, other, count))
        
    def add_lazy(self):
        self.add_items(self.lazy_items)
        self.lazy_items = []
        
    def get_list(self, key):
        #cursor = self.conn.execute('select other, count from %s where key=?;' % TABLE_NAME, (key,))
        #return cursor
        return self.get_query_set().filter(key=key).values_list('other', 'count')
        
    def __getitem__(self, key):
        #cursor = self.conn.execute('select other, count from %s where key=?;' % TABLE_NAME, (key,))
        #return dict((other, count) for (other, count) in cursor)
        return dict(self.get_query_set().filter(key=key).values_list('other', 'count'))
    
    def get_sorted(self, key, limit=None):
        #cursor = self.conn.execute('select other, count from %s where key=? order by count desc %s;' % (TABLE_NAME,
        #    ('limit %d' % limit) if limit else ''), (key,))
        #return list(cursor)
        items = self.get_query_set().filter(key=key).order_by('-count').values_list('other', 'count')
        #items = items
        if limit is not None:
            items = items[:limit]
        return list(items)
      
    def relation_count(self):
        #return self.conn.execute('select count(*) from %s;' % TABLE_NAME).fetchone()[0]
        return self.get_query_set().count()
    
    def clear(self):
        #self.conn.execute('delete from %s;' % TABLE_NAME)
        return self.get_query_set().delete()
        
    def get_multiple(self, keys, limit=None):
        items = self.get_query_set().filter(key__in=keys, other__in=keys).exclude(key=F('other'))
        items = items.order_by('-count')
        if limit is not None:
            items = items[:limit]
        return list(items)
        
class DBStringDict(AbstractDBDict):
    model = StringDict
    
    def __init__(self, instance, name, unique=False):
        super(DBStringDict, self).__init__(instance, name)
        self.unique = unique
        
    def add_item(self, key, value):
        #self.conn.execute('insert into %s (key, value) values (?, ?);' % TABLE_NAME, (key, value))
        
        if self.unique:
            StringDict.objects.get_or_create(instance=self.instance, name=self.name, key=key, value=value)
        else:
            StringDict.objects.create(instance=self.instance, name=self.name, key=key, value=value)
        
    def add_items(self, items):
        #self.conn.executemany('insert into %s (key, value) values (?, ?);' % TABLE_NAME, items)
        for key, value in items:
            self.add_item(key, value)
        
    def add_item_lazy(self, key, value):
        self.lazy_items.append((key, value))
        
    def add_lazy(self):
        self.add_items(self.lazy_items)
        self.lazy_items = []
        
    def __getitem__(self, key):
        #cursor = self.conn.execute('select value from %s where key=?;' % TABLE_NAME, (key,))
        #return set(value for (value,) in cursor)
        return set(self.get_query_set().filter(key=key).values_list('value', flat=True))
    
    def clear(self):
        return self.get_query_set().delete()
        