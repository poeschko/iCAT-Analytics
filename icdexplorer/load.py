"""
Load Wikipedia XML dumps into iCAT Analytics

Make sure the MySQL variable max_allowed_packet is big enough to handle
all the data for a single revision, which is usually bigger than the
default 1 MB.
"""

import sys
import xml.etree.ElementTree as etree
import os
from datetime import datetime

from django.core.management import setup_environ
import settings

setup_environ(settings)

from icd.models import *

datetime_format = '%Y-%m-%dT%H:%M:%SZ' # e.g. 2010-11-07T15:03:06Z

class WikiPage:
    def __init__(self, title, id):
        self.title = title
        self.id = id
        self.revisions = []

class WikiContributor:
    def __init__(self, username = None, id = None, ip = None):
        # contributors are defined by either: (username and id) or (ip)
        self.username = username
        self.id = id
        self.ip = ip
        
    def __unicode__(self):
        if self.ip:
            return self.ip
        return u'%s-%s' % (self.username, self.id)

class WikiRevision:
    def __init__(self, id, timestamp, contributor, text, comment = None):
        self.id = id
        self.timestamp = datetime.strptime(timestamp, datetime_format)
        self.contributor = contributor
        self.text = text
        self.comment = comment

def parse_wiki_dump(file, skip_unless_title=None):
    for event, element in etree.iterparse(file):
        if element.tag == 'page':
            title = element.findtext('title')
            if skip_unless_title is not None and title != skip_unless_title:
                continue
            id = element.findtext('id')
            current_page = WikiPage(title, id)
            revisions = []
            for revision in element.findall('revision'):
                r_id = revision.findtext('id')
                r_timestamp = revision.findtext('timestamp')
                contributor = revision.find('contributor')
                if contributor.find('username') != None:
                    r_c_username = contributor.findtext('username')
                    r_c_id = contributor.findtext('id')
                    r_c = WikiContributor(r_c_username, r_c_id)
                else:
                    r_c_ip = contributor.findtext('ip')
                    r_c = WikiContributor(None, None, r_c_ip)
                if contributor.find('comment') != None:
                    r_comment = revision.findtext('comment')
                else:
                    r_comment = None
                r_text = revision.findtext('text')
                revisions.append(WikiRevision(r_id, r_timestamp,
                                              r_c, r_text, r_comment))
            current_page.revisions = revisions
            yield current_page
            element.clear()

def load_wiki():
    instance = settings.INSTANCE
    
    authors = {}    # cache for Author instances
    skip_until = "Diarrhea" # set to page title or False
    if skip_until:
        print "Delete data for '%s'" % skip_until
        try:
            category = Category.objects.get(instance=instance, name=skip_until)
            for chao in category.chao.all():
                chao.changes.all().delete()
                chao.delete()
            category.delete()
        except Category.DoesNotExist:
            pass
        skipping = True
    else:
        skipping = False    
        print "Delete previous data"
        for model in [Category, OntologyComponent, Author, Change]:
            model.objects.filter(instance=instance).delete()
    
    print "Load new data"
    for dirpath, dirnames, filenames in os.walk(settings.WIKI_INPUT_DIR):
        filenames.sort()
        for filename in filenames:
            if filename.endswith('.xml'):
                print filename
                page_generator = parse_wiki_dump(settings.WIKI_INPUT_DIR + filename,
                    skip_unless_title=skip_until if skipping else None)
                for page in page_generator:
                    print page.title
                    if skipping:
                        if page.title == skip_until:
                            skipping = False
                        if skipping:
                            continue
                    category = Category.objects.create(instance=instance, name=page.title,
                        instance_name=instance + page.title,
                        sorting_label=page.id)
                    comp = OntologyComponent.objects.create(instance=instance, name=page.title,
                        instance_name=instance + page.title,
                        _instance=instance, _name=page.title,
                        type="Page", category=category)
                    old_value = ""
                    for revision in page.revisions:
                        print "  - %s" % revision.id
                        author_name = unicode(revision.contributor)
                        author = authors.get(author_name)
                        if author is None:
                            author, created = Author.objects.get_or_create(instance=instance,
                                name=author_name, instance_name=instance + author_name)
                            authors[author_name] = author
                        change = Change.objects.create(instance=instance, name=revision.id,
                            instance_name=instance + revision.id,
                            _instance=instance, _name=revision.id,
                            type="Revision",
                            author=author,
                            timestamp=revision.timestamp,
                            apply_to=comp,
                            old_value=old_value,
                            new_value=revision.text,
                            additional_info=revision.comment or '',
                            )
                        old_value = revision.text

def main():
    load_wiki()

if __name__ == '__main__':
    main()
