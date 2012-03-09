# -*- coding: UTF-8 -*-

"""
Downloads all the files of a Wikipedia dump and checks their hashes
"""
import urllib
import os
import hashlib
import re

def download():
    baseurl = "http://dumps.wikimedia.org/enwiki/20111201/"

    # these file names are copied verbatim from the above web site
    urls ="""enwiki-20111201-pages-meta-history1.xml-p000000010p000003343.7z 136.8 MB
enwiki-20111201-pages-meta-history1.xml-p000003344p000005409.7z 124.5 MB
enwiki-20111201-pages-meta-history1.xml-p000005410p000008182.7z 134.7 MB
enwiki-20111201-pages-meta-history1.xml-p000008183p000010000.7z 104.8 MB
enwiki-20111201-pages-meta-history2.xml-p000010001p000012663.7z 131.0 MB
enwiki-20111201-pages-meta-history2.xml-p000012664p000014909.7z 129.9 MB
enwiki-20111201-pages-meta-history2.xml-p000014910p000016625.7z 100.5 MB
enwiki-20111201-pages-meta-history2.xml-p000016628p000018758.7z 100.1 MB
enwiki-20111201-pages-meta-history2.xml-p000018760p000020412.7z 96.4 MB
enwiki-20111201-pages-meta-history2.xml-p000020414p000022413.7z 102.7 MB
enwiki-20111201-pages-meta-history2.xml-p000022414p000024434.7z 112.4 MB
enwiki-20111201-pages-meta-history2.xml-p000024435p000025000.7z 23.1 MB
enwiki-20111201-pages-meta-history3.xml-p000025001p000026833.7z 102.0 MB
enwiki-20111201-pages-meta-history3.xml-p000026838p000028951.7z 110.9 MB
enwiki-20111201-pages-meta-history3.xml-p000028952p000031260.7z 109.2 MB
enwiki-20111201-pages-meta-history3.xml-p000031261p000033158.7z 104.4 MB
enwiki-20111201-pages-meta-history3.xml-p000033161p000036971.7z 118.1 MB
enwiki-20111201-pages-meta-history3.xml-p000036972p000040297.7z 153.6 MB
enwiki-20111201-pages-meta-history3.xml-p000040298p000045470.7z 150.6 MB
enwiki-20111201-pages-meta-history3.xml-p000045472p000050973.7z 166.0 MB
enwiki-20111201-pages-meta-history3.xml-p000050974p000055000.7z 120.0 MB
enwiki-20111201-pages-meta-history4.xml-p000055002p000059892.7z 130.4 MB
enwiki-20111201-pages-meta-history4.xml-p000059893p000065651.7z 136.4 MB
enwiki-20111201-pages-meta-history4.xml-p000065652p000071792.7z 133.8 MB
enwiki-20111201-pages-meta-history4.xml-p000071793p000078336.7z 130.2 MB
enwiki-20111201-pages-meta-history4.xml-p000078337p000088324.7z 148.2 MB
enwiki-20111201-pages-meta-history4.xml-p000088325p000101898.7z 176.4 MB
enwiki-20111201-pages-meta-history4.xml-p000101899p000104998.7z 38.0 MB
enwiki-20111201-pages-meta-history5.xml-p000105001p000136247.7z 256.6 MB
enwiki-20111201-pages-meta-history5.xml-p000136248p000149354.7z 187.6 MB
enwiki-20111201-pages-meta-history5.xml-p000149355p000160792.7z 188.7 MB
enwiki-20111201-pages-meta-history5.xml-p000160793p000170026.7z 180.3 MB
enwiki-20111201-pages-meta-history5.xml-p000170027p000183740.7z 208.7 MB
enwiki-20111201-pages-meta-history5.xml-p000183741p000184999.7z 15.7 MB
enwiki-20111201-pages-meta-history6.xml-p000185003p000199445.7z 191.5 MB
enwiki-20111201-pages-meta-history6.xml-p000199446p000217500.7z 212.2 MB
enwiki-20111201-pages-meta-history6.xml-p000217501p000239297.7z 226.9 MB
enwiki-20111201-pages-meta-history6.xml-p000239298p000261150.7z 221.3 MB
enwiki-20111201-pages-meta-history6.xml-p000261151p000288150.7z 227.3 MB
enwiki-20111201-pages-meta-history6.xml-p000288151p000305000.7z 179.0 MB
enwiki-20111201-pages-meta-history7.xml-p000305002p000323167.7z 185.3 MB
enwiki-20111201-pages-meta-history7.xml-p000323168p000345811.7z 195.5 MB
enwiki-20111201-pages-meta-history7.xml-p000345813p000364423.7z 182.7 MB
enwiki-20111201-pages-meta-history7.xml-p000364425p000386887.7z 185.3 MB
enwiki-20111201-pages-meta-history7.xml-p000386888p000414848.7z 215.0 MB
enwiki-20111201-pages-meta-history7.xml-p000414849p000435871.7z 195.4 MB
enwiki-20111201-pages-meta-history7.xml-p000435874p000460253.7z 193.7 MB
enwiki-20111201-pages-meta-history7.xml-p000460254p000464997.7z 33.4 MB
enwiki-20111201-pages-meta-history8.xml-p000465001p000496675.7z 218.1 MB
enwiki-20111201-pages-meta-history8.xml-p000496676p000534386.7z 227.6 MB
enwiki-20111201-pages-meta-history8.xml-p000534387p000564696.7z 193.6 MB
enwiki-20111201-pages-meta-history8.xml-p000564697p000602483.7z 219.2 MB
enwiki-20111201-pages-meta-history8.xml-p000602484p000636692.7z 219.8 MB
enwiki-20111201-pages-meta-history8.xml-p000636693p000665000.7z 151.7 MB
enwiki-20111201-pages-meta-history9.xml-p000665001p000716868.7z 251.1 MB
enwiki-20111201-pages-meta-history9.xml-p000716869p000773959.7z 266.1 MB
enwiki-20111201-pages-meta-history9.xml-p000773960p000859805.7z 273.7 MB
enwiki-20111201-pages-meta-history9.xml-p000859806p000914122.7z 270.9 MB
enwiki-20111201-pages-meta-history9.xml-p000914124p000925000.7z 45.8 MB
enwiki-20111201-pages-meta-history10.xml-p000925001p000972034.7z 230.6 MB
enwiki-20111201-pages-meta-history10.xml-p000972035p001023197.7z 240.7 MB
enwiki-20111201-pages-meta-history10.xml-p001023199p001095706.7z 302.4 MB
enwiki-20111201-pages-meta-history10.xml-p001095707p001182469.7z 329.7 MB
enwiki-20111201-pages-meta-history10.xml-p001182471p001264757.7z 331.9 MB
enwiki-20111201-pages-meta-history10.xml-p001264758p001325000.7z 180.1 MB
enwiki-20111201-pages-meta-history11.xml-p001325001p001439517.7z 342.5 MB
enwiki-20111201-pages-meta-history11.xml-p001439518p001532791.7z 293.3 MB
enwiki-20111201-pages-meta-history11.xml-p001532792p001633584.7z 318.5 MB
enwiki-20111201-pages-meta-history11.xml-p001633586p001734818.7z 315.6 MB
enwiki-20111201-pages-meta-history11.xml-p001734819p001825000.7z 254.1 MB
enwiki-20111201-pages-meta-history12.xml-p001825001p001938822.7z 331.4 MB
enwiki-20111201-pages-meta-history12.xml-p001938823p002054713.7z 357.9 MB
enwiki-20111201-pages-meta-history12.xml-p002054715p002181929.7z 336.0 MB
enwiki-20111201-pages-meta-history12.xml-p002181930p002237175.7z 207.2 MB
enwiki-20111201-pages-meta-history12.xml-p002237176p002301314.7z 174.9 MB
enwiki-20111201-pages-meta-history12.xml-p002301315p002367306.7z 177.4 MB
enwiki-20111201-pages-meta-history12.xml-p002367308p002425000.7z 150.2 MB
enwiki-20111201-pages-meta-history13.xml-p002425001p002535875.7z 309.2 MB
enwiki-20111201-pages-meta-history13.xml-p002535877p002586018.7z 162.6 MB
enwiki-20111201-pages-meta-history13.xml-p002586019p002736872.7z 337.5 MB
enwiki-20111201-pages-meta-history13.xml-p002736873p002914855.7z 356.3 MB
enwiki-20111201-pages-meta-history13.xml-p002914856p003107615.7z 386.3 MB
enwiki-20111201-pages-meta-history13.xml-p003107616p003124998.7z 37.5 MB
enwiki-20111201-pages-meta-history14.xml-p003125001p003279591.7z 338.5 MB
enwiki-20111201-pages-meta-history14.xml-p003279593p003451225.7z 326.7 MB
enwiki-20111201-pages-meta-history14.xml-p003451227p003599746.7z 312.1 MB
enwiki-20111201-pages-meta-history14.xml-p003599747p003741656.7z 324.2 MB
enwiki-20111201-pages-meta-history14.xml-p003741657p003924999.7z 306.2 MB
enwiki-20111201-pages-meta-history15.xml-p003925001p004160521.7z 386.1 MB
enwiki-20111201-pages-meta-history15.xml-p004160528p004389605.7z 375.2 MB
enwiki-20111201-pages-meta-history15.xml-p004389609p004611493.7z 361.4 MB
enwiki-20111201-pages-meta-history15.xml-p004611494p004825000.7z 320.2 MB
enwiki-20111201-pages-meta-history16.xml-p004825001p005043192.7z 338.9 MB
enwiki-20111201-pages-meta-history16.xml-p005043194p005137507.7z 266.3 MB
enwiki-20111201-pages-meta-history16.xml-p005137508p005282169.7z 247.1 MB
enwiki-20111201-pages-meta-history16.xml-p005282170p005564296.7z 395.4 MB
enwiki-20111201-pages-meta-history16.xml-p005564297p005820258.7z 393.4 MB
enwiki-20111201-pages-meta-history16.xml-p005820261p006025000.7z 324.2 MB
enwiki-20111201-pages-meta-history17.xml-p006025001p006177137.7z 238.0 MB
enwiki-20111201-pages-meta-history17.xml-p006177138p006424922.7z 368.8 MB
enwiki-20111201-pages-meta-history17.xml-p006424923p006703617.7z 511.6 MB
enwiki-20111201-pages-meta-history17.xml-p006703618p006905700.7z 286.5 MB
enwiki-20111201-pages-meta-history17.xml-p006905701p007170273.7z 336.5 MB
enwiki-20111201-pages-meta-history17.xml-p007170274p007505160.7z 368.9 MB
enwiki-20111201-pages-meta-history17.xml-p007505162p007524999.7z 28.4 MB
enwiki-20111201-pages-meta-history18.xml-p007525002p007838545.7z 382.6 MB
enwiki-20111201-pages-meta-history18.xml-p007838547p008210133.7z 413.6 MB
enwiki-20111201-pages-meta-history18.xml-p008210134p008545752.7z 375.8 MB
enwiki-20111201-pages-meta-history18.xml-p008545753p008867758.7z 401.8 MB
enwiki-20111201-pages-meta-history18.xml-p008867759p009225000.7z 402.9 MB
enwiki-20111201-pages-meta-history19.xml-p009225001p009654110.7z 438.6 MB
enwiki-20111201-pages-meta-history19.xml-p009654111p010081897.7z 453.2 MB
enwiki-20111201-pages-meta-history19.xml-p010081898p010423025.7z 519.6 MB
enwiki-20111201-pages-meta-history19.xml-p010423027p010643068.7z 291.9 MB
enwiki-20111201-pages-meta-history19.xml-p010643069p010782336.7z 224.3 MB
enwiki-20111201-pages-meta-history19.xml-p010782338p011005908.7z 364.9 MB
enwiki-20111201-pages-meta-history19.xml-p011005911p011125000.7z 136.5 MB
enwiki-20111201-pages-meta-history20.xml-p011125001p011474936.7z 366.4 MB
enwiki-20111201-pages-meta-history20.xml-p011474937p011968595.7z 500.7 MB
enwiki-20111201-pages-meta-history20.xml-p011968597p012346293.7z 417.9 MB
enwiki-20111201-pages-meta-history20.xml-p012346294p012870648.7z 507.3 MB
enwiki-20111201-pages-meta-history20.xml-p012870649p013261098.7z 394.3 MB
enwiki-20111201-pages-meta-history20.xml-p013261102p013324998.7z 79.3 MB
enwiki-20111201-pages-meta-history21.xml-p013325001p013771035.7z 460.8 MB
enwiki-20111201-pages-meta-history21.xml-p013771036p014314216.7z 473.4 MB
enwiki-20111201-pages-meta-history21.xml-p014314217p014832618.7z 446.5 MB
enwiki-20111201-pages-meta-history21.xml-p014832619p015352141.7z 451.4 MB
enwiki-20111201-pages-meta-history21.xml-p015352142p015725000.7z 313.8 MB
enwiki-20111201-pages-meta-history22.xml-p015725003p016283969.7z 496.8 MB
enwiki-20111201-pages-meta-history22.xml-p016283970p016927404.7z 453.7 MB
enwiki-20111201-pages-meta-history22.xml-p016927406p017450097.7z 416.2 MB
enwiki-20111201-pages-meta-history22.xml-p017450099p018022576.7z 452.8 MB
enwiki-20111201-pages-meta-history22.xml-p018022577p018225000.7z 165.5 MB
enwiki-20111201-pages-meta-history23.xml-p018225001p018660105.7z 390.8 MB
enwiki-20111201-pages-meta-history23.xml-p018660106p018977430.7z 361.5 MB
enwiki-20111201-pages-meta-history23.xml-p018977431p019337544.7z 333.2 MB
enwiki-20111201-pages-meta-history23.xml-p019337545p019767582.7z 360.3 MB
enwiki-20111201-pages-meta-history23.xml-p019767583p020429402.7z 479.7 MB
enwiki-20111201-pages-meta-history23.xml-p020429403p020925000.7z 424.1 MB
enwiki-20111201-pages-meta-history24.xml-p020925002p021402352.7z 406.4 MB
enwiki-20111201-pages-meta-history24.xml-p021402353p021998387.7z 461.9 MB
enwiki-20111201-pages-meta-history24.xml-p021998388p022639715.7z 503.6 MB
enwiki-20111201-pages-meta-history24.xml-p022639716p023259666.7z 467.3 MB
enwiki-20111201-pages-meta-history24.xml-p023259667p023725000.7z 382.7 MB
enwiki-20111201-pages-meta-history25.xml-p023725001p024320051.7z 461.0 MB
enwiki-20111201-pages-meta-history25.xml-p024320052p025037165.7z 514.2 MB
enwiki-20111201-pages-meta-history25.xml-p025037168p025674296.7z 471.1 MB
enwiki-20111201-pages-meta-history25.xml-p025674297p026276372.7z 442.2 MB
enwiki-20111201-pages-meta-history25.xml-p026276373p026625000.7z 238.1 MB
enwiki-20111201-pages-meta-history26.xml-p026625002p027456236.7z 500.3 MB
enwiki-20111201-pages-meta-history26.xml-p027456237p028329803.7z 555.6 MB
enwiki-20111201-pages-meta-history26.xml-p028329804p029466351.7z 572.8 MB
enwiki-20111201-pages-meta-history26.xml-p029466352p029625000.7z 82.7 MB
enwiki-20111201-pages-meta-history27.xml-p029625001p030815455.7z 563.1 MB
enwiki-20111201-pages-meta-history27.xml-p030815456p031764407.7z 618.2 MB
enwiki-20111201-pages-meta-history27.xml-p031764408p032810977.7z 583.4 MB
enwiki-20111201-pages-meta-history27.xml-p032810978p033928889.7z 475.2 MB
"""
    urls = re.findall(r'enwiki.*7z', urls)
    
    for index, line in enumerate(urls):
        print "Downloading ", index + 1, " of ", len(urls)
        line = line.rstrip()
        f = open(line, "w+") # create the file
        f.close()
        urllib.urlretrieve(baseurl + line, line)

def check_md5():
    d = {}
    for line in open("enwiki-20111201-md5sums.txt"): # retrieved from http://dumps.wikimedia.org/enwiki/20111201/enwiki-20111201-md5sums.txt
        d[line.split()[1]] = line.split()[0]

    for file in os.listdir(os.getcwd()):
        if file[-2:] == "7z":
            f = open(file, "rb")
            md5 = hashlib.md5()
            while True:
                data = f.read(8192)
                if not data:
                    break
                md5.update(data)
            m = md5.hexdigest()
            if d[file] != m:
                print file, " ", m, "MD5 HASH NOT OK"
            else:
                print file, "OK"
                
                
if __name__ == '__main__':
    download()
    #check_md5()