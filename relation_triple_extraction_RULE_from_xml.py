#!/usr/bin/env python
# coding=utf-8
"""
基于句法依存关系抽取文本中的实体关系三元组
python *.py input.txt output.txt corpus.txt
"""

__author__ = "tianwen jiang"

# Set your own model path
MODELDIR="/data/ltp/ltp-models/3.3.0/ltp_data"

import sys
import os

from lxml import etree 
from pyltp import Segmentor, Postagger, Parser, NamedEntityRecognizer

print "正在加载LTP模型... ..."

segmentor = Segmentor()
segmentor.load(os.path.join(MODELDIR, "cws.model"))

postagger = Postagger()
postagger.load(os.path.join(MODELDIR, "pos.model"))

parser = Parser()
parser.load(os.path.join(MODELDIR, "parser.model"))

recognizer = NamedEntityRecognizer()
recognizer.load(os.path.join(MODELDIR, "ner.model"))

#labeller = SementicRoleLabeller()
#labeller.load(os.path.join(MODELDIR, "srl/"))

print "加载模型完毕。"

in_file_name = "input.txt"
out_file_name = "output.txt"
corpus_file_name = "corpus.txt"
begin_line = 1
end_line = 0

if len(sys.argv) > 1:
    in_file_name = sys.argv[1]

if len(sys.argv) > 2:
    out_file_name = sys.argv[2]

if len(sys.argv) > 3:
    corpus_file_name = sys.argv[3]

