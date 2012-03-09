# -*- coding: UTF-8 -*-

"""
Extracts ICD-10 articles from a Wikipedia dump.
Unzips each .7z file in the current working directory and extracts ICD-10 articles
This might use a lot of RAM and/or page files
requires the command line version of 7zip (7za)
"""

import os
import sys
import re

irrelevant = ["User:", "Talk:", "Template:", "Special:", "Wikipedia:", "Portal:", "Help:", "File:", "File:", "MediaWiki:", "Category:", "Book:", "Media:"]
irrelevant = map(lambda x: x.lower(), irrelevant) # convert to lower case

def extract_icd10_articles(sourcefile, targetfile):
    of = open(targetfile, "w+")
    of.write("<mediawiki>\n")
    read = 0
    page = []
    found = 0
    for line in open(sourcefile):
        if "<page>" in line:
            read = 1
        if read == 1:
            page.append(line)
            if "<title>" in line:
                for keyword in irrelevant:
                    line = line.lower()
                    if (keyword in line) or (keyword[:-1] + "_talk:" in line) or (keyword[:-1] + " talk:" in line):
                        del page
                        page = []
                        read = 0
                        found = 0
                        break
        if "</page>" in line:
            for pagestring in reversed(page):
                pagestring = re.sub(r'\s', '', pagestring) # remove white space
                if "{{ICD-10}}" in pagestring or "{{ICD10|" in pagestring:
                    found = 1
                    break
                if "<revision>" in pagestring:
                    break
            if found == 1:
                for pagestring in page:
                    of.write(pagestring)
            del page
            page = []
            read = 0
            found = 0
    of.write("</mediawiki>\n")
    
def main():
    for file in os.listdir(os.getcwd()):
        if file.endswith(".7z"):
            print file

            # unzip
            os.system("7za e " + file)

            # extract
            extract_icd10_articles(file[:-3], file[:-3] + "_extracted.xml")

            # delete unzipped file
            os.remove(file[:-3])

if __name__ == '__main__':
    main()        