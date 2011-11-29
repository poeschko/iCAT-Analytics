IS_SERVER = True

#BASE_DIR = '/srv/protege/www/vhosts/socialanalysis/icdexplorer/'
#BASE_DIR = '/home/simon/Desktop/WORKINGDIR/iCAT-Analytics/icdexplorer/'
#BASE_DIR = '/Users/Jan/Uni/Stanford/ICD-Python/icdexplorer/'
BASE_DIR = '/home/socialcomp/icdexplorer/'

DEBUG = False

ENABLE_CACHE = IS_SERVER

INSTANCES = ['ictm2011-11-24_04h02m']
INSTANCE = INSTANCES[-1]

IS_NCI = INSTANCE.startswith('nci')
IS_ICTM = INSTANCE.startswith('ictm')

DB_NAME = 'ictm'
DB_USER = 'ictm'
DB_PASSWORD = 'Chah4soh'