def fact_triple_extract(sentence, out_file, out_sentence_element):
    """
    对于给定的句子进行事实三元组抽取
    Args:
        sentence: 要处理的语句
    """
    #print sentence
    words = segmentor.segment(sentence)
    #print "\t".join(words)
    postags = postagger.postag(words)
    netags = recognizer.recognize(words, postags)
    arcs = parser.parse(words, postags)
    #print "\t".join("%d:%s" % (arc.head, arc.relation) for arc in arcs)
    
    find_flag = False
    
    NE_list = set()
    for i in range(len(netags)):
        if netags[i][0] == 'S' or netags[i][0] == 'B':
            j = i
            if netags[j][0] == 'B':
                while netags[j][0] != 'E':
                    j += 1
                e = ''.join(words[i:j+1])
                NE_list.add(e)
            else:
                e = words[j]
                NE_list.add(e)

    corpus_flag = False
    child_dict_list = build_parse_child_dict(words, postags, arcs)
    for index in range(len(postags)):
        # 抽取以谓词为中心的事实三元组
        if postags[index] == 'v':
            child_dict = child_dict_list[index]
            # 主谓宾
            if child_dict.has_key('SBV') and child_dict.has_key('VOB'):
                e1 = complete_e(words, postags, child_dict_list, child_dict['SBV'][0])
                r = words[index]
                e2 = complete_e(words, postags, child_dict_list, child_dict['VOB'][0])
                #if e1 in NE_list or e2 in NE_list:
                if is_good(e1, NE_list, sentence) and is_good(e2, NE_list, sentence):
                    out_file.write("主语谓语宾语关系\t(%s, %s, %s)\n" % (e1, r, e2))
                    out_file.flush()
                    find_flag = True
                    e1_start = (sentence.decode('utf-8')).index((e1.decode('utf-8')))
                    r_start = (sentence.decode('utf-8')).index((r.decode('utf-8')))
                    e2_start = (sentence.decode('utf-8')).index((e2.decode('utf-8')))
                    out_triple_element = etree.SubElement(out_sentence_element, "triple")
                    out_triple_element.attrib["type"] = u"主语谓语宾语关系"
                    out_e1_element = etree.SubElement(out_triple_element, "head_entity")
                    out_e1_element.attrib["start"] = str(e1_start)
                    out_e1_element.attrib["length"] = str(len(e1.decode('utf-8')))
                    out_e1_element.text = e1.decode('utf-8')
                    out_r_element = etree.SubElement(out_triple_element, "head_entity")
                    out_r_element.attrib["start"] = str(r_start)
                    out_r_element.attrib["length"] = str(len(r.decode('utf-8')))
                    out_r_element.text = r.decode('utf-8')
                    out_e2_element = etree.SubElement(out_triple_element, "head_entity")
                    out_e2_element.attrib["start"] = str(e2_start)
                    out_e2_element.attrib["length"] = str(len(e2.decode('utf-8')))
                    out_e2_element.text = e2.decode('utf-8')
            # 定语后置，动宾关系
            if arcs[index].relation == 'ATT':
                if child_dict.has_key('VOB'):
                    e1 = complete_e(words, postags, child_dict_list, arcs[index].head - 1)
                    r = words[index]
                    e2 = complete_e(words, postags, child_dict_list, child_dict['VOB'][0])
                    temp_string = r+e2
                    if temp_string == e1[:len(temp_string)]:
                        e1 = e1[len(temp_string):]
                    #if temp_string not in e1 and (e1 in NE_list or e2 in NE_list):
                    if temp_string not in e1 and is_good(e1, NE_list, sentence) and is_good(e2, NE_list, sentence):
                        out_file.write("定语后置动宾关系\t(%s, %s, %s)\n" % (e1, r, e2))
                        out_file.flush()
                        find_flag = True
                        e1_start = (sentence.decode('utf-8')).index((e1.decode('utf-8')))
                        e1_end = e1_start + len(e1.decode('utf-8')) - 1
                        r_start = (sentence.decode('utf-8')).index((r.decode('utf-8')))
                        r_end = r_start + len(r.decode('utf-8')) - 1
                        e2_start = (sentence.decode('utf-8')).index((e2.decode('utf-8')))
                        e2_end = e2_start + len(e2.decode('utf-8')) - 1
                        out_triple_element = etree.SubElement(out_sentence_element, "triple")
                        out_triple_element.attrib["type"] = u"定语后置动宾关系"
                        out_e1_element = etree.SubElement(out_triple_element, "head_entity")
                        out_e1_element.attrib["start"] = str(e1_start)
                        out_e1_element.attrib["length"] = str(len(e1.decode('utf-8')))
                        out_e1_element.text = e1.decode('utf-8')
                        out_r_element = etree.SubElement(out_triple_element, "head_entity")
                        out_r_element.attrib["start"] = str(r_start)
                        out_r_element.attrib["length"] = str(len(r.decode('utf-8')))
                        out_r_element.text = r.decode('utf-8')
                        out_e2_element = etree.SubElement(out_triple_element, "head_entity")
                        out_e2_element.attrib["start"] = str(e2_start)
                        out_e2_element.attrib["length"] = str(len(e2.decode('utf-8')))
                        out_e2_element.text = e2.decode('utf-8')
            # 含有介宾关系的主谓动补关系
            if child_dict.has_key('SBV') and child_dict.has_key('CMP'):
                #e1 = words[child_dict['SBV'][0]]
                e1 = complete_e(words, postags, child_dict_list, child_dict['SBV'][0])
                cmp_index = child_dict['CMP'][0]
                r = words[index] + words[cmp_index]
                if child_dict_list[cmp_index].has_key('POB'):
                    e2 = complete_e(words, postags, child_dict_list, child_dict_list[cmp_index]['POB'][0])
                    #if e1 in NE_list or e2 in NE_list:
                    if is_good(e1, NE_list, sentence) and is_good(e2, NE_list, sentence):
                        out_file.write("介宾关系主谓动补\t(%s, %s, %s)\n" % (e1, r, e2))
                        out_file.flush()
                        find_flag = True
                        e1_start = (sentence.decode('utf-8')).index((e1.decode('utf-8')))
                        e1_end = e1_start + len(e1.decode('utf-8')) - 1
                        r_start = (sentence.decode('utf-8')).index((r.decode('utf-8')))
                        r_end = r_start + len(r.decode('utf-8')) - 1
                        e2_start = (sentence.decode('utf-8')).index((e2.decode('utf-8')))
                        e2_end = e2_start + len(e2.decode('utf-8')) - 1
                        out_triple_element = etree.SubElement(out_sentence_element, "triple")
                        out_triple_element.attrib["type"] = u"介宾关系主谓动补"
                        out_e1_element = etree.SubElement(out_triple_element, "head_entity")
                        out_e1_element.attrib["start"] = str(e1_start)
                        out_e1_element.attrib["length"] = str(len(e1.decode('utf-8')))
                        out_e1_element.text = e1.decode('utf-8')
                        out_r_element = etree.SubElement(out_triple_element, "head_entity")
                        out_r_element.attrib["start"] = str(r_start)
                        out_r_element.attrib["length"] = str(len(r.decode('utf-8')))
                        out_r_element.text = r.decode('utf-8')
                        out_e2_element = etree.SubElement(out_triple_element, "head_entity")
                        out_e2_element.attrib["start"] = str(e2_start)
                        out_e2_element.attrib["length"] = str(len(e2.decode('utf-8')))
                        out_e2_element.text = e2.decode('utf-8')
        # 尝试抽取命名实体有关的三元组
        if netags[index][0] == 'S' or netags[index][0] == 'B':
            ni = index
            if netags[ni][0] == 'B':
                while netags[ni][0] != 'E':
                    ni += 1
                e1 = ''.join(words[index:ni+1])
            else:
                e1 = words[ni]
            if arcs[ni].relation == 'ATT' and postags[arcs[ni].head-1] == 'n' and netags[arcs[ni].head-1] == 'O':
                r = complete_e(words, postags, child_dict_list, arcs[ni].head-1)
                if e1 in r:
                    r = r[(r.index(e1)+len(e1)):]
                if arcs[arcs[ni].head-1].relation == 'ATT' and netags[arcs[arcs[ni].head-1].head-1] != 'O':
                    e2 = complete_e(words, postags, child_dict_list, arcs[arcs[ni].head-1].head-1)
                    mi = arcs[arcs[ni].head-1].head-1
                    li = mi
                    if netags[mi][0] == 'B':
                        while netags[mi][0] != 'E':
                            mi += 1
                        e = ''.join(words[li+1:mi+1])
                        e2 += e
                    if r in e2:
                        e2 = e2[(e2.index(r)+len(r)):]
                    if is_good(e1, NE_list, sentence) and is_good(e2, NE_list, sentence):
                        out_file.write("人名//地名//机构\t(%s, %s, %s)\n" % (e1, r, e2))
                        out_file.flush()
                        find_flag = True
                        e1_start = (sentence.decode('utf-8')).index((e1.decode('utf-8')))
                        e1_end = e1_start + len(e1.decode('utf-8')) - 1
                        r_start = (sentence.decode('utf-8')).index((r.decode('utf-8')))
                        r_end = r_start + len(r.decode('utf-8')) - 1
                        e2_start = (sentence.decode('utf-8')).index((e2.decode('utf-8')))
                        e2_end = e2_start + len(e2.decode('utf-8')) - 1
                        out_triple_element = etree.SubElement(out_sentence_element, "triple")
                        out_triple_element.attrib["type"] = u"人名//地名//机构"
                        out_e1_element = etree.SubElement(out_triple_element, "head_entity")
                        out_e1_element.attrib["start"] = str(e1_start)
                        out_e1_element.attrib["length"] = str(len(e1.decode('utf-8')))
                        out_e1_element.text = e1.decode('utf-8')
                        out_r_element = etree.SubElement(out_triple_element, "head_entity")
                        out_r_element.attrib["start"] = str(r_start)
                        out_r_element.attrib["length"] = str(len(r.decode('utf-8')))
                        out_r_element.text = r.decode('utf-8')
                        out_e2_element = etree.SubElement(out_triple_element, "head_entity")
                        out_e2_element.attrib["start"] = str(e2_start)
                        out_e2_element.attrib["length"] = str(len(e2.decode('utf-8')))
                        out_e2_element.text = e2.decode('utf-8')
    
    return find_flag;

