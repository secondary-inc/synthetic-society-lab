"""Distinct four-GET/4MiB metadata scope. No content downloads or retry.

Read only the correct project, its explicitly linked license and already-listed
replication-folder metadata, plus at most one returned pagination URL. Bodies
are kept only in ignored local cache; public summaries select catalog fields.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import http.client
import json
import ssl
import time
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
CACHE=ROOT/'data/processed/e02_human_anchor_rights_metadata_v1_20261116'
MAX_REQUESTS=4;MAX_BYTES=4194304
state={'requests':0,'response_bytes':0,'stopped_routes':[]}
context=ssl.create_default_context()


def save_new(path,value):
    raw=value if isinstance(value,bytes) else (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    with open(path,'xb') as stream:stream.write(raw)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def fetch(url,route,purpose):
    parts=urlsplit(url)
    assert parts.scheme=='https' and parts.hostname=='api.osf.io' and parts.username is None and parts.password is None
    assert parts.path.startswith(('/v2/nodes/xe28y/','/v2/licenses/'))
    assert state['requests']<MAX_REQUESTS and route not in state['stopped_routes']
    assert state['response_bytes']<MAX_BYTES
    state['requests']+=1;ordinal=state['requests'];started=time.monotonic()
    record={'kind':'E02_HUMAN_ANCHOR_RIGHTS_METADATA_REQUEST_V1','scope_ordinal':ordinal,'combined_ordinal':8+ordinal,'url':url,'route':route,'purpose':purpose,'method':'GET','retrieval_start_utc':datetime.now(timezone.utc).isoformat(),'remaining_response_bytes_before_request':MAX_BYTES-state['response_bytes'],'credentials':False,'redirect_following':False,'file_content_download':False}
    save_new(E/f'{ordinal:02d}-RESERVED.json',record)
    connection=None;body=b'';payload=None
    try:
        connection=http.client.HTTPSConnection(parts.hostname,timeout=20,context=context)
        connection.request('GET',parts.path+('?' +parts.query if parts.query else ''),headers={'User-Agent':'SyntheticSocietyLab-PublicMetadataCheck/1.0','Accept':'application/json','Accept-Encoding':'identity'})
        response=connection.getresponse();record['http_status']=response.status
        record['headers']={k.lower():v for k,v in response.getheaders() if k.lower() in {'content-type','content-length','location','last-modified','date','etag'}}
        if response.status in {401,403,429}:
            state['stopped_routes'].append(route);record['route_disposition']='DENIED_STOP_NO_RETRY'
        while True:
            remaining=MAX_BYTES-state['response_bytes']
            if remaining<=0:record['body_status']='BOUND_REACHED_NOT_COMPLETE';break
            part=response.read(min(65536,remaining))
            if not part:record['body_status']='COMPLETE';break
            body+=part;state['response_bytes']+=len(part)
        record['body_bytes']=len(body);record['body_sha256']=sha(body)
        cache_path=CACHE/f'{ordinal:02d}-RESPONSE.json'
        save_new(cache_path,body)
        record['private_body_cache']={'path':str(cache_path.relative_to(ROOT)),'bytes':len(body),'sha256':sha(body),'Git_allowed':False}
        if response.status==200 and record['body_status']=='COMPLETE':
            payload=json.loads(body)
    except BaseException as error:
        record['error_type']=type(error).__name__
        if route not in state['stopped_routes']:state['stopped_routes'].append(route)
        record['route_disposition']='ERROR_STOP_NO_RETRY'
    finally:
        if connection is not None:connection.close()
        record['elapsed_seconds']=time.monotonic()-started;record['retrieval_end_utc']=datetime.now(timezone.utc).isoformat()
        record['public_response_body_saved']=False
        save_new(E/f'{ordinal:02d}-OBSERVATION.json',record)
    return record,payload


def file_rows(value):
    rows=[]
    for node in value.get('data',[]):
        attrs=node.get('attributes',{});links=node.get('links',{});relationships=node.get('relationships',{})
        rows.append({'id':node.get('id'),'name':attrs.get('name'),'kind':attrs.get('kind'),'size_bytes':attrs.get('size'),'date_created':attrs.get('date_created'),'date_modified':attrs.get('date_modified'),'catalog_version':attrs.get('current_version'),'repository_reported_hashes':attrs.get('extra',{}).get('hashes',{}),'metadata_url':links.get('info',links.get('self')),'html_url':links.get('html'),'download_url_not_followed':links.get('download'),'child_metadata_url_not_followed':relationships.get('files',{}).get('links',{}).get('related',{}).get('href'),'contents_acquired':False})
    return rows


def main():
    assert not list(E.glob('*-RESERVED.json')) and not list(CACHE.glob('*-RESPONSE.json')),'SCOPE_NOT_REPLAYABLE'
    predecessor=ROOT/'reports/E02_HUMAN_ANCHOR_REPLICATION_AVAILABILITY_20261116.json'
    assert sha(predecessor.read_bytes())=='2c744473a592db12ece850305e453860510493ef23296b819476c0ae934448ee'
    project_record,project=fetch('https://api.osf.io/v2/nodes/xe28y/','CORRECT_PROJECT','Correct author-identified replication project metadata and its license relationship only.')
    summary={'kind':'E02_HUMAN_ANCHOR_RIGHTS_METADATA_V1_CLOSED','project':None,'license':None,'folder_pages':[],'file_inventory':[]}
    if project is not None:
        node=project.get('data',{});attrs=node.get('attributes',{});relationships=node.get('relationships',{})
        license_relationship=relationships.get('license',{})
        summary['project']={'request':project_record,'id':node.get('id'),'title':attrs.get('title'),'public':attrs.get('public'),'category':attrs.get('category'),'date_created':attrs.get('date_created'),'date_modified':attrs.get('date_modified'),'node_license':attrs.get('node_license'),'license_relationship':license_relationship,'html_url':node.get('links',{}).get('html')}
        license_url=license_relationship.get('links',{}).get('related',{}).get('href')
        if license_url and state['requests']<MAX_REQUESTS:
            record,value=fetch(license_url,'LINKED_PROJECT_LICENSE','Exact license metadata explicitly linked by project; not assumed to cover third-party stimuli.')
            if value is not None:
                license_node=value.get('data',{});license_attrs=license_node.get('attributes',{})
                text=license_attrs.get('text','')
                summary['license']={'request':record,'id':license_node.get('id'),'type':license_node.get('type'),'name':license_attrs.get('name'),'short_name':license_attrs.get('short_name'),'url':license_attrs.get('url'),'required_fields':license_attrs.get('required_fields'),'rights_text_chars':len(text),'rights_text_sha256':sha(text.encode()),'exact_rights_text_private_cache':record['private_body_cache'],'rights_text_publicly_reproduced':False}
                print(json.dumps({'linked_license_selected_metadata':summary['license']}))
    folder='https://api.osf.io/v2/nodes/xe28y/files/osfstorage/62cf3d1d588bb91920b8703b/?page%5Bsize%5D=100'
    if state['requests']<MAX_REQUESTS and state['response_bytes']<MAX_BYTES:
        record,value=fetch(folder,'REPLICATION_FOLDER','Already-cataloged Replication folder child metadata only; no file download/preview/render.')
        summary['folder_pages'].append({'request':record,'pagination':value.get('links') if value else None})
        if value is not None:
            summary['file_inventory'].extend(file_rows(value))
            next_url=value.get('links',{}).get('next')
            if next_url and state['requests']<MAX_REQUESTS and state['response_bytes']<MAX_BYTES:
                # A single returned continuation, never a guessed page/file URL.
                record,following=fetch(next_url,'REPLICATION_FOLDER','One explicitly returned metadata pagination URL; no content files.')
                summary['folder_pages'].append({'request':record,'pagination':following.get('links') if following else None})
                if following is not None:summary['file_inventory'].extend(file_rows(following))
    summary.update(accounting=state,limits={'requests':MAX_REQUESTS,'response_bytes':MAX_BYTES},prior_scope_untouched={'requests':8,'response_bytes':4561042},combined_actual={'requests':8+state['requests'],'response_bytes':4561042+state['response_bytes']},metadata_only=True,cost_usd=0)
    save_new(E/'CLOSED_METADATA.json',summary)
    print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
