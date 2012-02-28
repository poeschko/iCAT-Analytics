IS_SERVER = False

#BASE_DIR = '/srv/protege/www/vhosts/socialanalysis/icdexplorer/'
#BASE_DIR = '/home/simon/Desktop/WORKINGDIR/iCAT-Analytics/icdexplorer/'
BASE_DIR = '/Users/Jan/Uni/Stanford/ICD-Python/icdexplorer/'

DEBUG = False

ENABLE_CACHE = IS_SERVER

if IS_SERVER:
    INSTANCES = ['2011-04-21_04h02m', '2011-06-20_04h02m', '2011-07-28_04h02m', '2011-08-08_04h02m', '2011-08-28_04h02m', '2011-11-24_04h02m']
    INSTANCE = INSTANCES[-1]
    #INSTANCES = ['main']
    #INSTANCE = INSTANCES[0]
else:
    """INSTANCES = ['nci100400', 'nci110815',
        '2010-06-01_04h02m',
        '2011-09-09_04h02m', 'main', 'dynamic_graph', 'main2', '03-10-11', '10-11-11', '2011-11-20_04h02m',
        'ictm2011-11-24_04h02m', """
    INSTANCES = ['wiki-icd10-sample']
    INSTANCE = INSTANCES[-1]
    
IS_NCI = INSTANCE.startswith('nci')
IS_ICTM = INSTANCE.startswith('ictm')
IS_WIKI = INSTANCE.startswith('wiki')
IS_ICD = not IS_NCI and not IS_ICTM and not IS_WIKI 

WIKI_INPUT_DIR = BASE_DIR + '../wiki/randomsample_icd10/'

#DB_NAME = 'socialanalysis' if IS_SERVER else 'ictm' if IS_ICTM else 'icd'
DB_NAME = 'wiki'
DB_USER = 'root' if IS_SERVER else 'icd'
DB_PASSWORD = '' if IS_SERVER else 'AiX1Ifie'