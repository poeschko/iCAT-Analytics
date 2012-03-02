# -*- coding: UTF-8 -*-

"""
finds relations among the Wikipedia-Articles regarding their ICD-10 short codes
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

import sys
import cPickle as pickle
import random

class CurrentCategory(object):
    
    def __init__(self, cat):
        self.cat = cat
        print cat
        self.line = ""
        self.value = self.get_current_value()
        self.codes = self.get_codes()
        self.parents = []
        self.children = []
    
    def get_current_value(self):
        # get the new_value of the most recent change for this category
        return Change.objects.filter(apply_to = self.cat.instance_name).order_by('-timestamp')[:1].get().new_value.encode('utf-8')
    
    def get_codes(self):
        # get the codes corresponding to this category's most recent revision
        # this has handling for a lot of possible errors/specials cases
        # any remaining errors are treated as special cases in assign_special_cases()
        all_codes = []
        original_line = ""
        for line in self.value.split('\n'):
            if ("ICD10" in line and "=" in line) or ("ICD10" in line and "DiseasesDB" in line):
                self.line = ''.join(line)
                line = line[line.find("ICD10"):]
                line = line[line.find("=")+1:].replace('.','|').replace('}}{{', '}},{{')
                for wp_code in line.split(','): # split by comma to get several codes, if present
                    codes = []
                    wp_code = wp_code.strip()
                    if "ICD10" in wp_code and "{" in wp_code:
                        if ('–' in wp_code or '-' in wp_code) and not "<!--" in wp_code and not "(" in wp_code: # we have a range (e.g. "E10 - E14")
                            wp_code.replace('–', '-') # different sorts of dashes
                            range = wp_code.split('-')
                            start = range[0].strip("{}ICD10,").rstrip('|').split('|')[1:]
                            end = range[1].strip("{}ICD10,").rstrip('|').split('|')[1:]
                            if start[-1] == '':
                                start = start[:-1]
                            if len(end) > 1 and end[-1] == '':
                                end = end[:-1]
                                
                            if ('' in start and not '' in end) or ('' in end and not '' in start):
                                #print "Range error: Codes of different length ", start, " ", end
                                continue
                                #sys.exit(0)
                            if '' in start: # we have a code with two levels (e.g. "E.20")
                                positions = 2
                            else: # we have a code with three levels (e.g. "E.20.2")
                                positions = 3
                            try:
                                if start[positions-2] != end[positions-2]:
                                    #print "Range error: Invalid range ", start, " ", end
                                    continue
                            except IndexError, ie:
                                #print "IndexError ", str(ie)
                                continue
                            icd_code = [c for c in start[:positions]]
                            if icd_code[1][0] == '0' and len(icd_code[1]) > 1:
                                icd_code[1] = icd_code[1][1]
                            if positions == 3 and icd_code[2][0] == '0' and len(icd_code[2]) > 1:
                                icd_code[2] = icd_code[2][1]
                            start = icd_code
                            end = [c for c in end[:positions]]
                            # generate every code in the range
                            for c in xrange(int(start[-1]),int(end[-1])+1):
                                code = [e for e in start]
                                code[-1] = str(c)
                                codes.append(code)
                        else:
                            wp_code = wp_code.strip("{}ICD10,").rstrip('|').split('|')[1:]
                            if wp_code[-1] == '':
                                wp_code = wp_code[:-1]
                            if len(wp_code) == 1:
                                wp_code.append('')
                            if '' in wp_code or len(wp_code) == 2: # we have a code with two levels (e.g. "E.20")
                                positions = 2
                            else: # we have a code with three levels (e.g. "E.20.2")
                                positions = 3
                            icd_code = [c for c in wp_code[:positions]]
                            if icd_code[1] != '' and icd_code[1][0] == '0' and len(icd_code[1]) > 1:
                                icd_code[1] = icd_code[1][1]
                            if positions == 3 and icd_code[2][0] == '0' and len(icd_code[2]) > 1:
                                icd_code[2] = icd_code[2][1]
                            if len(icd_code) == 2 and icd_code[1] == '':
                                icd_code = icd_code[0]
                                print self.cat, " - ", icd_code
                            codes.append(icd_code)
                        all_codes.append(codes)
                return all_codes
    
def connect(a, b, categories):
    # connects two CurrentCategory objects given their category names
    node = None
    for c in categories:
        if c.cat.name == a:
            node = c
            break

    for c in categories:
        if c.cat.name == b:
            c.parents = [[node]]
            break
    return categories
    
def code_range(start, end):
    # generates a code range of icd-10 codes
    if len(start) == len(end):
        codes = []
        for c in xrange(int(start[-1]), int(end[-1])+1):
            code = [e for e in start]
            code[-1] = str(c)
            codes.append(code)
        return codes
    else:
        print "code_range: Error! invalid range ", start, end

def find_code_ranges(codelist):
    # a code range would be written as e.g., "A12-A15" and hence be identified as such by this program
    # code ranges might also occur as e.g., "A12, A13, A14, A15", which would evaluate to four separate code ranges
    # we're fixing this here
    
    # first, let's consider only code ranges of length one
    relevant_ranges = []
    irrelevant_ranges = []
    for coderange in codelist:
        if len(coderange) == 1:
            relevant_ranges.append(coderange)
        else:
            irrelevant_ranges.append(coderange)
    
    # now let's unify ranges, if possible
    unified_ranges = []
    for index1, coderange1 in enumerate(relevant_ranges):
        for index2, coderange2 in enumerate(relevant_ranges):
            if index1 < index2:
                code1 = next(iter(coderange1)) # these sets have only one element
                code2 = next(iter(coderange2))
                if adjacent_ranges(code1, code2):
                    added = False
                    for range in unified_ranges:
                        if (adjacent_ranges(max(range), code1) or adjacent_ranges(min(range), code1)) and not code1 in range:
                            range.add(code1)
                            added = True
                        elif adjacent_ranges(max(range), code2) or adjacent_ranges(min(range), code2) and not code2 in range:
                            range.add(code2)
                            added = True
                    if not added:
                        unified_ranges.append(set([tuple(code1), tuple(code2)]))

    non_unified_ranges = []
    if unified_ranges == []:
        non_unified_ranges = relevant_ranges
    else:
        for coderange1 in relevant_ranges:
            present = False
            for coderange2 in unified_ranges:
                if next(iter(coderange1)) in coderange2:
                    present = True
                if next(iter(coderange1)) in non_unified_ranges:
                    present = True
            if not present:
                non_unified_ranges.append(coderange1)
                
                
    
    return_list = irrelevant_ranges + unified_ranges + non_unified_ranges
    return return_list

def adjacent_ranges(range1, range2):
    # finds out if two given code ranges are adjacent
    le1 = len(range1)
    if le1 == len(range2):
        if range1[0] == range2[0]:
            if (le1 == 3 and range1[1] == range2[1]) or (le1 == 2):
                if int(range1[le1-1]) == int(range2[le1-1]) + 1 or int(range1[le1-1]) == int(range2[le1-1]) - 1:
                    return True
    return False                    
        
def save_to_disk(categories):
    print "saving to disk..."
    file = open('categories.obj', 'wb+')
    pickle.dump(categories, file, 2)
    file.close()
    print "done saving"

def load_from_disk():
    print "loading from disk"
    file = open('categories.obj', 'rb')
    c = pickle.load(file)
    file.close()
    print "loaded"
    return c

def assign_special_cases(categories):
    # assigns icd codes to special cases that could not be parsed automatically
    d = {}

    # define codes for chapters
    l = code_range(['A', '0'], ['A', '99'])
    m = code_range(['B', '0'], ['B', '99'])
    d['Infectious disease'] = [l, m]
    l = code_range(['C', '0'], ['C', '99'])
    m = code_range(['D', '0'], ['D', '48'])
    d['Neoplasm'] = [l, m]
    d['ICD-10 Chapter III: Diseases of the blood and blood-forming organs, and certain disorders involving the immune mechanism'] = [code_range(['D', '50'], ['D', '99'])]
    d['ICD-10 Chapter IV: Endocrine, nutritional and metabolic diseases'] = [code_range(['E', '0'], ['E', '90'])]
    d['Mental disorder'] = [code_range(['F', '0'], ['F', '99'])]
    d['Nervous system disease'] = [code_range(['G', '0'], ['G', '99'])]
    d['ICD-10 Chapter VII: Diseases of the eye, adnexa'] = [code_range(['H', '0'], ['H', '59'])]
    d['Ear disease'] = [code_range(['H', '60'], ['H', '95'])]
    d['ICD-10 Chapter IX: Diseases of the circulatory system'] = [code_range(['I', '0'], ['I', '99'])]
    d['Respiratory Disease'] = [code_range(['J', '0'], ['J', '99'])]
    d['ICD-10 Chapter XI: Diseases of the digestive system'] = [code_range(['K', '0'], ['K', '93'])]
    d['ICD-10 Chapter XII: Diseases of the skin and subcutaneous tissue'] = [code_range(['L', '0'], ['L', '99'])]
    d['ICD-10 Chapter XIII: Diseases of the musculoskeletal system and connective tissue'] = [code_range(['M', '0'], ['M', '99'])]
    d['ICD-10 Chapter XIV: Diseases of the genitourinary system'] = [code_range(['N', '0'], ['N', '99'])]
    d['ICD-10 Chapter XV: Pregnancy, childbirth and the puerperium'] = [code_range(['O', '0'], ['O', '99'])]
    d['ICD-10 Chapter XVI: Certain conditions originating in the perinatal period'] = [code_range(['P', '0'], ['P', '96'])]
    d['ICD-10 Chapter XVII: Congenital malformations, deformations and chromosomal abnormalities'] = [code_range(['Q', '0'], ['Q', '99'])]
    d['ICD-10 Chapter XVIII: Symptoms, signs and abnormal clinical and laboratory findings'] = [code_range(['R', '0'], ['R', '99'])]
    l = code_range(['S', '0'], ['S', '99'])
    m = code_range(['T', '0'], ['T', '98'])
    d['ICD-10 Chapter XIX: Injury, poisoning and certain other consequences of external causes'] = [l, m]
    l = code_range(['V', '1'], ['V', '99'])
    m = code_range(['W', '0'], ['W', '99'])
    n = code_range(['X', '0'], ['X', '99'])
    o = code_range(['Y', '0'], ['Y', '98'])
    d['ICD-10 Chapter XX: External causes of morbidity and mortality'] = [l, m, n, o]
    d['ICD-10 Chapter XXI: Factors influencing health status and contact with health services'] = [code_range(['Z', '0'], ['Z', '99'])]
    d['ICD-10 Chapter XXII: Codes for special purposes'] = [code_range(['U', '0'], ['U', '99'])]
    
    # these will be assigned later
    d['ICD-10 Chapter I: Certain infectious and parasitic diseases'] = []
    d['ICD-10 Chapter II: Neoplasms'] = []
    d['ICD-10 Chapter V: Mental and behavioural disorders'] = []
    d['ICD-10 Chapter X: Diseases of the respiratory system'] = []
    d['ICD-10 Chapter VIII: Diseases of the ear and mastoid process'] = []
    d['ICD-10 Chapter VI: Diseases of the nervous system'] = []
   
   
    # manually assign codes to 22 special cases where errors occurred 
    d['AIDS'] = [[['B', '24']]]
    d['Ego-dystonic sexual orientation'] = [[['F', '66', '1']]]
    d['Hepatorenal syndrome'] = [[['K', '76', '7']]]
    d['Pulmonary aspiration'] = [[['J', '69']], [['J', '95', '4']], [['O', '29', '0']], [['O', '74', '0']], [['O', '89', '0']], [['P', '24']], [['T', '17', '3'], ['T', '17', '4'], ['T', '17', '5'], ['T', '17', '6'], ['T', '17', '7'], ['T', '17', '8'], ['T', '17', '9']]]
    d['Chlamydia infection'] = [[['A', '55'], ['A', '56']], [['A', '70'], ['A', '71'], ['A', '72'], ['A', '73'], ['A', '74']]]
    d['Colitis'] = [[['K', '50'], ['K', '51'], ['K', '52']]]
    d["Colles' fracture"] = [[['S', '52', '5']]]
    d['Dermatophytosis'] = [[['B', '35'], ['B', '36']]]
    d['Enthesopathy'] = [[['M', '76'], ['M', '77']]]
    d['Food intolerance'] = [[['K', '90', '4']], [['Z', '71', '3']]]
    d['Gastritis'] = [[['K', '29', '0'], ['K', '29', '1'], ['K', '29', '2'], ['K', '29', '3'], ['K', '29', '4'], ['K', '29', '5'], ['K', '29', '6'], ['K', '29', '7']]]
    d['HPV-positive oropharyngeal cancer'] = [[['C', '9'], ['C', '10']], [['C', '1']], [['C', '2', '4']], [['C', '14', '2']]]
    d['Hyperphenylalanemia'] = [[['E', '70', '1']]]
    d['Ileitis'] = [[['K', '50'], ['K', '51'], ['K', '52']]]
    d['Infestation'] = [code_range(['B', '65'], ['B', '88'])]
    d['Intracranial hemorrhage'] = [[['I', '60'], ['I', '61'], ['I', '62']], [['S', '6']]]
    d['Multicystic dysplastic kidney'] = [[['Q', '61', '4']]]
    d['Occipital neuralgia'] = [[['G', '52', '8']], [['R', '51']]]
    d['Parkinsonism'] = [[['G', '20'], ['G', '21']]]
    d['Retinopathy'] = [[['H', '35', '0'], ['H', '35', '1'], ['H', '35', '2']]]
    d['Upper respiratory tract infection'] = [[['J', '0'], ['J', '1'], ['J', '2'], ['J', '3'], ['J', '4'], ['J', '5'], ['J', '6']], [['J', '30'], ['J', '31'], ['J', '32'], ['J', '33'], ['J', '34'], ['J', '35'], ['J', '36'], ['J', '37'], ['J', '38'], ['J', '39']]]
    d['Shock (circulatory)'] = [[['R', '57']]]
    
    # 130 additional corrections as of 2012-03-01
    d['Acrochordon'] = [[['L', '91', '8']], [['Q', '82', '8']]]
    d['Aicardi syndrome'] = [[['G', '93', '8']]]
    d['Alcohol dependence'] = [[['F', '10', '2']]]
    d['Alcoholism']  = [[['F', '10', '2']]]
    d['Amnesia'] = [[['R', '41', '3']], [['F', '4']]]
    d['Amphetamine dependence'] = [[['F', '15', '2']]]
    d['Arcuate uterus'] = [[['Q', '51', '9']]]
    d['Arteritis'] = [[['I', '77', '6']], [['M', '31']]]
    d['Argyria'] = [[['T', '56', '8']], [['L', '81', '8']]]
    d['Ballistic trauma'] = [[['T', '14', '1']], [['X', '95']], [['W', '34']]]
    d['Barbiturate dependence'] = [[['F', '13', '2']]]
    d['Barbiturate overdose'] = [[['F', '13', '0']], [['T', '42', '3']]]
    d['Benzodiazepine dependence'] = [[['F', '13', '2']]]
    d['Benzodiazepine overdose'] = [[['F', '13', '0']], [['T', '42', '4']]]
    d['Benzodiazepine withdrawal syndrome'] = [[['F', '13', '3']]]
    d['Birth trauma (physical)'] = [code_range(['P', '10'], ['P', '15'])]
    d['Breech birth'] = [[['O', '32', '1']], [['O', '64', '1']], [['O', '80', '1']], [['O', '83', '0']], [['P', '3', '0']]]
    d['Calcific tendinitis'] = [[['M', '65', '2']], [['M', '75', '3']]]
    d['Cannabis dependence'] = [[['F', '12', '2']]]
    d['Cannabis withdrawal'] = [[['F', '12', '3']]]
    d['Capillary hemangioma'] = [[['Q', '82', '5']], [['D', '18', '0']]]
    d["Caplan's syndrome"] = [[['J', '99', '0']], [['M', '5', '1']]]
    d["Carrion's disease"] = [[['A', '44', '0']]]
    d['Cephalic presentation'] = [[['O', '80', '0']]]
    d['Chickenpox'] = [[['B', '1']]]
    d['Childhood obesity'] = [[['E', '66']]]
    d['Cocaine dependence'] = [[['F', '14', '2']]]
    d['Colorectal cancer'] = [[['C', '18'], ['C', '19'], ['C', '20']], [['C', '21']]]
    d['Contracture'] = [[['M', '24', '5']], [['M', '62', '4']], [['T', '79', '6']], [['M', '67', '1']], [['M', '72', '0']]]
    d['Dermatochalasis'] = [[['H', '2', '3']], [['Q', '10', '0']]]
    d['Dermatomyositis'] = [[['M', '33', '0'], ['M', '33', '1']]]
    d['Diabetes insipidus'] = [[['E', '23', '2']], [['N', '25', '1']]]
    d['Diabetes mellitus'] = [code_range(['E', '10'], ['E', '14'])]
    d['Diabetic retinopathy'] = [[['H', '36']], [['E', '10', '3']], [['E', '11', '3']], [['E', '12', '3']], [['E', '13', '3']], [['E', '14', '3']]]
    d['Digestive system neoplasm'] = [code_range(['C', '15'], ['C', '26']), code_range(['D', '12'], ['D', '13'])]
    d['Disease theory of alcoholism'] = [[['F', '10', '2']]]
    d['Drug-induced lupus erythematosus'] = [[['M', '32', '0']]]
    d['Dysbarism'] = [[['T', '70']]]
    d['Dysuria'] = [[['R', '30', '0']]]
    d['Ectopia cordis'] = [[['Q', '24', '8']]]
    d['Effects of cannabis'] = [[['F', '12', '0']]]
    d['Elephantiasis'] = [[['B', '74', '0']], [['I', '89']]]
    d['Emotional and behavioral disorders'] = [code_range(['F', '90'], ['F', '98'])]
    d['Encopresis'] = [[['R', '15']], [['F', '98', '1']]]
    d['Endocrine gland neoplasm'] = [[['C', '73'], ['C', '74'], ['C', '75']], [['D', '34'], ['D', '35']]]
    d['Erythroderma'] = [[['L', '26']], [['L', '53', '9']]]
    d['Facial trauma'] = [[['S', '0']], code_range(['S', '2', '2'], ['S', '2', '9'])]
    d['Focal segmental glomerulosclerosis'] = [[['N','0', '1']], [['N','0', '2']], [['N','0', '3']], [['N','0', '4']], [['N','0', '5']], [['N','0', '6']], [['N','0', '7']], [['N','0', '8']]]
    d['Folate deficiency'] = [[['D', '52']], [['E', '53', '8']]]
    d['Gender identity disorder'] = [[['F', '64', '8']], [['F', '64', '9']]]
    d['Gender identity disorder in children'] = [[['F', '64', '2']]]
    d['Gitelman syndrome'] = [[['N', '25', '8']], [['E', '87', '6']], [['E', '83', '4']]]
    d['Gumma (pathology)'] = [[['A', '52', '3']], [['A', '52', '7']]]
    d['Hallucinogen persisting perception disorder'] = [[['F', '16', '7']]]
    d['Halo nevus'] = [[['I', '78', '1']], [['D', '22']]]
    d['Head and neck cancer'] = [code_range(['C', '7'], ['C', '14']), code_range(['C', '32'], ['C', '33'])]
    d['Hepatomegaly'] = [[['R', '16', '0']]]
    d['Hyperemesis gravidarum'] = [[['O', '21', '1']]]
    d['Hypertrichosis'] = [[['L', '68']], [['Q', '84', '2']]]
    d['Hypertrophic cardiomyopathy'] = [[['I', '42', '1']], [['I', '42', '2']]]
    d['Hypogonadism'] = [[['E', '28', '3']], [['E', '29', '1']], [['E', '23', '0']]]
    d['Inhalant abuse'] = [[['F', '18', '1']], [['T', '52']], [['T', '53']]]
    d['Insect bites and stings'] = [[['T', '14', '1']], code_range(['X', '23'],['X', '25']), [['W', '57']]]
    d['Interstitial pregnancy'] = [[['O', '0', '8']]]
    d['Iodine deficiency'] = [code_range(['E', '0'], ['E', '2'])]
    d['Kidney stone'] = [[['N', '20', '0']], [['N', '20', '9']]]
    d['Leiomyosarcoma'] = [[['C', '49']], [['M', '48']]]
    d['Leptospirosis'] = [[['A', '27']]]
    d['Long-term effects of benzodiazepines'] = [[['F', '13', '1']]]
    d['Membranoproliferative glomerulonephritis'] = [[['N', '0', '5']], [['N', '1', '5']], [['N', '2', '5']], [['N', '3', '5']], [['N', '4', '5']], [['N', '5', '5']], [['N', '6', '5']], [['N', '7', '5']], [['N', '8', '5']], [['N', '0', '6']], [['N', '1', '6']], [['N', '2', '6']], [['N', '3', '6']], [['N', '4', '6']], [['N', '5', '6']], [['N', '6', '6']], [['N', '7', '6']], [['N', '8', '6']]]
    d['Membranous glomerulonephritis'] = [[['N', '3', '2']]]
    d['Meningitis'] = [code_range(['G', '0'], ['G', '3'])]
    d['Minimal change disease'] = [[['N', '0', '0'], ['N', '1', '0'], ['N', '2', '0'], ['N', '3', '0'], ['N', '4', '0'], ['N', '5', '0'], ['N', '6', '0'], ['N', '7', '0'], ['N', '8', '0']]]
    d['Morning sickness'] = [[['O', '21', '0']]]
    d['Movement disorder'] = [[['R', '25']], [['F', '44', '4']], [['F', '98', '4']], [['G', '25', '8'], ['G', '25', '9']]]
    d['Myocardial rupture'] = [[['I', '23', '3'], ['I', '23', '4'], ['I', '23', '5']], [['S', '26', '8']]]
    d['Myxoma'] = [[['D', '21', '9']]]
    d['Nervous system neoplasm'] = [[['C', '69'], ['C', '70'], ['C', '71'], ['C', '72']], code_range(['D', '31'], ['D', '33'])]
    d['Nicotine poisoning'] = [[['F', '17', '0']], [['T', '65', '2']]]
    d['Nicotine withdrawal'] = [[['F', '17', '2']]]
    d['Nystagmus'] = [[['H', '55']], [['H', '81', '4']]]
    d['Obesity'] = [[['E', '66']]]
    d['Ocular albinism type 1'] = [[['E', '70', '3']]]
    d['Opioid dependence'] = [[['F', '11', '2']]]
    d['Opioid overdose'] = [[['F', '11', '0']], [['T', '40', '0'], ['T', '40', '1'], ['T', '40', '2']]]
    d['Oropharyngeal squamous cell carcinomas'] = [[['C', '9'], ['C', '10']], [['C', '1']], [['C', '2', '4']], [['C', '5', '1']]]
    d['Otalgia'] = [[['H', '60']], [['H', '65']], [['H', '66']], [['H', '92']]]
    d['Palmoplantar keratoderma'] = [[['L', '85', '1'], ['L', '85', '2']], [['Q', '82', '8']]]
    d['Pancreatitis'] = [[['K', '85']], [['K', '86', '0'], ['K', '86', '1']]]
    d['Pelvic pain'] = [[['R', '10', '2']]]
    d['Peptic ulcer'] = [code_range(['K', '25'], ['K', '27'])]
    d['Periorbital cellulitis'] = [[['L', '1', '1']], [['H', '5', '0']]]
    d['Pigeon toe'] = [[['Q', '66', '2']], [['M', '20', '5']]]
    d['Pinealoma'] = [[['D', '44', '5']], [['C', '75', '3']]]
    d['Pneumatosis intestinalis'] = [[['R', '93', '3']], [['K', '63', '8']]]
    d['Postherpetic neuralgia'] = [[['G', '53', '0']], [['B', '0', '2']]]
    d['Postpartum psychosis'] = [[['F', '53', '0']]]
    d['Proliferating angioendotheliomatosis'] = [[['D', '21']], [['C', '83', '3']]]
    d['Prostatitis'] = [[['N', '41']]]
    d['Pyometra'] = [[['N', '71']], [['O', '85']]]
    d['Ramsay Hunt syndrome type II'] = [[['B', '2', '2']], [['G', '53']]]
    d['Rapidly progressive glomerulonephritis'] = [[['N', '0', '7']], [['N', '1', '7']],[['N', '2', '7']],[['N', '3', '7']],[['N', '4', '7']],[['N', '5', '7']],[['N', '6', '7']],[['N', '7', '7']],[['N', '8', '7']]]
    d['Recurrent corneal erosion'] = [[['H', '16', '0']], [['H', '18', '4']]]
    d['Respiratory tract neoplasm'] = [[['C', '32'], ['C', '33'], ['C', '34']], [['D', '14']]]
    d['Rickets'] = [[['E', '55']]]
    d['Sepsis'] = [code_range(['A', '40'], ['A', '41'])]
    d['Shoulder presentation'] = [[['O', '64', '4']]]
    d['Small fiber peripheral neuropathy'] = [[['G', '63', '3']], [['G', '60', '8']], [['G', '62', '8']]]
    d['Smallpox'] = [[['B', '3']]]
    d['Snakebite'] = [[['T', '63', '0']], [['T', '14', '1']], [['W', '59']], [['X', '20']]]
    d['Spider bite'] = [[['T', '14', '1']], [['T', '63', '3']], [['W', '57']], [['X', '21']]]
    d['Stimulant psychosis'] = [[['F', '15', '5']]]
    d['Substance abuse'] = [[['F', '10', '1']], [['F', '11', '1']], [['F', '12', '1']], [['F', '13', '1']], [['F', '14', '1']], [['F', '15', '1']], [['F', '16', '1']], [['F', '17', '1']], [['F', '18', '1']], [['F', '19', '1']]]
    d['Substance dependence'] = [[['F', '10', '2']], [['F', '11', '2']], [['F', '12', '2']], [['F', '13', '2']], [['F', '14', '2']], [['F', '15', '2']], [['F', '16', '2']], [['F', '17', '2']], [['F', '18', '2']], [['F', '19', '2']]]
    d['Substance intoxication'] = [[['F', '10', '0']], [['F', '11', '0']], [['F', '12', '0']], [['F', '13', '0']], [['F', '14', '0']], [['F', '15', '0']], [['F', '16', '0']], [['F', '17', '0']], [['F', '18', '0']], [['F', '19', '0']]]
    d['Substance use disorder'] = [[['F', '10', '1']], [['F', '11', '1']], [['F', '12', '1']], [['F', '13', '1']], [['F', '14', '1']], [['F', '15', '1']], [['F', '16', '1']], [['F', '17', '1']], [['F', '18', '1']], [['F', '19', '1']], [['F', '10', '2']], [['F', '11', '2']], [['F', '12', '2']], [['F', '13', '2']], [['F', '14', '2']], [['F', '15', '2']], [['F', '16', '2']], [['F', '17', '2']], [['F', '18', '2']], [['F', '19', '2']]]
    d['Substance-induced psychosis'] = [[['F', '10', '5']], [['F', '11', '5']], [['F', '12', '5']], [['F', '13', '5']], [['F', '14', '5']], [['F', '15', '5']], [['F', '16', '5']], [['F', '17', '5']], [['F', '18', '5']], [['F', '19', '5']]] 
    d['Suicide'] = [code_range(['X', '60'], ['X', '84'])]
    d['Temporal lobe epilepsy'] = [[['G', '40', '1'], ['G', '40', '2']]]
    d['Trisomy'] = [[['Q', '90'], ['Q', '91'], ['Q', '92']], [['Q', '97'], ['Q', '98']]]
    d['Tuberculosis'] = [code_range(['A', '15'], ['A', '19'])]
    d['Unicornuate uterus'] = [[['Q', '51', '4']]]
    d['Urogenital neoplasm'] = [code_range(['C', '50'], ['C', '68']), code_range(['D', '24'], ['D', '30'])]
    d['Uterus didelphys'] = [[['Q', '51', '1']]]
    d['Uveitis'] = [[['H', '20']]]
    d['VIPoma'] = [[['C', '25', '4']], [['E', '16', '8']]]
    d['Vulvar cancer'] = [[['C', '51', '9']]]
    d['Wart'] = [[['B', '7']]]
    d['Withdrawal'] = [[['F', '10', '3']], [['F', '11', '3']], [['F', '12', '3']], [['F', '13', '3']], [['F', '14', '3']], [['F', '15', '3']], [['F', '16', '3']], [['F', '17', '3']], [['F', '18', '3']], [['F', '19', '3']]]
    
    for c in categories:
        if c.cat.name in d:
            c.codes = d[c.cat.name]
    
    return categories

def connect_special_cases(categories):
    categories = connect('ICD-10 Chapter I: Certain infectious and parasitic diseases', 'Infectious disease', categories)
    categories = connect('ICD-10 Chapter II: Neoplasms', 'Neoplasm', categories)
    categories = connect('ICD-10 Chapter V: Mental and behavioural disorders', 'Mental disorder', categories)
    categories = connect('ICD-10 Chapter X: Diseases of the respiratory system', 'Respiratory disease', categories)
    categories = connect('ICD-10 Chapter VIII: Diseases of the ear and mastoid process', 'Ear disease', categories)
    categories = connect('ICD-10 Chapter VI: Diseases of the nervous system', 'Nervous system disease', categories)
    return categories
    
def save_to_db():
    categories = load_from_disk()
    
    # let's empty all parent-child relations first...
    for c in categories:
        for p in c.parents:
            c.parents.remove(p)
    
    # now let's add the relations we found
    for c in categories:
        print c.cat
        for prange in c.parents:
            for p in prange:
                c.cat.parents.add(p.cat)
      
def main():
    """
    # retrieve the required objects from the database
    categories = [CurrentCategory(c) for c in Category.objects.all()]
    save_to_disk(categories)
    """
 
    categories = load_from_disk()
    
    # manually define some codes for special cases
    categories = assign_special_cases(categories)
        
    # convert codes to tuples to be able to work with sets
    for c in categories:
        tcodes = []
        for coderange in c.codes:
            tcoderanges = []
            for codes in coderange:
                tcoderanges.append(tuple(codes))
            tcodes.append(set(tcoderanges))
        c.codes = tcodes
    
    # add empty children and parent lists
    for c in categories:
        num_ranges = len(c.codes)
        c.parents = [set() for dummy in range(num_ranges)]
        c.pcl = ['' for dummy in range(num_ranges)] # code lengths of the relevant code ranges of the parents
        c.children = [set() for dummy in range(num_ranges)]

    # link root and chapter nodes
    root = None
    for c in categories:
        if c.cat.instance_name == "wiki-icd10ICD-10":
            root = c
            break
            
    for c in categories:
        if "Chapter" in c.cat.instance_name:
            c.parents.append([root])
    
    for c in categories:
        c.codes = find_code_ranges(c.codes)
    
    categories = categories
    categories2 = categories
    
    # loop 1: look for supersets of categories on the same level (i.e. "X.X" and "Y.Y", but not "X.X" and "Y.Y.Y")
    for cix, c in enumerate(categories):
        for dix, d in enumerate(categories):
            if dix > cix:
                for cindex, ccode in enumerate(c.codes):
                    for dindex, dcode in enumerate(d.codes):
                        if ccode < dcode:
                            if len(c.parents[cindex]) == 0 or len(dcode) < c.pcl[cindex]:
                                c.parents[cindex] = [d]
                                c.pcl[cindex] = len(dcode)
                            elif len(dcode) == c.pcl[cindex]:
                                c.parents[cindex].append(d)
                        if dcode < ccode:
                            if len(d.parents[dindex]) == 0 or len(ccode) < d.pcl[dindex]:
                                d.parents[dindex] = [c]
                                d.pcl[dindex] = len(ccode)
                            elif len(ccode) == d.pcl[dindex]:
                                d.parents[dindex].append(c)     
       
    
    
    # loop 2: look for supersets of categories as in "X.X.X" and "Y.Y"
    for cix, c in enumerate(categories2):
        for dix, d in enumerate(categories2):
            if dix > cix:
                for cindex, ccode in enumerate(c.codes):
                    ccode_shortened = set(tuple([random.sample(ccode, 1)[0][:-1]]))
                    for dindex, dcode in enumerate(d.codes):
                        if ccode_shortened <= dcode: # here we allow for set equality, since the code "E10.2" is shortened to "E10" and may thus be legally contained in "E10"
                            if len(c.parents[cindex]) == 0 or len(dcode) < c.pcl[cindex]:
                                c.parents[cindex] = [d]
                                c.pcl[cindex] = len(dcode)
                            elif len(dcode) == c.pcl[cindex]:
                                c.parents[cindex].append(d)
                        dcode = set(tuple([random.sample(dcode, 1)[0][:-1]]))
                        if dcode <= ccode:
                            if len(d.parents[dindex]) == 0 or  len(ccode) < d.pcl[dindex]:
                                d.parents[dindex] = [c]
                                d.pcl[dindex] = len(ccode)
                            elif len(ccode) == d.pcl[dindex]:
                                d.parents[dindex].append(c)                     
    
    # assign parents from loop 2, if loop 1 found none
    for cix, c in enumerate(categories):
        for dix, d in enumerate(categories2):
            for cindex, ccode in enumerate(c.codes):
                for dindex, dcode in enumerate(d.codes):
                    if c.parents[cindex] == '':
                        if d.parents[dindex] != '':
                            c.parents[cindex] = d.parents[dindex]
                                                  
                    
    # delete multiple instances of the same parent for a node
    for cix, c in enumerate(categories):
        new_c_parents = []
        for pcindex, pc in enumerate(c.parents):
            found = False
            for pdindex, pd in enumerate(c.parents):
                if pcindex > pdindex and pc == pd:
                    found = True
                    break
            if not found and pc not in new_c_parents:
                new_c_parents.append(pc)
        c.parents = new_c_parents
                        
                    
    
    # connect special cases
    categories = connect_special_cases(categories)
    
    #save_to_disk(categories)

    # print for debugging
    print "Debugging"
    for c in categories:
        if len(c.parents) > 1 and len(c.parents[0]) > 0 and len(c.parents[1]) > 0:
            print c.cat.name.encode('utf-8')
            #print c.line
            print c.codes
            print "--------"
            
            print "Parents: "
            #print c.parents
            for d in c.parents:
                if d:
                    for e in d:
                        print e.cat.name.encode('utf-8'), e.codes
                    print
            print
        
    
    """
    categories = load_from_disk()
    # print for debugging
    print "Debugging"
    for c in categories:
        print c.cat.name.encode('utf-8')
        print c.line
        print c.codes
        print "--------"
        
        print "Parents: "
        #print c.parents
        for d in c.parents:
            if d:
                for e in d:
                    print e.cat.name.encode('utf-8'), e.codes
                print
        print
    """
    """
    # write to database
    # save_to_db() # let's think about how we deal with things as "A10, A11, A12" and "A10-A12" first...
    """

if __name__ == '__main__':
    main()

    """
    some test cases...
    assert  find_code_ranges([set([('A', '1')]), set([('A', '2')])]) == [set([('A', '1'), ('A', '2')])]
    assert  find_code_ranges([set([('A', '1')]), set([('A', '3')])]) == [set([('A', '1')]), set([('A', '3')])]
    assert  find_code_ranges([set([('A', '1', '0')]), set([('A', '1', '1')])]) == [set([('A', '1', '0'), ('A', '1', '1')])]
    assert  find_code_ranges([set([('A', '1', '0')]), set([('A', '2', '3')])]) == [set([('A', '1', '0')]), set([('A', '2', '3')])]
    assert  find_code_ranges([set([('A', '1')]), set([('A', '2')]), set([('A', '4')]), set([('A', '3')])]) == [set([('A', '2'), ('A', '1'), ('A', '4'), ('A', '3')])]
    assert  find_code_ranges([set([('A', '1'), ('A', '2')]),  set([('A', '4')]), set([('A', '3')])]) == [set([('A', '2'), ('A', '1')]), set([('A', '4'), ('A', '3')])]
    assert  find_code_ranges([set([('A', '1'), ('A', '2')]),  set([('A', '4')])]) == [set([('A', '2'), ('A', '1')]), set([('A', '4')])]
    
    print "all tests passed"
    """
