"""
ICDexplorer
Django settings for icdexplorer project.

(c) 2011 Jan Poeschko
jan@poeschko.com
"""

from settings_site import (IS_SERVER, BASE_DIR, DEBUG, ENABLE_CACHE,
    INSTANCE, IS_NCI, IS_ICTM,
    DB_NAME, DB_USER, DB_PASSWORD)

#IS_SERVER = False

#ENABLE_CACHE = True #IS_SERVER

DEFAULT_CHARSET='utf-8'

"""if IS_SERVER:
    #BASE_DIR = '/apps/bmir.apps/socialanalysis/'
    BASE_DIR = '/srv/protege/www/vhosts/socialanalysis/icdexplorer/'
else:
    #BASE_DIR = '/Users/Jan/Uni/Stanford/ICD-Python/icdexplorer/'
    BASE_DIR = '/home/simon/Desktop/WORKINGDIR/iCAT-Analytics/icdexplorer/'
"""

"""if IS_SERVER:
    INSTANCES = ['2011-04-21_04h02m', '2011-06-20_04h02m', '2011-07-28_04h02m', '2011-08-08_04h02m', '2011-08-28_04h02m', '2011-11-24_04h02m']
    INSTANCE = INSTANCES[-1]
    #INSTANCES = ['main']
    #INSTANCE = INSTANCES[0]
else:
    INSTANCES = ['nci100400', 'nci110815',
        '2010-06-01_04h02m',
        '2011-09-09_04h02m', 'main', 'dynamic_graph', 'main2', '03-10-11', '10-11-11', '2011-11-20_04h02m',
        'ictm2011-11-24_04h02m']
    INSTANCE = INSTANCES[-1]
 
IS_NCI = INSTANCE.startswith('nci')
IS_ICTM = INSTANCE.startswith('ictm')"""
    
INPUT_DIR = BASE_DIR + '../input/'

LAYOUTS = [
    ('Radial', 'twopi', 'twopi'),
    ('Force-directed', 'sfdp', 'sfdp'),
    #('Circular', 'circo'),
]
DEFAULT_LAYOUT = 'twopi'
"""WEIGHTS = [
    ('activity', 'Changes + Notes', lambda c, filter: c.chao.changes.filter(**filter).count() + c.chao.annotations.filter(**filter).count() if c.chao else 0),
    ('changes', 'Changes', lambda c, filter: c.chao.changes.filter(**filter).count() if c.chao else 0),
    ('annotations', 'Notes', lambda c, filter: c.chao.annotations.filter(**filter).count() if c.chao else 0),
]"""
WEIGHTS = [
    ('activity', 'Changes + Notes', lambda changes, annotations: changes + annotations),
    ('changes', 'Changes', lambda changes, annotations: changes),
    ('annotations', 'Notes', lambda changes, annotations: annotations),
]

#DEBUG = True #not IS_SERVER
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Jan Poeschko', 'jan@poeschko.com'),
    ('Simon Walk', 'swalk86@gmail.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': DB_NAME,                      # Or path to database file if using sqlite3.
        'USER': DB_USER,                      # Not used with sqlite3.
        'PASSWORD': DB_PASSWORD,                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

if ENABLE_CACHE:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'icdexplorer-cache',
            'TIMEOUT': 3 * 3600, # 3 hours
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

DATETIME_FORMAT = 'Y-m-d H:i:s'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = False

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = BASE_DIR + 'media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/adminmedia/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'vtly4+0crbp$0@7sea)l@^rowkgdp&(4sty(kpr!lx)f84j!o@'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = (3 * 3600 if ENABLE_CACHE else 1)
CACHE_MIDDLEWARE_KEY_PREFIX = ''

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    #"django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    'django.core.context_processors.request',
)

ROOT_URLCONF = 'icdexplorer.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    BASE_DIR + 'templates',
)

LOGIN_REDIRECT_URL = '/'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    'icdexplorer.icd',
    'icdexplorer.storage',
)