def build_parse_child_dict(words, postags, arcs):
    """
    为句子中的每个词语维护一个保存句法依存儿子节点的字典
    Args:
        words: 分词列表
        postags: 词性列表
        arcs: 句法依存列表
    """
    child_dict_list = []
    for index in range(len(words)):
        child_dict = dict()
        for arc_index in range(len(arcs)):
            if arcs[arc_index].head == index + 1:
                if child_dict.has_key(arcs[arc_index].relation):
                    child_dict[arcs[arc_index].relation].append(arc_index)
                else:
                    child_dict[arcs[arc_index].relation] = []
                    child_dict[arcs[arc_index].relation].append(arc_index)
        #if child_dict.has_key('SBV'):
        #    print words[index],child_dict['SBV']
        child_dict_list.append(child_dict)
    return child_dict_list

def complete_e(words, postags, child_dict_list, word_index):
    """
    完善识别的部分实体
    """
    child_dict = child_dict_list[word_index]
    prefix = ''
    if child_dict.has_key('ATT'):
        for i in range(len(child_dict['ATT'])):
            prefix += complete_e(words, postags, child_dict_list, child_dict['ATT'][i])
    
    postfix = ''
    if postags[word_index] == 'v':
        if child_dict.has_key('VOB'):
            postfix += complete_e(words, postags, child_dict_list, child_dict['VOB'][0])
        if child_dict.has_key('SBV'):
            prefix = complete_e(words, postags, child_dict_list, child_dict['SBV'][0]) + prefix

    return prefix + words[word_index] + postfix

