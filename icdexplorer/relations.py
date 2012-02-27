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
        #print cat
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
        # all errors are treated as special cases in main()
        all_codes = []
        original_line = ""
        for line in self.value.split('\n'):
            if ("ICD10" in line and "=" in line) or ("ICD10" in line and "DiseasesDB" in line):
                #print "\n-------------------------"
                #print line
                line = line[line.find("ICD10"):]
                line = line[line.find("=")+1:].replace('.','|').replace('}}{{', '}},{{')
                for wp_code in line.split(','): # split by comma to get several codes, if present
                    codes = []
                    wp_code = wp_code.strip()
                    #print "wp_code 0 ", wp_code
                    if "ICD10" in wp_code and "{" in wp_code:
                        if ('–' in wp_code or '-' in wp_code) and not "<!--" in wp_code and not "(" in wp_code: # we have a range (e.g. "E10 - E14")
                            wp_code.replace('–', '-') # different sorts of dashes
                            #print "range - ", wp_code
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
                                    #sys.exit(0)
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
                            #print "wp_code 1 ", wp_code
                            wp_code = wp_code.strip("{}ICD10,").rstrip('|').split('|')[1:]
                            if wp_code[-1] == '':
                                wp_code = wp_code[:-1]
                            if len(wp_code) == 1:
                                wp_code.append('')
                            #print "wp_code 2 ", wp_code
                            if '' in wp_code or len(wp_code) == 2: # we have a code with two levels (e.g. "E.20")
                                positions = 2
                            else: # we have a code with three levels (e.g. "E.20.2")
                                positions = 3
                            icd_code = [c for c in wp_code[:positions]]
                            #print "icd_code ", icd_code
                            #print line
                            #print icd_code
                            if icd_code[1] != '' and icd_code[1][0] == '0' and len(icd_code[1]) > 1:
                                icd_code[1] = icd_code[1][1]
                            if positions == 3 and icd_code[2][0] == '0' and len(icd_code[2]) > 1:
                                icd_code[2] = icd_code[2][1]
                            if len(icd_code) == 2 and icd_code[1] == '':
                                icd_code = icd_code[0]
                                print self.cat, " - ", icd_code
                            codes.append(icd_code)
                        all_codes.append(codes)
                #print line
                #print all_codes
                #print "-----------------\n"
                return all_codes
    
def connect(a, b, categories):
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

def save_to_disk(obj):
    print "saving to disk..."
    file = open('categories.obj', 'w+')
    pickle.dump(obj, file)
    file.close()
    print "done saving"

def load_from_disk():
    print "loading from disk"
    file = open('categories.obj', 'r')
    c = pickle.load(file)
    file.close()
    print "loaded"
    return c

       
def main():
    """
    # get all categories with their current values
    categories = [CurrentCategory(c) for c in Category.objects.all()]
    """
    categories = load_from_disk()
    # manually define some codes for special cases
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
    
    #
    d['ICD-10 Chapter I: Certain infectious and parasitic diseases'] = []
    d['ICD-10 Chapter II: Neoplasms'] = []
    d['ICD-10 Chapter V: Mental and behavioural disorders'] = []
    d['ICD-10 Chapter X: Diseases of the respiratory system'] = []
    d['ICD-10 Chapter VIII: Diseases of the ear and mastoid process'] = []
    d['ICD-10 Chapter VI: Diseases of the nervous system'] = []
   
   
    # manually assign codes to special cases where errors occurred 
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
    
    for c in categories:
        if c.cat.name in d:
            c.codes = d[c.cat.name]
    
    for c in categories:
        if c.codes == []:
            print "empty codes - ", c.cat
    
    # convert codes to tuples to be able to work with sets
    for c in categories:
        #print c.cat
        #print c.codes
        tcodes = []
        for coderange in c.codes:
            tcoderanges = []
            for codes in coderange:
                tcoderanges.append(tuple(codes))
            tcodes.append(set(tcoderanges))
        c.codes = tcodes
        #print c.codes

        
    
    
    # add empty children and parent lists
    for c in categories:
        num_ranges = len(c.codes)
        c.parents = [set() for dummy in range(num_ranges)]
        c.parentcodes = set()
        c.pcl = ['' for dummy in range(num_ranges)] # code lenghts of the relevant code ranges of the parents
        c.children = [set() for dummy in range(num_ranges)]

    
    
    
    # link root and chapter nodes
    root = None
    for c in categories:
        if c.cat.instance_name == "wiki-icd10ICD-10":
            root = c
            #print c.cat
            break
            
    for c in categories:
        if "Chapter" in c.cat.instance_name:
            c.parents.append([root])
            #print c.cat
    
    
    categories = categories
    categories2 = categories
    
    # look for supersets of categories on the same level (i.e. "X.X" and "Y.Y", but not "X.X" and "Y.Y.Y")
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
       
    
    
    # look for supersets of categories as in "X.X.X" and "Y.Y"
    for cix, c in enumerate(categories2):
        for dix, d in enumerate(categories2):
            if dix > cix:
                for cindex, ccode in enumerate(c.codes):
                    ccode_shortened = set(tuple([random.sample(ccode, 1)[0][:-1]]))
                    for dindex, dcode in enumerate(d.codes):
                        if ccode_shortened <= dcode:
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
            if not found:
                new_c_parents.append(pc)
        c.parents = new_c_parents
                        
                    
    
    # treat special cases
    categories = connect('ICD-10 Chapter I: Certain infectious and parasitic diseases', 'Infectious disease', categories)
    categories = connect('ICD-10 Chapter II: Neoplasms', 'Neoplasm', categories)
    categories = connect('ICD-10 Chapter V: Mental and behavioural disorders', 'Mental disorder', categories)
    categories = connect('ICD-10 Chapter X: Diseases of the respiratory system', 'Respiratory disease', categories)
    categories = connect('ICD-10 Chapter VIII: Diseases of the ear and mastoid process', 'Ear disease', categories)
    categories = connect('ICD-10 Chapter VI: Diseases of the nervous system', 'Nervous system disease', categories)
    
    save_to_disk(categories)
    sys.exit()
    """
    # print for debugging
    for c in categories:
        print c.cat.name.encode('utf-8')
        print c.codes
        print "Parents: "
        #print c.parents
        for d in c.parents:
            if d:
                for e in d:
                    print e.cat.name.encode('utf-8'), e.codes
                print
        print
    """
    # write to database
    save_to_db()
            
def save_to_db():
    categories = load_from_disk()
    for c in categories:
        print c.cat
        for prange in c.parents:
            for p in prange:
                c.cat.parents.add(p.cat)

    
if __name__ == '__main__':
    #main()
    save_to_db()
