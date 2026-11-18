"""One fresh optional-reader MOCK qualification; never opens the FEC workbook."""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import os
import resource
import signal
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def column(index):
    value = ""
    while index:
        index, remainder = divmod(index-1,26)
        value = chr(65+remainder)+value
    return value


def fixture(tables):
    """Small literal OOXML unit fixture, no publisher cells/formulas/macros."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        types = ET.Element("Types",xmlns="http://schemas.openxmlformats.org/package/2006/content-types")
        ET.SubElement(types,"Default",Extension="rels",ContentType="application/vnd.openxmlformats-package.relationships+xml")
        ET.SubElement(types,"Default",Extension="xml",ContentType="application/xml")
        ET.SubElement(types,"Override",PartName="/xl/workbook.xml",ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml")
        root_rels = ET.Element("Relationships",xmlns=PKG)
        ET.SubElement(root_rels,"Relationship",Id="rId1",Type=REL+"/officeDocument",Target="xl/workbook.xml")
        workbook = ET.Element("workbook",xmlns=NS)
        sheets = ET.SubElement(workbook,"sheets")
        book_rels = ET.Element("Relationships",xmlns=PKG)
        for index,(title,rows) in enumerate(tables.items(),1):
            name="xl/worksheets/sheet"+str(index)+".xml"
            ET.SubElement(types,"Override",PartName="/"+name,ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml")
            ET.SubElement(sheets,"sheet",name=title,sheetId=str(index),attrib={"{"+REL+"}id":"rId"+str(index)})
            ET.SubElement(book_rels,"Relationship",Id="rId"+str(index),Type=REL+"/worksheet",Target="worksheets/sheet"+str(index)+".xml")
            sheet=ET.Element("worksheet",xmlns=NS)
            ET.SubElement(sheet,"dimension",ref="A1:"+column(len(rows[0]))+str(len(rows)))
            data=ET.SubElement(sheet,"sheetData")
            for number,row in enumerate(rows,1):
                row_xml=ET.SubElement(data,"row",r=str(number))
                for c,cell in enumerate(row,1):
                    if cell.value is None:continue
                    attributes={"r":column(c)+str(number),"t":"inlineStr" if type(cell.value) is str else "n"}
                    node=ET.SubElement(row_xml,"c",attributes)
                    if type(cell.value) is str:ET.SubElement(ET.SubElement(node,"is"),"t").text=cell.value
                    else:ET.SubElement(node,"v").text=str(cell.value)
            archive.writestr(name,ET.tostring(sheet,encoding="utf-8"))
        for name,node in [("[Content_Types].xml",types),("_rels/.rels",root_rels),("xl/workbook.xml",workbook),("xl/_rels/workbook.xml.rels",book_rels)]:
            archive.writestr(name,ET.tostring(node,encoding="utf-8"))
    return stream.getvalue()


def main():
    started=time.monotonic()
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    signal.alarm(120)
    os.environ["OPENPYXL_LXML"]="False"
    os.environ["OPENPYXL_DEFUSEDXML"]="False"
    runtime_root=Path(sys.base_prefix).resolve()
    read_bytes=[0]
    def audit(event,args):
        if event.startswith("socket.") or event in {"subprocess.Popen","os.fork","os.posix_spawn","os.system","sqlite3.connect"}:
            raise AssertionError("FEC_READER_FIXTURE_NO_EXTERNAL")
        if event=="ctypes.dlopen" and args!=(None,):raise AssertionError("FEC_FIXTURE_NO_FOREIGN_NATIVE_LIBRARY")
        if event=="open" and not isinstance(args[0],int):
            path=Path(args[0]).resolve();flags=args[2]
            if path.name.startswith(".env") or "SyntheticSocietyLab" in str(path):raise AssertionError("FEC_NO_OWNER_OR_KEY")
            if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise AssertionError("FEC_FIXTURE_NO_DISK_WRITES")
            if not(path.is_relative_to(runtime_root) or path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'tests') or path==ROOT/'configs/e01_fec2020_senate_mapping_v1.json'):
                raise AssertionError("FEC_FIXTURE_READ_SCOPE")
            if path.is_file():read_bytes[0]+=path.stat().st_size
            if read_bytes[0]>67108864:raise AssertionError("FEC_FIXTURE_FILE_READ_BOUND")
    sys.addaudithook(audit)
    sys.path.insert(0,str(ROOT/'src'))
    path=ROOT/'tests/test_fec2020_parser_v1.py'
    spec=importlib.util.spec_from_file_location('fec_authored_reader_fixture',path)
    authored=importlib.util.module_from_spec(spec);spec.loader.exec_module(authored)
    p=authored.p
    contract=p.load_contract(ROOT/'configs/e01_fec2020_senate_mapping_v1.json')
    raw=fixture(authored.tables(contract))
    assert len(raw)<8388608
    result=p.read_candidate_bytes(raw,contract,authored.source(raw))
    assert result['reader']['backend']=='STDLIB_XML_ETREE_ELEMENTTREE'
    assert len(result['cohort'])==33 and result['features']==[]
    assert all(result[k] is False for k in p.FALSE_FLAGS)
    group=next(r for r in result['stage_controls'] if r['state']=='AL' and r['stage']=='GENERAL')
    assert group['candidate_sum']==20 and group['control']==20 and group['status']=='PASS_INTERNAL_COUNT'
    print(json.dumps({'kind':'FEC2020_OPTIONAL_READER_AUTHORED_FIXTURE_V1','status':'PASS_MOCK_READER_ONLY',
                      'provenance':'MOCK','runtime':sys.version.split()[0],'reader':result['reader'],
                      'fixture_zip_bytes':len(raw),'fixture_zip_sha256':hashlib.sha256(raw).hexdigest(),
                      'archive':result['archive'],'bounded_cells':15543,'file_read_reservation_bytes':read_bytes[0],
                      'cohort_slots':33,'features':0,'result_bytes':len(p.packed(result)),
                      'wall_seconds':time.monotonic()-started,'actual_workbooks_opened':0,
                      'network_calls':0,'model_calls':0,'cost_usd':0,**p.FALSE_FLAGS},sort_keys=True))


if __name__=='__main__':main()
