import re
import sys
import bibtexparser
from fuzzywuzzy import fuzz

def short(s):
    return re.sub('[^a-z]', '', s.lower())

article_reserved_attr = ['title', 'author', 'journal', 'year', 'volume', 'number', 'pages']
inprocedings_reserved_attr = ['title', 'author', 'booktitle', 'year', 'pages']
all_reserved_attr = ['ID', 'ENTRYTYPE']
existed_title = set()
attr_parser = {}

bucket_re = re.compile(r'[(](.*)[)]', re.S)
attr_parser['booktitle'] = [ lambda x: re.sub(bucket_re, '', x), lambda x: re.sub('[0-9]', '', x) ]
attr_parser['journal'] = [ lambda x: re.sub(bucket_re, '', x) ]
attr_parser['pages'] = [ lambda x: re.sub('-', '--', re.sub('--', '-', x)) ]

def citation_to_str(citation):
    s = ''
    s += '@%s{\t\t%s,\n' % (citation['ENTRYTYPE'], citation['ID'])
    for attr in citation:
        if attr not in all_reserved_attr:
            s += '\t%s\t\t = {%s},\n' % (attr, citation[attr])
    s += '}\n'
    return s

if __name__ == '__main__':
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    error_file = 'error.txt'
    errf = open(error_file, 'w')
    f = open(input_file, 'r')
    citations = bibtexparser.load(f).entries
    f.close()

    f = open(input_file, 'r')
    old_citations = bibtexparser.load(open('data', 'r')).entries
    f.close()

    conf_cnt = {}
    for citation in old_citations:
        if citation['ENTRYTYPE'] == 'inproceedings':
            name = citation['booktitle']
        elif citation['ENTRYTYPE'] == 'article':
            name = citation['journal']
        else:
            continue
        name = re.sub('\n', '', name)
        if name not in conf_cnt:
            conf_cnt[name] = 0
        conf_cnt[name] += 1
    conf_names = [[name, conf_cnt[name]] for name in conf_cnt if conf_cnt[name] > 2]
    conf_names = sorted(conf_names, key = lambda x: -x[1])
    conf_names = [x[0] for x in conf_names]
    for i in range(1, len(conf_names)):
        for j in range(i):
            if fuzz.ratio(conf_names[i], conf_names[j]) >= 98:
                conf_names[i] = ''
                break
    conf_names = [x for x in conf_names if x != '']

    new_citations = []
    duplicated_paper_cnt = 0
    for citation in citations:
        item = {}
        for attr in citation:
            citation[attr] = re.sub('\n', ' ', citation[attr])
        title = citation['title']
        short_title = short(title)
        if short_title in existed_title:
            duplicated_paper_cnt += 1
            continue
        existed_title.add(short_title)
        missing_attrs = []
        if citation['ENTRYTYPE'] == 'inproceedings':
            conf = citation['booktitle']
            for name in conf_names:
                if fuzz.ratio(name, conf) >= 98:
                    conf = name
                    break
            if not conf.startswith('Proceedings of'):
                conf = 'Proceedings of ' + conf
            citation['booktitle'] = conf
            for attr in inprocedings_reserved_attr:
                if attr not in citation:
                    missing_attrs.append(attr)
                else:
                    value = citation[attr]
                    if attr in attr_parser:
                        for f in attr_parser[attr]:
                            value = f(value)
                    item[attr] = value
            for attr in all_reserved_attr:
                item[attr] = citation[attr]
            if 'International Conference on Learning Representations' in conf or 'AAAI' in conf or 'ICLR' in conf:
                missing_attrs = [attr for attr in missing_attrs if attr != 'pages']
        elif citation['ENTRYTYPE'] == 'article':
            journal = citation['journal']
            for name in conf_names:
                if fuzz.ratio(name, journal) >= 98:
                    journal = name
                    break
            citation['journal'] = journal
            for attr in article_reserved_attr:
                if attr not in citation:
                    missing_attrs.append(attr)
                else:
                    value = citation[attr]
                    if attr in attr_parser:
                        for f in attr_parser[attr]:
                            value = f(value)
                    item[attr] = value
            for attr in all_reserved_attr:
                value = citation[attr]
                item[attr] = value
            if 'arXiv' in journal:
                missing_attrs = []
        else:
            title = ''
            item = citation
        if len(missing_attrs) > 0:
            errf.write(citation_to_str(citation))
            errf.write('%s are missing.\n' % (', '.join(['"' + x + '"' for x in missing_attrs])))
            errf.write('\n')
        new_citations.append(item)
    print('%s duplicated papers have been dropped.' % duplicated_paper_cnt)
    print('%s papers remain.' % len(new_citations))
    f = open(output_file, 'w')
    new_citations = sorted(new_citations, key = lambda x: -int(x.get('year', 0)))
    for citation in new_citations:
        f.write(citation_to_str(citation))
        f.write('\n')
    f.close()
    errf.close()