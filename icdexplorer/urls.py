"""
ICDexplorer
URL settings.

(c) 2011 Jan Poeschko
jan@poeschko.com
"""

from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^icdexplorer/', include('icdexplorer.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)


urlpatterns = patterns('icd.views',
    (r'^$', 'network'),
    (r'^search/$', 'search'),
    (r'^about/$', 'about'),
    (r'^categories/$', 'categories'),
    (r'^authors/$', 'authors'),
    (r'^properties/$', 'properties'),
    (r'^categories/(?P<name>.+)/$', 'category'),
    (r'^authors/(?P<name>.*)/$', 'author'),
    (r'^properties/(?P<name>.*)/$', 'property'),
    (r'^ajax/graph/$', 'ajax_graph'),
    
)

urlpatterns += patterns('',
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),#, {'template_name': 'myapp/login.html'}),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login'),
)

#if not settings.IS_SERVER:
urlpatterns += patterns('django.views.static',
    (r'^media/(?P<path>.*)$', 'serve', {'document_root': settings.MEDIA_ROOT[:-1], 'show_indexes': True}),
    (r'^favicon.ico$', 'serve', {'document_root': settings.MEDIA_ROOT, 'path': 'favicon.ico'}),
)
