"""Read-only contract/cell-witness review; no election totals or parser adopted."""
from pathlib import Path
import json,hashlib,io,zipfile,xml.etree.ElementTree as ET,re,resource,signal,time
resource.setrlimit(resource.RLIMIT_CPU,(120,120));signal.alarm(120);root=Path.cwd();t=time.monotonic();checks={};refs=[];reads=0
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def read(p):
 global reads
 b=p.read_bytes();reads+=len(b);assert reads<=33554432;refs.append({'path':str(p.relative_to(root)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return b
def check(k,v):checks[k]=bool(v)
def packed(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
h=json.loads(read(root/'reports/E01_FEC2020_MAPPING_HANDOFF_20261118.json'))
for r in h['source_refs']:
 b=read(root/r['path']);check('handoff_pin:'+r['path'],len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'])
c=json.loads(read(root/'configs/e01_fec2020_senate_mapping_v1.json'))
for r in c['basis_refs']:
 b=read(root/r['path']);check('basis_pin:'+r['path'],len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'])
b=read(root/c['source']['path']);check('exact_workbook_identity',len(b)==c['source']['bytes']==6251110 and hashlib.sha256(b).hexdigest()==c['source']['sha256'])
with zipfile.ZipFile(io.BytesIO(b)) as z:
 check('archive_bounds',len(z.infolist())<=80 and sum(i.file_size for i in z.infolist())<=67108864 and len({i.filename for i in z.infolist()})==len(z.infolist()))
 def xml(name,cap):
  global reads
  info=z.getinfo(name);assert info.file_size<=cap
  data=z.read(name);reads+=len(data);assert reads<=33554432 and b'<!DOCTYPE' not in data and b'<!ENTITY' not in data;return ET.fromstring(data)
 ss=[''.join(n.text or '' for n in row.findall('.//s:t',ns)) for row in xml('xl/sharedStrings.xml',1048576)]
 cells={};formulas=0
 for no in (1,7,12,14):
  doc=xml(f'xl/worksheets/sheet{no}.xml',1048576);values={}
  for cell in doc.findall('.//s:sheetData/s:row/s:c',ns):
   formulas+=int(cell.find('s:f',ns) is not None);v=cell.find('s:v',ns);value=None if v is None else v.text
   if cell.attrib.get('t')=='s':value=ss[int(value)]
   elif value is not None and re.fullmatch(r'-?[0-9]+',value):value=int(value)
   values[cell.attrib['r']]=value
  cells[no]=values
 s,p,l,pub=cells[12],cells[7],cells[14],cells[1]
 check('four_sheets_no_formulas',formulas==0)
 check('GA_terms_separate',s['D84']=='S-FULL TERM' and s['D97']=='S-UNEXPIRED TERM')
 check('GA_runoff_later_year_footnotes',all('January 5, 2021' in s[f'X{r}'] for r in (84,92,97,98)))
 check('AK_party_identity_ambiguous_not_silently_D',s['K17']=='N(D)/D' and 'Nonpartisan' in s['X17'] and 'exclusion' in c['party_identity_rules']['AK'])
 check('MT_removed_marker_not_zero',s['P304']=='#' and 'removed' in s['X304'])
 check('MN_DFL_literal',s['K262']=='DFL')
 row29=[l.get(f'{col}29') for col in 'ABCDE'];check('DFL_party_label_row29',any(v=='DFL' for v in row29) and any(isinstance(v,str) and 'Democratic-Farmer-Labor' in v for v in row29))
 check('OR_combined_label_single_occurrence',s['K403']=='DEM/IP/WF' and 'Never split' in c['party_identity_rules']['OR'])
 check('NC_whitespace_subtotal_role',s['J386']=='Total State Votes:' and s['I386']==' ' and s['K386']==' ')
 check('blank_other_controls_remain_missing',p.get('G58') is None and p.get('G60') is None)
 check('no_data_combined_totals',all(s.get(f'T{r}') is None for r in range(2,543)))
 check('GA_summary_notes_multiple_terms',all('both full and unexpired' in p[f'A{r}'] for r in (68,70)))
 check('publication_month_literal',pub['A42']=='October 2022')
 check('source_witness_header_exact',[s.get(chr(65+i)+'1') for i in range(26)]==c['input_contract']['header_literal'])
 witness_hash=hashlib.sha256(packed({'GA':[s[f'X{r}'] for r in (84,92,97,98)],'AK':s['X17'],'MT':s['X304'],'DFL':row29,'GA_summary':[p[f'A{r}'] for r in (68,70)]})).hexdigest()
r=c['cohort']['official_class_source_candidate'];b=read(root/r['path']);check('class_capture_exact',len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']);text=b.decode();body=text.split('Democrats\n',1)[1].split('Article I',1)[0];states=re.findall(r'\([DR]-([A-Z]{2})\)',body);check('captured_classII_33_state_frame_matches',len(states)==len(set(states))==33 and set(states)==set(c['cohort']['expected_regular_class_II_states']));check('captured_term_text_matches', 'January 3, 2021' in text and 'January 3, 2027' in text)
check('no_adoption_execution_or_cost',all(c[k] is False for k in ('adoption','forecast_consumption','actual_parser_run','parser_implementation_exists_claimed')) and c['model_calls']==c['cost_usd']==0)
check('bounded_ranges_fit_cell_cap',542*26+78*7+121*5+150*2==15543<=c['implementation_bounds_proposed']['range_cells_max'])
check('separate_methods_parser_numeric_gates',set(x['id'] for x in c['acceptance_criteria'])=={'FEC-M01','FEC-P01','FEC-P02','FEC-A01','FEC-A02','FEC-S01'})
result={'status':'PASS' if all(checks.values()) else 'BLOCKED','checks':checks,'refs':refs,'selected_witness_sha256':witness_hash,'numeric_vote_totals_computed':False,'source_adoption':False,'model_calls':0,'network_calls':0,'workbook_writes':0,'logical_read_bytes':reads,'wall_seconds':time.monotonic()-t,'class_capture_limitation':'Content/hash/frame agreement only; not fresh server authenticity, candidate identity or independent pre-results availability.'}
(root/'reports/evidence_independent_fec2020_mapping_methods_20261118/METHODS_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'checks':checks,'read_bytes':reads,'wall_seconds':result['wall_seconds']},sort_keys=True))
