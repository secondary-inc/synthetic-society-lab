"""Bounded source-readiness metadata/ZIP/header review; no totals adopted."""
from pathlib import Path
import hashlib,json,zipfile,re,xml.etree.ElementTree as ET,csv,posixpath,time,resource,signal
resource.setrlimit(resource.RLIMIT_CPU,(60,60));signal.alarm(120);t=time.monotonic();root=Path.cwd();out=root/'reports/evidence_independent_source_readiness_20261118';checks={};refs=[];read_bytes=0
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/package/2006/relationships'}
def read(p):
 global read_bytes
 b=p.read_bytes();read_bytes+=len(b);assert read_bytes<=33554432;refs.append({'path':str(p.relative_to(root)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return b
def check(k,v):checks[k]=bool(v)
def xml(b):
 assert b'<!DOCTYPE' not in b and b'<!ENTITY' not in b;return ET.fromstring(b)
report=json.loads(read(root/'reports/E01_FEC2020_WORKBOOK_DISCOVERY_20261118.json'));a=report['acquisition'];book=root/'data/raw/e01_fec2020_workbook_20261118/federalelections2020.xlsx';raw=read(book)
check('workbook_exact_identity',len(raw)==a['bytes']==6251110 and hashlib.sha256(raw).hexdigest()==a['sha256']=='5073b6d2c76c86c941508dfb1a11cc497e8529b0068c5132aceb0f385c19352e')
check('not_adopted_no_forecast_or_model',report['adoption'] is False and report['forecast_consumption'] is False and report['new_model_requests']==report['model_cost_usd']==0)
with zipfile.ZipFile(book) as z:
 info=z.infolist();check('65_unique_archive_members',len(info)==len({i.filename for i in info})==a['zip_members']==65);check('declared_expansion_matches',sum(i.file_size for i in info)==a['declared_expanded_bytes']==51902709)
 def zread(name,cap):
  global read_bytes
  i=z.getinfo(name);assert i.file_size<=cap and not(i.flag_bits&1)
  with z.open(i) as f:b=f.read(cap+1)
  assert len(b)==i.file_size;read_bytes+=len(b);assert read_bytes<=33554432;return b
 wb=xml(zread('xl/workbook.xml',65536));rels=xml(zread('xl/_rels/workbook.xml.rels',65536));relmap={r.attrib['Id']:r.attrib['Target'] for r in rels};sheets=[];targets={}
 for sheet in wb.find('s:sheets',ns):
  title=sheet.attrib['name'];rel=sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'];target=posixpath.normpath('xl/'+relmap[rel]);assert target.startswith('xl/worksheets/') and '..' not in target.split('/');targets[title]=target
  with z.open(target) as f:prefix=f.read(16384)
  read_bytes+=len(prefix);dim=re.search(rb'<dimension\s+ref="([A-Z]+)([0-9]+):([A-Z]+)([0-9]+)"',prefix)
  assert dim is not None
  col=0
  for c in dim.group(3).decode():col=col*26+ord(c)-64
  sheets.append({'title':title,'declared_rows':int(dim.group(4)),'declared_columns':col})
 check('all19_sheet_names_and_declared_dimensions',sheets==report['workbook_sheets'] and len(sheets)==19)
 strings=[ ''.join(t.text or '' for t in si.findall('.//s:t',ns)) for si in xml(zread('xl/sharedStrings.xml',1048576)) ]
 sr=zread(targets[report['senate_sheet']['title']],1048576);check('Senate_declared_range_A1_Z542',b'<dimension ref="A1:Z542"' in sr)
 root_tag=re.search(rb'<worksheet\b[^>]*>',sr).group(0);row=re.search(rb'<row\b[^>]*\br="1"[^>]*>.*?</row>',sr,re.S).group(0);node=xml(root_tag+b'<sheetData>'+row+b'</sheetData></worksheet>');header=[None]*26
 for cell in node.findall('.//s:c',ns):
  label=re.match(r'([A-Z]+)1$',cell.attrib['r']).group(1);col=0
  for c in label:col=col*26+ord(c)-64
  if col>26:continue
  v=cell.find('s:v',ns);value=None if v is None else v.text
  if cell.attrib.get('t')=='s':value=strings[int(value)]
  elif value is not None and re.fullmatch(r'-?[0-9]+',value):value=int(value)
  header[col-1]=value
 check('Senate_A1_Z1_header_exact',header==report['senate_sheet']['header']);formula_count=len(re.findall(rb'<(?:[A-Za-z0-9_]+:)?f(?:\s|>)',sr));check('Senate_formula_tag_count_exact',formula_count==report['senate_sheet']['formula_cells_in_inspected_range']==0)
 check('separate_general_runoff_combined_labels_present',header[15]=='GENERAL VOTES ' and header[17]=='GE RUNOFF ELECTION VOTES (GA, LA)' and header[19]=='COMBINED GE PARTY TOTALS (when applicable)')
v=json.loads(read(root/'data/processed/validation/source-integrity-20261118.json'));check('validation_receipt_93_PASS',v['status']=='PASS' and len(v['checks'])==93 and all(c['status']=='PASS' for c in v['checks']));check('validation_limitation_explicit','Byte integrity only' in v['limitation'])
g=json.loads(read(root/'data/processed/gdelt/fixture-20261118.json'));craw=read(root/'data/processed/gdelt/fixture-20261118.csv');check('GDELT_csv_hash_matches_JSON_receipt',hashlib.sha256(craw).hexdigest()==g['csv_summary']['sha256'])
rows=list(csv.DictReader(craw.decode().splitlines()));check('GDELT_JSON_CSV_868_rows',len(rows)==len(g['records'])==868);check('GDELT_records_and_dates_preserved',all(r['record_id']==j['record_id'] and r['published_at_utc']=='' and j['published_at_utc'] is None and r['forecast_admissible'].lower()=='false' and j['forecast_admissible'] is False for r,j in zip(rows,g['records'])));check('GDELT_metadata_not_news_text',g['not_news_text'] is True and g['kind']=='INGESTION_FIXTURE')
result={'status':'PASS' if all(checks.values()) else 'BLOCKED','checks':checks,'refs':refs,'workbook_schema_summary':{'sheet_count':len(sheets),'Senate_range':'A1:Z542','independently_verified_header_range':'A1:Z1','header_columns':len(header),'Senate_formula_tags':formula_count,'numeric_election_totals_adopted':False,'candidate_party_or_district_row_counts_recomputed':False},'validation_scope':'Existing93-check receipt verified for count/status only; no independent rerun of full raw-source inventory.','GDELT_source_sha256_as_recorded':g['source_sha256'],'logical_read_bytes':read_bytes,'wall_seconds':time.monotonic()-t,'network_calls':0,'workbook_writes':0,'model_calls':0,'source_adoption':False}
(out/'SOURCE_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'checks':checks,'logical_read_bytes':read_bytes,'wall_seconds':result['wall_seconds']},sort_keys=True))