def is_good(e, NE_list, sentence):
    """
    判断e是否为命名实体
    """
    if e not in sentence:
        return False

    words_e = segmentor.segment(e)
    postags_e = postagger.postag(words_e)
    if e in NE_list:
        return True
    else:
        NE_count = 0
        for i in range(len(words_e)):
            if words_e[i] in NE_list:
                NE_count += 1
            if postags_e[i] == 'v':
                return False
        if NE_count >= len(words_e)-NE_count:
            return True
    return False

def extraction_start_from_xml(in_file_name):
    """
    提取文本中的text标签的内容，进行实体关系三元组抽取
    """
    docs_root = etree.parse(in_file_name).getroot()
    out_file = open(in_file_name+'.triple.txt', 'w')
    out_docs_root = etree.Element("docs")
    sentence_count = 0
    find_flag = False
    for each_doc in docs_root:  # 遍历每个doc
        out_doc_element = etree.SubElement(out_docs_root, "doc")
        out_doc_element.attrib["name"] = each_doc.attrib["name"]
        out_doc_element.attrib["url"] = each_doc.attrib["url"]
        out_doc_element.attrib["id"] = each_doc.attrib["id"]
        out_doc_element.attrib["baike_id"] = each_doc.attrib["baike_id"]
        out_doc_element.attrib["time"] = each_doc.attrib["time"]
        for each_par in each_doc:
            out_par_element = etree.SubElement(out_doc_element, "par")
            for element in each_par:
                if element.tag == "text":  
                    text = element.text.encode('utf-8')
                    text = text.replace("。","。\n").replace("！","！\n").replace("？","？\n")
                    sentences = text.split("\n")
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if sentence == '':
                            continue
                        sentence_count += 1
                        if sentence_count%1000 == 0:
                            print sentence_count,"sentences done."
                        u_sentence = sentence.decode('utf-8')
                        out_sentence_element = etree.SubElement(out_par_element, "sentence")
                        out_s_text_element = etree.SubElement(out_sentence_element, "s_text")
                        out_s_text_element.text = u_sentence
                        try:
                            find_flag = fact_triple_extract(sentence, out_file, out_sentence_element)
                            if find_flag == False:
                                out_sentence_element.xpath("..")[0].remove(out_sentence_element)
                            out_file.flush()
                        except:
                            pass
            if find_flag == False:
                out_par_element.xpath("..")[0].remove(out_par_element)
        if find_flag == False:
            out_doc_element.xpath("..")[0].remove(out_doc_element)
    tree = etree.ElementTree(out_docs_root)
    tree.write(in_file_name+".triple.xml", pretty_print=True, xml_declaration=True, encoding='utf-8')
if __name__ == "__main__":
    extraction_start_from_xml(in_file_name)
