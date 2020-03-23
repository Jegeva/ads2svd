#! /usr/bin/env python3

import lxml
from lxml import etree
import lxml.builder
import os
import sys
import glob
import copy
import re
import argparse

rawparser = etree.XMLParser(remove_blank_text=True)
xmlparser=None
config={}

def update_config(args):    
    global config
    config["configdb_path"]= os.path.abspath(os.path.expanduser(args.configdb))
    config["configdb_cores_path"]=  os.path.join(config["configdb_path"], "Cores/")
    config["configdb_schemas_path"]= os.path.join(config["configdb_path"], "Schemas/")
    config["out_dir"] =   os.path.normpath(args.out)
    config["xinclude_error_log"] = os.path.join(config["out_dir"], 'xinclude_error.log')
    if not os.path.isdir(config["out_dir"]):
        os.mkdir(config["out_dir"])

    if os.path.isfile(config["xinclude_error_log"]):
        error_log = open(config["xinclude_error_log"],"w+")
        error_log.close()




def build_schema_wrapper():
    global xmlparser    
    breaking = { 'os_extension.xsd' : 1 }
    ws = '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="">'+"\n" 
    for s in glob.glob(  os.path.join(config["configdb_schemas_path"] , "*.xsd")):        
        if(s.split(os.path.sep)[-1] in breaking):
            continue
        sch = etree.parse(s,rawparser)
        tns = sch.xpath('/xs:schema',namespaces={'xs': 'http://www.w3.org/2001/XMLSchema'})[0].get("targetNamespace")   
        if(tns):
            ws += '<xs:import'+"\n"
            ws += 'namespace="' + tns + '"'+ "\n"
            ws+= 'schemaLocation="file://' + s + '"' + "\n/>\n"        
    ws +="</xs:schema>"
    s  = etree.XMLSchema(etree.XML(ws))
    xmlparser = etree.XMLParser(remove_blank_text=True,schema =  s)

def loadxml(p):

    print(p)
    curr_path = os.path.sep.join(p.split(os.path.sep)[:-1])
    root = etree.parse(p,xmlparser)
    error_log = open(config["xinclude_error_log"],"a")
    out_file = os.path.join(config["out_dir"] , p.split(os.path.sep)[-1])
    out_file = open(out_file,"w")
    nfail = 0;  
    incls = [i for i in root.xpath("//xi:include", namespaces={'xi':'http://www.w3.org/2001/XInclude'})]
    for el in incls:        
        tree =  etree.ElementTree(el)
        try :
            tree.xinclude()
            #error_log.write( 'SUCC "%s";"%s";\n' % (p[len(config["base_path"]):],orighref))         
        except lxml.etree.XIncludeError as err:
            if el.get("href"):
                error_log.write( 'ERR;num=%d;file="%s";errhref="%s";errreason="%s";merrmsg="%s"\n' % (nfail,p[len(config["base_path"]):],el.get("href"),el.get("xpointer"),err))
                nfail+=1
                error_log.flush()
                pap = el.getparent()        
                pap.append(etree.Comment( b'FAIL : %d ' % (nfail) + etree.tostring( el)))
                pap.remove(el)
    out_file.write(etree.tostring(root, pretty_print=True).decode("utf8"))
    error_log.close()
    out_file.close()

def get_dev():
    error_log = open(config["xinclude_error_log"],"w+")
    error_log.close()
    xmls_cores = [
        'Cortex-M0.xml',
        'Cortex-M4.xml',
        'Cortex-A72.xml',
    ]
    for x in xmls_cores:
        loadxml(config["configdb_cores_path"] +"/" + x)

def get_all():
    error_log = open(config["xinclude_error_log"],"w+")
    error_log.close()
    xmls_cores = [ x for x in sorted(glob.glob(   os.path.join(config["configdb_cores_path"] , "*.xml")))]
    for x in xmls_cores:
        loadxml(x)     
        


argparser = argparse.ArgumentParser()
argparser.add_argument('-c', '--configdb', required=True, help="Base path for the DS configdb folder.")
argparser.add_argument('-o', '--out'     , default="./out/", help="Output directory path (defaults to 'out').")
argparser.add_argument('-a', '--all'     , action='store_true' , help="Process all xml files in configdb/Cores/ (default).")
argparser.add_argument('-i', '--infile'      , default=False, help="Process an xml file.")

args = argparser.parse_args()



if(args.infile):
    args.all = False
 
update_config(args)
build_schema_wrapper()
    
if(args.all):
    get_all()
elif args.infile:
    loadxml(args.infile)
else:
    print("No action selected")

