def main():
    with open('template.pprj', 'r') as template:
        template = template.read()
        #tables = ['thesaurus_baseline%d' % k for k in range(1, 19)] + ['annotation_thesaurus_baseline%d' % k for k in range(33, 39)]
        tables = ['annotation_Thesaurus_Baseline%d' % k for k in range(0, 29)] + ['annotation_thesaurus_baseline%d' % k for k in range(33, 39)]
        for index, table in enumerate(tables):
            print "Processing %s" % table
            content = template.replace('<<<TABLE>>>', table)
            with open('nci_%d.pprj' % index, 'w') as project:
                project.write(content)
        tables = ['annotation_Thesaurus_Baseline%d' % k for k in range(0, 29)]
        for index, table in enumerate(tables):
            print "Processing %s" % table
            content = template.replace('<<<TABLE>>>', table)
            with open('nci_old_%d.pprj' % index, 'w') as project:
                project.write(content)
    print "Done"
    
if __name__ == '__main__':
    main()