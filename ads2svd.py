#! /usr/bin/python3

from lxml import etree
import lxml.builder
import os
import sys
import glob
import copy
import re
import pprint

#rows, columns = os.popen('stty size', 'r').read().split()
#pp = pprint.PrettyPrinter(indent=4)#,width=columns)

config={}

#config["base_path"]="/home/jg/developmentstudio-2019.1/"
#config["configdb_path"]= config["base_path"] + "sw/debugger/configdb/"
#config["configdb_cores_path"]= config["configdb_path"] + "Cores/"

config["base_path"]= os.getcwd() +"/in"
config["configdb_path"]= config["base_path"] + "/"
config["configdb_cores_path"]= config["configdb_path"] + "Cores/"

config["configdb_schemas_path"]= config["configdb_path"] + "Schemas/"
config["xinclude_error_log"] = './xinclude_error.log'
config["out_dir"] =  './out/'

rawparser = etree.XMLParser(remove_blank_text=True)
parser=None

def build_schema_wrapper():
    global parser    
    breaking = { 'os_extension.xsd' : 1 }
    ws = '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="">'+"\n" 
    for s in glob.glob(  config["configdb_schemas_path"] + "*.xsd"):
        if(s.split('/')[-1] in breaking):
            continue        
        sch = etree.parse(s,rawparser)
        tns = sch.xpath('/xs:schema',namespaces={'xs': 'http://www.w3.org/2001/XMLSchema'})[0].get("targetNamespace")   
        if(tns):
            ws += '<xs:import'+"\n"
            ws += 'namespace="' + tns + '"'+ "\n"
            ws+= 'schemaLocation="file://' + s + '"' + "\n/>\n"        
    ws +="</xs:schema>"        
    s  = etree.XMLSchema(etree.XML(ws))
    parser = etree.XMLParser(remove_blank_text=True,schema =  s)

def loadxml(p):
    if not os.path.isdir(config["out_dir"]):
        os.mkdir(config["out_dir"])
    print(p)
    curr_path = '/'.join(p.split("/")[:-1])
    root = etree.parse(p,parser)
    error_log = open(config["xinclude_error_log"],"a")
    out_file = config["out_dir"] + p.split("/")[-1]
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
#        'Cortex-M0+.xml',
        'Cortex-M4.xml',
        'Cortex-A72.xml',
    ]
    for x in xmls_cores:
        loadxml(config["configdb_cores_path"] +"/" + x)

def get_all():
    error_log = open(config["xinclude_error_log"],"w+")
    error_log.close()
    xmls_cores = [ x for x in sorted(glob.glob(  config["configdb_cores_path"] + "*.xml"))]
    for x in xmls_cores:
        loadxml(x)     

def get_one(x):

    loadxml(x)     

        
build_schema_wrapper()
#get_dev()
#get_all()
get_one(sys.argv[1])

