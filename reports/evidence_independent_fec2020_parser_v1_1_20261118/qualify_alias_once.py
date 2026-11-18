"""Finite independent authored suite / fresh-reader controls; no real data."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import signal
import sys
import sysconfig
import time
import types
import unittest
import zipfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
MIME=Path('/private/etc/apache2/mime.types')
MIME_SHA='57265fdf030202387c23e44283d440cab368a031214566b538b4b27064ed23df'


def main(mode):
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('review120seconds')))
    signal.setitimer(signal.ITIMER_REAL,120)
    started=time.monotonic()
    trusted={Path(sysconfig.get_path('stdlib')).resolve(),Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve()}
    allowed={ROOT/'src/civiclab/e01/fec2020_parser_v1.py',ROOT/'src/civiclab/e01/__init__.py',ROOT/'src/civiclab/__init__.py',ROOT/'tests/test_fec2020_parser_v1.py',ROOT/'configs/e01_fec2020_senate_mapping_v1.json',HERE/'additional_controls.py',HERE/'SOURCE_PINS.json',MIME,ROOT/'scripts/qualify_fec2020_reader_fixture_v1_20261118.py'}
    def audit(event,args):
        if event=='ctypes.dlopen' and args[0] is not None:raise RuntimeError('NO_FOREIGN_LIBRARY')
        if event.startswith('socket.') or event in ('sqlite3.connect','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
            raise RuntimeError('REVIEW_NO_EXTERNAL')
        if event=='open' and not isinstance(args[0],int):
            path=Path(os.fsdecode(args[0])).resolve();flags=args[2]
            if path.name.startswith('.env') or 'SyntheticSocietyLab' in str(path):raise RuntimeError('NO_KEY_OR_OWNER')
            if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise RuntimeError('NO_CHILD_FILE_WRITES')
            if not(path in allowed or path.is_relative_to(ROOT/'src') or any(path.is_relative_to(t) for t in trusted)):
                raise RuntimeError('REVIEW_READ_SCOPE')
    sys.addaudithook(audit)
    console=[0]
    class Output:
        def __init__(self,stream):self.stream=stream
        def __getattr__(self,k):return getattr(self.stream,k)
        def write(self,value):
            console[0]+=len(value.encode())
            if console[0]>65536:raise RuntimeError('CONSOLE_BOUND')
            return self.stream.write(value)
        def flush(self):return self.stream.flush()
    sys.stdout=Output(sys.stdout);sys.stderr=Output(sys.stderr)
    mime=MIME.read_bytes()
    if len(mime)!=61375 or hashlib.sha256(mime).hexdigest()!=MIME_SHA:raise RuntimeError('MIME_PIN_CHANGED')
    pins=json.loads((HERE/'SOURCE_PINS.json').read_text())
    for item in pins['source_refs']:
        if item['path']=='pyproject.toml':continue  # parent metadata check, no package install
        raw=(ROOT/item['path']).read_bytes()
        if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:raise RuntimeError('FROZEN_PIN_CHANGED')
    sys.path.insert(0,str(ROOT/'src'))
    from civiclab.e01 import fec2020_parser_v1 as p
    def module(path,name):
        m=types.ModuleType(name);m.__file__=str(path);sys.modules[name]=m
        exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m
    authored=module(ROOT/'tests/test_fec2020_parser_v1.py','frozen_authored_suite')
    if mode=='suite':
        extra=module(HERE/'additional_controls.py','independent_controls')
        suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(authored),unittest.defaultTestLoader.loadTestsFromModule(extra)])
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        summary={'kind':'INDEPENDENT_FEC_PARSER_FOCUSED_SUITE','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful()}
        exitcode=0 if result.wasSuccessful() else 1
    else:
        # No actual workbook. Construct every cell solely from fictional tables.
        contract=p.load_contract(ROOT/'configs/e01_fec2020_senate_mapping_v1.json')
        tables=authored.tables(contract)
        ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        rel='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        pkg='http://schemas.openxmlformats.org/package/2006/relationships'
        content='http://schemas.openxmlformats.org/package/2006/content-types'
        members={};book=ET.Element('workbook',xmlns=ns);sheets=ET.SubElement(book,'sheets');rels=ET.Element('Relationships',xmlns=pkg)
        typesxml=ET.Element('Types',xmlns=content)
        ET.SubElement(typesxml,'Default',Extension='rels',ContentType='application/vnd.openxmlformats-package.relationships+xml')
        ET.SubElement(typesxml,'Default',Extension='xml',ContentType='application/xml')
        ET.SubElement(typesxml,'Override',PartName='/xl/workbook.xml',ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml')
        cell_count=0
        for index,(title,rows) in enumerate(tables.items(),1):
            filename='sheet'+str(index)+('.payload' if mode=='adversarial' and index==1 else '.xml')
            ET.SubElement(sheets,'sheet',name=title,sheetId=str(index),attrib={'{'+rel+'}id':'rId'+str(index)})
            ET.SubElement(rels,'Relationship',Id='rId'+str(index),Type=rel+'/worksheet',Target='worksheets/'+filename)
            ET.SubElement(typesxml,'Override',PartName='/xl/worksheets/'+filename,ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml')
            sheet=ET.Element('worksheet',xmlns=ns)
            ET.SubElement(sheet,'dimension',ref='A1:'+chr(64+len(rows[0]))+str(len(rows)))
            data=ET.SubElement(sheet,'sheetData')
            for number,row in enumerate(rows,1):
                rowxml=ET.SubElement(data,'row',r=str(number))
                for column,cell in enumerate(row,1):
                    cell_count+=1;c=ET.SubElement(rowxml,'c',r=chr(64+column)+str(number))
                    value=cell.value
                    if value is None:continue
                    if type(value) is str:
                        c.set('t','inlineStr');ET.SubElement(ET.SubElement(c,'is'),'t').text=value
                    else:
                        if type(value) is bool:c.set('t','b')
                        ET.SubElement(c,'v').text=str(int(value)) if type(value) is bool else str(value)
            raw=ET.tostring(sheet,encoding='utf-8')
            if mode=='adversarial' and index==1:
                text=raw.decode().replace('Fictional Delta','&audit_entity;')
                text='<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE worksheet [<!ENTITY audit_entity "INDEPENDENT_AUTHORED_ENTITY_EXPANDED">]>'+text
                raw=text.encode('utf-16')
            members['xl/worksheets/'+filename]=raw
        members['xl/workbook.xml']=ET.tostring(book)
        members['xl/_rels/workbook.xml.rels']=ET.tostring(rels)
        members['[Content_Types].xml']=ET.tostring(typesxml)
        top=ET.Element('Relationships',xmlns=pkg)
        ET.SubElement(top,'Relationship',Id='rId1',Type=rel+'/officeDocument',Target='xl/workbook.xml')
        members['_rels/.rels']=ET.tostring(top)
        expanded=sum(map(len,members.values()));assert expanded<=67108864 and cell_count<=16000
        raw=authored.archive(members);assert len(raw)<=8388608
        source=authored.source(raw)
        try:
            result=p.read_candidate_bytes(raw,contract,source)
        except p.ParserRefused as error:
            if mode!='adversarial':raise
            # Fixed parser codes only; no cell/foreign exception strings.
            code=error.args[0] if len(error.args)==1 and type(error.args[0]) is str else 'UNKNOWN'
            summary={'kind':'INDEPENDENT_FEC_FRESH_READER','mode':mode,'refused':True,'code':code,'successful':code in ('XML_DTD_OR_ENTITY','XML_ENTITY','INVALID_WORKBOOK_ARCHIVE')}
        else:
            assert result['features']==[] and len(result['cohort'])==33 and all(result[k] is False for k in p.FALSE_FLAGS)
            observed=any(r['candidate_name']=='INDEPENDENT_AUTHORED_ENTITY_EXPANDED' for r in result['records'])
            summary={'kind':'INDEPENDENT_FEC_FRESH_READER','mode':mode,'refused':False,'entity_expanded_into_candidate_name':observed,'reader':result['reader'],'cohort_slots':33,'all_adoption_flags_false':True,'successful':mode=='baseline','output_bytes':len(p.packed(result))}
            assert len(p.packed(result))<=4194304
        summary.update({'fixture_cells':cell_count,'authored_zip_bytes':len(raw),'authored_expanded_bytes':expanded,'fixture_sha256':hashlib.sha256(raw).hexdigest()})
        exitcode=0 if summary['successful'] else 1
    usage=resource.getrusage(resource.RUSAGE_SELF)
    summary.update({'runtime':sys.version.split()[0],'wall_seconds':time.monotonic()-started,'CPU_seconds':usage.ru_utime+usage.ru_stime,'actual_workbook_reads':0,'owner_key_reads':0,'network_model_calls':0})
    print(json.dumps(summary,sort_keys=True));return exitcode


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['suite','baseline','adversarial'],required=True)
    raise SystemExit(main(parser.parse_args().mode))
