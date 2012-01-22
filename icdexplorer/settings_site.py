IS_SERVER = False

#BASE_DIR = '/srv/protege/www/vhosts/socialanalysis/icdexplorer/'
#BASE_DIR = '/home/simon/Desktop/WORKINGDIR/iCAT-Analytics/icdexplorer/'
#BASE_DIR = '/Users/Jan/Uni/Stanford/ICD-Python/icdexplorer/'
BASE_DIR = 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\icdexplorer\\'
#BASE_DIR = '/var/www/vhosts/simonwalk.at/icd11/icdexplorer/'

DEBUG = True

ENABLE_CACHE = IS_SERVER

if IS_SERVER:
    INSTANCES = ['2011-04-21_04h02m', '2011-06-20_04h02m', '2011-07-28_04h02m', '2011-08-08_04h02m', '2011-08-28_04h02m', '2011-11-24_04h02m']
    INSTANCE = INSTANCES[-1]
    #INSTANCES = ['main']
    #INSTANCE = INSTANCES[0]
else:
    INSTANCES = ['nci100400', 'nci110815',
        
        'icd2011-08-30_04h02m', 
        'icd2011-09-27_04h02m', 
        'icd2011-10-03_04h02m', 
        'icd2011-11-10_04h02m', 'icd2011-11-20_04h02m',
        
        'ictm2011-11-24_04h02m', 'ictm2011-11-30_04h02m', 'ictm2011-12-02_10h00m', 'ictm2011-12-02_11h38m']
    INSTANCE = INSTANCES[6]
IS_NCI = INSTANCE.startswith('nci')
IS_ICTM = INSTANCE.startswith('ictm')
IS_WIKI = INSTANCE.startswith('wiki')
IS_ICD = not IS_NCI and not IS_ICTM and not IS_WIKI 

WIKI_INPUT_DIR = BASE_DIR + '../wiki/randomsample_icd10/'

DB_NAME = 'socialanalysis' if IS_SERVER else 'ictm2' if IS_ICTM else 'icd11'
DB_USER = 'root' if IS_SERVER else 'root'
DB_PASSWORD = '' if IS_SERVER else '8986'
