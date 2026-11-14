from __future__ import annotations
import argparse, copy, gzip, hashlib, json, math, os, re, tempfile, time, urllib.request, uuid
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from decimal import Decimal, InvalidOperation

def decode_sec_text(data,charset=None):
    if charset:
        try: return data.decode(charset)
        except LookupError as exc: raise ValueError('Unsupported document charset') from exc
    try: return data.decode('utf-8')
    except UnicodeDecodeError: return data.decode('cp1252')

class NoAutomaticRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None

class SecClient:
    requests_per_second = 5
    def __init__(self, user_agent):
        if not user_agent.strip(): raise ValueError('SEC_USER_AGENT is required in .env')
        self.headers={'User-Agent':user_agent, 'Accept-Encoding':'identity'}
        self.last=0.0
        self.opener=urllib.request.build_opener(NoAutomaticRedirects())
    def get(self,url):
        if not re.match(r'^https://(?:www\.sec\.gov|data\.sec\.gov)/',url): raise ValueError('SEC hosts only')
        wait=1/self.requests_per_second-(time.monotonic()-self.last)
        if wait>0: time.sleep(wait)
        self.last=time.monotonic()
        with self.opener.open(urllib.request.Request(url,headers=self.headers),timeout=30) as response:
            charset=response.headers.get_content_charset()
            return decode_sec_text(response.read(),charset)

class CachedIndexClient:
    """Reuse recent SEC index responses; filing documents are always fetched live."""
    def __init__(self,client,folder,ttl=3600,clock=time.time):
        if isinstance(ttl,bool) or not isinstance(ttl,(int,float)) or not math.isfinite(ttl) or ttl<=0: raise ValueError('Invalid index cache duration')
        self.client=client; self.folder=Path(folder); self.ttl=ttl; self.clock=clock
    def get(self,url):
        if not re.match(r'^https://(?:www\.sec\.gov|data\.sec\.gov)/',url): raise ValueError('SEC hosts only')
        if not re.fullmatch(r'https://www\.sec\.gov/Archives/edgar/full-index/\d{4}/QTR[1-4]/form\.idx',url): return self.client.get(url)
        path=self.folder/(hashlib.sha256(url.encode('utf-8')).hexdigest()+'.json.gz')
        now=self.clock()
        try:
            with gzip.open(path,'rt',encoding='utf-8') as stream: saved=json.load(stream)
            age=now-float(saved['fetched_at'])
            if saved.get('url')==url and isinstance(saved.get('content'),str) and 0<=age<self.ttl: return saved['content']
        except (OSError,ValueError,TypeError,KeyError,EOFError): pass
        content=self.client.get(url)
        if not isinstance(content,str): raise ValueError('Invalid index response')
        temporary=None
        try:
            self.folder.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=self.folder,suffix='.tmp',delete=False) as stream: temporary=Path(stream.name)
            with gzip.open(temporary,'wt',encoding='utf-8') as stream:
                json.dump({'url':url,'fetched_at':now,'content':content},stream,ensure_ascii=False)
            os.replace(temporary,path); temporary=None
        except OSError: pass
        finally:
            if temporary is not None:
                try: temporary.unlink(missing_ok=True)
                except OSError: pass
        return content

def parse_index(text):
    output=[]
    pattern=re.compile(r'^(10-12B(?:/A)?|10-12G(?:/A)?|10/A|10|CERT|8-K(?:/A)?|10-Q|10-K|4)\s+(.+?)\s+(\d{1,10})\s+(\d{4}-\d\d-\d\d)\s+(edgar/data/\S+\.txt)\s*$')
    for line in text.splitlines():
        m=pattern.match(line.strip())
        if m:
            form,name,cik,day,path=m.groups(); output.append({'form':form,'name':name.strip(),'cik':cik.zfill(10),'date':day,'path':path})
    return output

def folder_url(row):
    m=re.fullmatch(r'edgar/data/(\d{1,10})/(\d{10}-\d{2}-\d{6})\.txt',row['path'])
    if not m or int(m.group(1)) != int(row['cik']): raise ValueError('Invalid filing path')
    return 'https://www.sec.gov/Archives/edgar/data/'+str(int(m.group(1)))+'/'+m.group(2).replace('-','')+'/'

def filing_documents(folder_json):
    result=[]
    for item in json.loads(folder_json)['directory']['item']:
        name=item.get('name','')
        if re.fullmatch(r'[A-Za-z0-9_.-]+\.(?:htm|html|txt|xml)',name,re.I) and name not in {'.','..'}:
            result.append(name)
    return result

def discover_index(client, year, quarter):
    if not isinstance(year,int) or year < 1994 or quarter not in (1,2,3,4): raise ValueError('Invalid index period')
    url=f'https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/form.idx'
    contents=client.get(url)
    match=re.search(r'^Last Data Received:\s*(.+?)\s*$',contents,re.M)
    index_date=None
    if match:
        try: index_date=datetime.strptime(match.group(1).strip(),'%B %d, %Y').date().isoformat()
        except ValueError: pass
    return parse_index(contents), index_date

def collect_indices(client,first_year,end,event_start=None):
    if event_start is not None: date.fromisoformat(event_start)
    if first_year < 1994 or first_year > end.year: raise ValueError('Invalid first index year')
    rows=[]; latest=None; problems=[]
    for year in range(first_year,end.year+1):
        for quarter in range(1,5):
            if year == 1994 and quarter < 3: continue
            if year == end.year and quarter > (end.month-1)//3+1: break
            try:
                found, index_date=discover_index(client,year,quarter)
            except (OSError,ValueError) as exc:
                if getattr(exc,'code',None) in (403,429): raise
                problems.append(f'{year} Q{quarter}: {type(exc).__name__}'); continue
            if index_date and date.fromisoformat(index_date)<=end and (not latest or index_date>latest): latest=index_date
            if not index_date: problems.append(f'{year} Q{quarter}: index date unavailable')
            forms={'10','10/A','10-12B','10-12B/A','10-12G','10-12G/A','CERT','8-K','8-K/A'}
            rows.extend(row for row in found if row['date']<=end.isoformat() and row['form'] in forms and (row['form'] not in {'8-K','8-K/A'} or event_start is None or row['date']>=event_start))
    return rows,latest,problems

def group_candidates(rows):
    forms={'10','10/A','10-12B','10-12B/A','10-12G','10-12G/A'}
    ids={r['cik'] for r in rows if r['form'] in forms}
    grouped={cik:[] for cik in ids}
    for row in rows:
        if row['cik'] in grouped: grouped[row['cik']].append(row)
    for records in grouped.values(): records.sort(key=lambda r:(r['date'],r['path']))
    return grouped

def submission_text_documents(content):
    """Read named text documents from an SEC complete-submission SGML file."""
    found={}; duplicates=set()
    for match in re.finditer(r'(?ims)^<DOCUMENT>\s*$([\s\S]*?)^</DOCUMENT>\s*$',content):
        block=match.group(1)
        name=re.search(r'(?im)^<FILENAME>\s*([^\r\n<]+)',block)
        start=re.search(r'(?im)^<TEXT>\s*',block)
        if not name or not start: continue
        end=re.search(r'(?im)^</TEXT>\s*$',block[start.end():])
        if not end: continue
        filename=name.group(1).strip()
        if not re.fullmatch(r'[A-Za-z0-9_.-]+\.(?:htm|html|txt|xml)',filename,re.I): continue
        text=block[start.end():start.end()+end.start()]
        if re.match(r'\s*(?:begin\s+\d{3}\s|<PDF>|<ZIP>)',text,re.I): continue
        if filename in found: duplicates.add(filename)
        else: found[filename]=text
    for filename in duplicates: found.pop(filename,None)
    return found

def read_filing_folder(client,row):
    from urllib.parse import quote
    folder=folder_url(row)
    index=client.get(folder+'index.json')
    names=filing_documents(index)
    submission_name=row['path'].rsplit('/',1)[-1]
    embedded={}; submission_content=None; submission_error=None
    if submission_name in names:
        try:
            submission_content=client.get(folder+quote(submission_name))
            embedded=submission_text_documents(submission_content)
        except (OSError,ValueError) as exc:
            if getattr(exc,'code',None) in (403,429): raise
            submission_error=type(exc).__name__
    docs=[]
    if names==[submission_name]:
        if embedded:
            for name,text in embedded.items():
                docs.append({'url':folder+quote(submission_name),'text':text,'embedded_filename':name})
        else:
            docs.append({'url':folder+quote(submission_name),'text':submission_content,'error':submission_error})
    for name in names:
        if name==submission_name: continue
        url=folder+quote(name)
        if name in embedded:
            docs.append({'url':url,'text':embedded[name]})
            continue
        try:
            docs.append({'url':url,'text':client.get(url)})
        except (OSError,ValueError) as exc:
            if getattr(exc,'code',None) in (403,429): raise
            docs.append({'url':url,'text':None,'error':type(exc).__name__})
    if names!=[submission_name]:
        for name,text in embedded.items():
            if name not in names:
                docs.append({'url':folder+quote(submission_name),'text':text,'embedded_filename':name})
    if submission_content:
        embedded_names=set(re.findall(r'(?im)^<FILENAME>\s*([^\r\n<]+)',submission_content))
        for raw_name in embedded_names:
            name=raw_name.strip()
            if name not in embedded and name not in names:
                safe_name=name if re.fullmatch(r'[A-Za-z0-9_.-]{1,200}',name) else '[invalid embedded filename]'
                docs.append({'url':folder+quote(submission_name),'text':None,'embedded_filename':safe_name,'error':'Unparsed embedded attachment: '+safe_name})
    for item in json.loads(index)['directory']['item']:
        name=item.get('name','')
        if name not in ('.','..') and name not in names:
            docs.append({'url':folder+quote(name,safe=''),'text':None,'error':'Unsupported or invalid attachment name'})
    return docs

def html_text(content):
    class Reader(HTMLParser):
        def __init__(self): super().__init__(convert_charrefs=True); self.skip=0; self.parts=[]
        def handle_starttag(self,tag,attrs):
            if tag in {'script','style'}: self.skip+=1
            if tag in {'p','div','br','tr','li','h1','h2','h3'}: self.parts.append('\n')
            if tag in {'td','th'}: self.parts.append(' ')
        def handle_endtag(self,tag):
            if tag in {'script','style'} and self.skip: self.skip-=1
            if tag in {'p','div','tr','li','h1','h2','h3'}: self.parts.append('\n')
        def handle_data(self,data):
            if not self.skip: self.parts.append(data)
    reader=Reader(); reader.feed(content)
    return '\n'.join(' '.join(line.split()) for line in ''.join(reader.parts).splitlines() if line.strip())

def extract_labeled_evidence(text,filing):
    """Return every recognized, sourced label, including conflicting values."""
    if not filing: raise ValueError('Filing URL required')
    labels={'parent':'parent','parent cik':'parent_cik','distribution ratio':'distribution_ratio',
            'record date':'record_date','distribution date':'distribution_date'}
    found={}
    for line in text.splitlines():
        match=re.fullmatch(r'\s*(parent|parent cik|distribution ratio|record date|distribution date)\s*:\s*(.{1,250}?)\s*',line,re.I)
        if not match: continue
        label,raw=match.groups(); key=labels[label.lower()]; val=raw.strip()
        if key in {'record_date','distribution_date'}:
            try: val=datetime.strptime(val,'%B %d, %Y').date().isoformat()
            except ValueError:
                try: val=date.fromisoformat(val).isoformat()
                except ValueError: continue
        elif key=='parent_cik':
            if not val.isdigit() or len(val)>10: continue
            val=val.zfill(10)
        elif val.lower() in {'unknown','none','n/a','to be announced'}: continue
        found.setdefault(key,[]).append({'value':val,'filing':filing,'section':label,'quote':line.strip()})
    return found

def extract_labeled_facts(text,filing):
    """Resolve labels only when all recognized values agree."""
    found=extract_labeled_evidence(text,filing)
    return {key: entries[0] for key,entries in found.items() if len({e['value'] for e in entries})==1}

def fact(value, filing, section):
    if value is None or value == '': return None
    if not filing or not section: raise ValueError('Every fact needs a filing and section')
    return {'value':value,'filing':filing,'section':section}

def new_registry_path(folder):
    timestamp=datetime.now().astimezone().strftime('%Y-%m-%d_%H-%M-%S_%f_%z')
    return Path(folder)/('registry-'+timestamp+'_'+uuid.uuid4().hex[:8]+'.json')

class Registry:
    fields=('parent','parent_cik','distribution_ratio','record_date','distribution_date')
    def __init__(self,path,autosave=True):
        self.path=Path(path)
        self.data=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}
        self.autosave=autosave
        self.dirty=False

    def ensure_entity(self,cik):
        if not str(cik).isdigit() or len(str(cik))>10: raise ValueError('Invalid CIK')
        entity=self.data.setdefault(str(cik).zfill(10),{})
        for key in self.fields:
            if key not in entity:
                entity[key]=[]
                self.dirty=True
        if self.autosave: self.flush()

    def record(self,cik,key,evidence):
        if evidence is None: return
        if not isinstance(evidence,dict) or evidence.get('value') in (None,'') or not evidence.get('filing') or not evidence.get('section'):
            raise ValueError('Fact requires value, filing and section')
        if not str(cik).isdigit() or len(str(cik))>10: raise ValueError('Invalid CIK')
        entry=self.data.setdefault(str(cik).zfill(10),{}).setdefault(key,[])
        if evidence not in entry:
            entry.append(dict(evidence)); self.dirty=True
        if self.autosave: self.flush()

    def flush(self):
        if not self.dirty: return
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.path.parent,suffix='.tmp',delete=False) as stream:
                temporary=Path(stream.name)
                json.dump(self.data,stream,indent=2,ensure_ascii=False)
                stream.write('\n')
            for attempt in range(5):
                try:
                    os.replace(temporary,self.path)
                    temporary=None
                    self.dirty=False
                    break
                except PermissionError:
                    if attempt==4: raise
                    time.sleep(0.05*(2**attempt))
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)

    def entries(self,cik,key,as_of=None):
        entries=self.data.get(str(cik).zfill(10),{}).get(key,[])
        if as_of is None: return list(entries)
        if not isinstance(as_of,date) or isinstance(as_of,datetime): raise ValueError('as_of must be a date')
        result=[]
        for entry in entries:
            try:
                if date.fromisoformat(entry['filing_date'])<=as_of: result.append(entry)
            except (KeyError,TypeError,ValueError): continue
        return result

    def evidence(self,cik,key,as_of=None):
        entries=self.entries(cik,key,as_of)
        values={json.dumps(x['value'],sort_keys=True) for x in entries}
        return entries[-1] if len(values)==1 else None

    def resolved(self,cik,key,as_of=None):
        evidence=self.evidence(cik,key,as_of)
        return evidence['value'] if evidence is not None else None

    def conflicts(self,cik,as_of=None):
        return sorted(k for k in self.data.get(str(cik).zfill(10),{}) if len({json.dumps(x['value'],sort_keys=True) for x in self.entries(cik,k,as_of)})>1)

def value(record,key):
    item=record.get(key)
    return item.get('value') if isinstance(item,dict) else None

def is_dropped(record):
    rejection=record.get('rejection')
    if not rejection or not rejection.get('reason') or not rejection.get('filing'): return False
    evidence=record.get('spinoff_evidence') or {}
    return not (evidence.get('filing') and evidence.get('date','')>rejection.get('date',''))

def rejection_from_evidence(evidence):
    kind=evidence.get('kind')
    if kind not in {'no information statement','fund','already owned shares'} or not evidence.get('filing') or evidence.get('complete') is not True: return None
    if kind != 'no information statement' and not evidence.get('section'): return None
    return {'reason':kind,'filing':evidence['filing'],'section':evidence.get('section','entire filing folder')}

def company_name_pattern(name):
    words=name.strip().rstrip('.').split()
    if not words: return ''
    suffixes={'co':r'(?:co\.?|company)','company':r'(?:co\.?|company)',
              'corp':r'(?:corp\.?|corporation)','corporation':r'(?:corp\.?|corporation)',
              'inc':r'(?:inc\.?|incorporated)','incorporated':r'(?:inc\.?|incorporated)'}
    tail=suffixes.get(words[-1].lower())
    if tail and len(words)>1:
        return r'\s+'.join(re.escape(w.rstrip(',')) for w in words[:-1])+r',?\s+'+tail
    return re.escape(name)

def distribution_statement(text,parent,registrant):
    if not parent or not registrant or len(parent)>200 or len(registrant)>200: return False
    p=company_name_pattern(parent); r=company_name_pattern(registrant)
    planned=re.search(rf'\b{p}\s+(?:will|intends to|plans to)\s+distribute\s+(?:its\s+|the\s+)?(?:shares|common stock)\s+of\s+{r}\b[^.\n]{{0,180}}\b(?:its\s+)?(?:shareholders|stockholders)\b',text,re.I)
    completed=re.search(rf'\b{p}(?:\s*\([^\n)]{{1,50}}\))?\s+completed\b[^\n]{{0,300}}\bdistribution\b[^\n]{{0,300}}\bof\s+{r}\b[^\n]{{0,160}}\b(?:shareholders|stockholders)\b',text,re.I)
    return bool(planned or completed)

def extract_letter_facts(text,filing,registrant):
    """Extract a narrow shareholder-letter pattern without treating a plan as completed."""
    if not filing or not registrant: return {}
    normalized=' '.join(text.split())
    if not re.search(r'\binformation\s+statement\b',normalized,re.I): return {}
    opening=normalized[:12000]
    letter=re.search(r'\bDear\s+(?P<parent>[A-Za-z0-9][A-Za-z0-9&., -]{1,100}?)\s+Shareholder\s*:',opening,re.I)
    if not letter: return {}
    parent=letter.group('parent').strip()
    parent_pattern=company_name_pattern(parent)
    quote_chars='["\u201c\u201d\u2018\u2019\\x27]'
    announcement=rf'\bOn\s+[A-Za-z]+\s+\d{{1,2}},\s+\d{{4}},\s+{parent_pattern}\s*\(\s*{quote_chars}(?P<alias>[A-Za-z0-9. -]{{1,40}}?){quote_chars}\s*\)\s+announced\s+its\s+plan\s+to\s+separate\b'
    found=re.search(announcement,opening,re.I)
    if not found: return {}
    parent_alias=found.group('alias').strip()
    context=opening[found.start():found.start()+1800]
    child_pattern=company_name_pattern(registrant)
    child=re.search(rf'\bnewly\s+formed\s+company\s*,\s*{child_pattern}\s*\(\s*{quote_chars}(?P<alias>[A-Za-z0-9. -]{{1,40}}?){quote_chars}\s*\)',context,re.I)
    distribution=re.search(rf'\bdistribution\s+by\s+{re.escape(parent_alias)}\b',context,re.I)
    if not child or not distribution or distribution.start()>child.start(): return {}
    child_alias=child.group('alias').strip()
    result={'parent':[{'value':parent,'filing':filing,'section':'Shareholder letter','quote':context[:600]}]}
    share_context=opening[found.start():found.start()+5000]
    numbers=r'(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+(?:\.\d+)?)'
    pattern=rf'\bEach\s+{re.escape(parent_alias)}\s+shareholder\b[^.]{{0,300}}?\bon\s+([A-Za-z]+\s+\d{{1,2}},\s+\d{{4}})\s*,\s*the\s+record\s+date\s+for\s+the\s+distribution\s*,\s*will\s+receive\s+({numbers}\s+shares?\s+of\s+{re.escape(child_alias)}\s+common\s+stock\s+for\s+every\s+{numbers}\s+shares?\s+of\s+{re.escape(parent_alias)}\s+common\s+stock)'
    facts=re.search(pattern,share_context,re.I)
    if facts:
        try: record_day=datetime.strptime(facts.group(1),'%B %d, %Y').date().isoformat()
        except ValueError: return result
        entry={'filing':filing,'section':'Shareholder letter','quote':facts.group(0)}
        result['record_date']=[dict(entry,value=record_day)]
        result['distribution_ratio']=[dict(entry,value=facts.group(2))]
    return result

def extract_separation_letter_facts(text,filing,registrant):
    """Extract a second narrow planned-separation shareholder-letter pattern."""
    if not filing or not registrant: return {}
    normalized=' '.join(text.split())
    if not re.search(r'\binformation\s+statement\b',normalized,re.I): return {}
    opening=normalized[:16000]
    salutation=re.search(r'\bDear\s+(?P<alias>[A-Za-z0-9. -]{1,40}?)\s+Stockholder\s*:',opening,re.I)
    if not salutation: return {}
    parent_alias=salutation.group('alias').strip()
    quotes='["\u201c\u201d\u2018\u2019\\x27]'
    parent_pattern=rf'\bplan\s+to\s+separate\s+(?P<parent>[A-Za-z0-9][A-Za-z0-9&., -]{{1,100}}?(?:Inc\.?|Incorporated|Co\.?|Company|Corp\.?|Corporation))\s*\(\s*{quotes}{re.escape(parent_alias)}{quotes}\s*\)'
    parent=re.search(parent_pattern,opening[salutation.end():],re.I)
    if not parent: return {}
    parent_name=parent.group('parent').strip()
    context=opening[salutation.end()+parent.start():salutation.end()+parent.start()+2000]
    child_pattern=company_name_pattern(registrant)
    child=re.search(rf'{child_pattern}\s*\(\s*{quotes}(?P<alias>[A-Za-z0-9. -]{{1,40}}?){quotes}\s*\)',context,re.I)
    if not child: return {}
    child_alias=child.group('alias').strip()
    distribution=rf'\bdistribution\s+to\s+{re.escape(parent_alias)}\s+stockholders\s+of\b.{{0,240}}?\bshares\s+of\s+common\s+stock\s+of\s+{re.escape(child_alias)}\b'
    if not re.search(distribution,context[child.end():],re.I): return {}
    result={'parent':[{'value':parent_name,'filing':filing,'section':'Shareholder letter','quote':context[:800]}]}
    ratio_pattern=rf'\bEach\s+{re.escape(parent_alias)}\s+stockholder\s+will\s+receive\s+(?P<ratio>(?:one|\d+)\s+share\s+of\s+{re.escape(child_alias)}\s+common\s+stock\s+on\s+the\s+date\s+of\s+the\s+distribution\s+for\s+every\s+(?:one\s+)?share\s+of\s+{re.escape(parent_alias)}\s+common\s+stock)\s+held\s+as\s+of\s+the\s+close\s+of\s+business\s+on\s+(?P<day>[A-Za-z]+\s+\d{{1,2}},\s+\d{{4}})\s*,\s*the\s+record\s+date\s+for\s+the\s+distribution'
    facts=re.search(ratio_pattern,opening[salutation.end():],re.I)
    if facts:
        try: record_day=datetime.strptime(facts.group('day'),'%B %d, %Y').date().isoformat()
        except ValueError: return result
        entry={'filing':filing,'section':'Shareholder letter','quote':facts.group(0)}
        result['record_date']=[dict(entry,value=record_day)]
        result['distribution_ratio']=[dict(entry,value=facts.group('ratio'))]
    return result

def completed_distribution_date(text,filing,parent,registrant):
    """Extract only a dated completion statement in the parent's Item 2.01."""
    if not filing or not parent or not registrant: return None
    normalized=' '.join(text.split())
    heading=re.search(r'\bItem\s+2\.01\b',normalized,re.I)
    if not heading: return None
    section=normalized[heading.end():]
    other=re.search(r'\bItem\s+\d+\.\d+\b',section,re.I)
    if other: section=section[:other.start()]
    parent_pattern=company_name_pattern(parent)
    pattern=rf'\bOn\s+([A-Za-z]+\s+\d{{1,2}},\s+\d{{4}})\s*,\s*{parent_pattern}(?:\s*\([^)]{{1,50}}\))?\s+completed\b'
    candidates=[]
    for match in re.finditer(pattern,section,re.I):
        excerpt=section[match.start():match.start()+900]
        if not distribution_statement(excerpt,parent,registrant): continue
        try: day=datetime.strptime(match.group(1),'%B %d, %Y').date().isoformat()
        except ValueError: continue
        candidates.append({'value':day,'filing':filing,'section':'Item 2.01','quote':excerpt[:600]})
    values={c['value'] for c in candidates}
    if len(values)==1: return candidates[0]
    if values: return None
    return completed_intro_distribution_date(normalized,filing,parent,registrant)

def completed_intro_distribution_date(text,filing,parent,registrant):
    intro=re.search(r'\bIntroductory\s+Note\s*\.',text,re.I)
    if not intro: return None
    following=text[intro.end():]
    item=re.search(r'\bItem\s*2\.01\b',following,re.I)
    if not item: return None
    note=following[:item.start()]
    item_text=following[item.end():item.end()+600]
    if not re.search(r'\bIntroductory\s+Note\b[^.]{0,250}\bis\s+incorporated\s+by\s+reference\b',item_text,re.I): return None
    quotes='["\u201c\u201d\u2018\u2019\\x27]'
    p=company_name_pattern(parent); child=company_name_pattern(registrant)
    pattern=rf'\bon\s+([A-Za-z]+\s+\d{{1,2}},\s+\d{{4}})\s*(?:\([^)]{{1,80}}\)\s*,\s*)?{p}\s*(?:\(\s*{quotes}(?P<alias>[A-Za-z0-9. -]{{1,40}}?){quotes}\s*\))?\s+completed\b'
    completed=re.search(pattern,note,re.I)
    if not completed: return None
    child_and_company=rf'{child}\s*\(\s*(?:the\s+)?{quotes}Company{quotes}\s*\)'
    if not re.search(child_and_company,note[completed.end():completed.end()+600],re.I): return None
    owner=re.escape(completed.group('alias').strip()) if completed.group('alias') else p
    distribution=rf'\bpro\s+rata\s+distribution\b.{{0,450}}?\bshares\b.{{0,200}}?\bof\s+the\s+Company\b.{{0,300}}?\bto\s+holders\b.{{0,300}}?\bof\s+{owner}\b'
    if not re.search(distribution,note[completed.end():],re.I): return None
    try: day=datetime.strptime(completed.group(1),'%B %d, %Y').date().isoformat()
    except ValueError: return None
    return {'value':day,'filing':filing,'section':'Introductory Note (incorporated into Item 2.01)','quote':note[completed.start():completed.start()+1200]}

def proves_trading(form): return form in {'10-Q','10-K','4'}

def submissions(client,cik,since):
    if not str(cik).isdigit() or len(str(cik))>10: raise ValueError('Invalid CIK')
    date.fromisoformat(since)
    cik=str(cik).zfill(10)
    base='https://data.sec.gov/submissions/'
    main=json.loads(client.get(base+'CIK'+cik+'.json'))
    records=[]
    def add(columns):
        forms=columns['form']; dates=columns['filingDate']; accessions=columns['accessionNumber']
        if not (len(forms)==len(dates)==len(accessions)): raise ValueError('Malformed SEC submissions')
        for form,day,accession in zip(forms,dates,accessions):
            date.fromisoformat(day)
            if day>=since:
                records.append({'form':form,'date':day,'cik':cik,'path':f'edgar/data/{int(cik)}/{accession}.txt'})
    add(main['filings']['recent'])
    for item in main['filings'].get('files',[]):
        name=item.get('name','')
        if not re.fullmatch(r'CIK\d{10}-submissions-\d+\.json',name): raise ValueError('Invalid submissions history path')
        if item.get('filingTo','9999-12-31')>=since: add(json.loads(client.get(base+name)))
    return records

def parent_8ks(client,parent_cik,since):
    return [r for r in submissions(client,parent_cik,since) if r['form'] in ('8-K','8-K/A')]

def parent_cik_candidates(parent,ticker_data):
    pattern=company_name_pattern(' '.join(str(parent).split()))
    matches={str(row['cik_str']).zfill(10) for row in ticker_data.values() if pattern and re.fullmatch(pattern,' '.join(str(row.get('title','')).split()),re.I) and str(row.get('cik_str','')).isdigit()}
    return sorted(matches)

def fetch_company_tickers(client):
    result=json.loads(client.get('https://www.sec.gov/files/company_tickers.json'))
    if not isinstance(result,dict): raise ValueError('Invalid SEC ticker list')
    return result

def parent_header_matches(text,parent,cik):
    blocks=re.split(r'(?im)^\s*COMPANY CONFORMED NAME:\s*',text)
    for block in blocks[1:]:
        lines=block.splitlines()
        if not lines or not re.fullmatch(company_name_pattern(' '.join(parent.split())),' '.join(lines[0].split()),re.I): continue
        found=re.search(r'^\s*CENTRAL INDEX KEY:\s*(\d{1,10})\s*$',block,re.I|re.M)
        if found and found.group(1).zfill(10)==str(cik).zfill(10): return True
    return False

def find_parent_cik(client,parent,ticker_data,as_of=None):
    matches=parent_cik_candidates(parent,ticker_data)
    if len(matches)!=1: return None
    cik=matches[0]
    if as_of is not None and (not isinstance(as_of,date) or isinstance(as_of,datetime)): raise ValueError('as_of must be a date')
    cutoff=as_of or date.today()
    checked=set()
    recent=f'{max(1994,cutoff.year-2)}-01-01'
    for since in dict.fromkeys((recent,'1994-01-01')):
        filings=submissions(client,cik,since)
        for row in sorted(filings,key=lambda r:r['date'],reverse=True):
            if row['form'] not in {'10-K','10-Q','8-K'} or row['path'] in checked or date.fromisoformat(row['date'])>cutoff: continue
            checked.add(row['path'])
            url='https://www.sec.gov/Archives/'+row['path']
            if parent_header_matches(client.get(url),parent,cik):
                return {'value':cik,'filing':url,'section':'SEC filing header: company name and CIK','filing_date':row['date']}
    return None

def has_trading_evidence(rows,cik):
    return any(str(row.get('cik','')).zfill(10)==str(cik).zfill(10) and proves_trading(row.get('form','')) for row in rows)

def inspect_candidate(client,cik,rows,registry,since,ticker_data=None,as_of=None):
    if as_of is not None and (not isinstance(as_of,date) or isinstance(as_of,datetime)): raise ValueError('as_of must be a date')
    if as_of is not None: rows=[r for r in rows if date.fromisoformat(r['date'])<=as_of]
    registration_forms={'10','10/A','10-12B','10-12B/A','10-12G','10-12G/A'}
    registrations=[r for r in rows if r['form'] in registration_forms]
    if not registrations: raise ValueError('Candidate has no Form 10 registration')
    registry.ensure_entity(cik)
    name=registrations[-1]['name']; gaps=[]; texts=[]; letter_evidence=[]; registration_complete=True
    def read(row):
        nonlocal registration_complete
        try: documents=read_filing_folder(client,row)
        except (OSError,ValueError,KeyError) as exc:
            if getattr(exc,'code',None) in (403,429): raise
            gaps.append(f"Could not read filing {row['path']}: {type(exc).__name__}")
            if row['form'] in registration_forms: registration_complete=False
            return
        if not documents and row['form'] in registration_forms: registration_complete=False
        for doc in documents:
            if doc.get('text') is None:
                gaps.append(f"Could not read document {doc['url']}: {doc.get('error','unknown error')}")
                if row['form'] in registration_forms: registration_complete=False
                continue
            try:
                content=html_text(doc['text']) if '<' in doc['text'] else doc['text']
            except (AssertionError,ValueError) as exc:
                gaps.append(f"Could not parse document {doc['url']}: {type(exc).__name__}")
                if row['form'] in registration_forms: registration_complete=False
                continue
            embedded_name=doc.get('embedded_filename')
            texts.append((row,doc['url'],content,embedded_name))
            def sourced(entry):
                result=dict(entry,filing_date=row['date'])
                if embedded_name: result['section']=embedded_name+': '+result['section']
                return result
            other=row['cik'].zfill(10)!=str(cik).zfill(10)
            if other and not re.search(company_name_pattern(name),content,re.I):
                continue
            if not other:
                if row['form'] in registration_forms:
                    for key,entries in extract_labeled_evidence(content,doc['url']).items():
                        for entry in entries: registry.record(cik,key,sourced(entry))
                if row['form'] in registration_forms:
                    letter_facts=extract_letter_facts(content,doc['url'],name) or extract_separation_letter_facts(content,doc['url'],name)
                    for key,entries in letter_facts.items():
                        for entry in entries: registry.record(cik,key,sourced(entry))
                    if letter_facts.get('parent'):
                        entry=sourced(letter_facts['parent'][0])
                        letter_evidence.append({'filing':doc['url'],'date':row['date'],'section':entry['section'],'quote':entry['quote'],'status':'planned'})
            if row['form'] in ('8-K','8-K/A'):
                recorded_parent=registry.resolved(cik,'parent',as_of=as_of)
                recorded_parent_cik=registry.resolved(cik,'parent_cik',as_of=as_of)
                if recorded_parent and (not other or (recorded_parent_cik and str(recorded_parent_cik).zfill(10)==row['cik'].zfill(10))):
                    completed=completed_distribution_date(content,doc['url'],recorded_parent,name)
                    if completed: registry.record(cik,'distribution_date',sourced(completed))
    for row in registrations: read(row)
    for row in (r for r in rows if r['form']=='CERT'): read(row)
    parent=registry.resolved(cik,'parent',as_of=as_of)
    for row in (r for r in rows if r['form'] in ('8-K','8-K/A')): read(row)
    parent_cik=registry.resolved(cik,'parent_cik',as_of=as_of)
    if parent and not parent_cik and ticker_data is not None:
        try:
            resolved=find_parent_cik(client,parent,ticker_data,as_of=as_of) if as_of is not None else find_parent_cik(client,parent,ticker_data)
            if resolved:
                registry.record(cik,'parent_cik',resolved)
                parent_cik=resolved['value']
        except (OSError,ValueError,KeyError) as exc:
            if getattr(exc,'code',None) in (403,429): raise
            gaps.append(f'Could not verify parent CIK: {type(exc).__name__}')
    if parent_cik:
        try:
            for event in parent_8ks(client,parent_cik,min(since,min(r['date'] for r in registrations))):
                if as_of is None or date.fromisoformat(event['date'])<=as_of: read(event)
        except (OSError,ValueError,KeyError) as exc:
            if getattr(exc,'code',None) in (403,429): raise
            gaps.append(f'Could not read parent submissions: {type(exc).__name__}')
    else: gaps.append('Parent CIK not established; parent distribution filings were not searched.')
    evidence=max(letter_evidence,key=lambda e:e['date']) if parent and letter_evidence else None
    if parent:
        for row,url,content,embedded_name in texts:
            for line in content.splitlines():
                if distribution_statement(line,parent,name):
                    candidate={'filing':url,'date':row['date'],'section':((embedded_name+': ') if embedded_name else '')+'distribution statement','quote':line}
                    if evidence is None or candidate['date']>evidence['date']: evidence=candidate
    listing_evidence=None
    listing_pattern=rf'\b{company_name_pattern(name)}\s+(?:(?:has\s+been|is|was)\s+)?approved\s+for\s+listing\b'
    for listing_row,url,content,embedded_name in texts:
        if listing_row['form']!='CERT': continue
        match=re.search(listing_pattern,content,re.I)
        if match:
            listing_evidence={'filing':url,'date':listing_row['date'],'section':((embedded_name+': ') if embedded_name else '')+'listing statement','quote':match.group(0)}
            break
    listing=bool(listing_evidence)
    trading_evidence=None
    try:
        own_filings=submissions(client,cik,min(since,min(r['date'] for r in registrations)))
        if as_of is not None: own_filings=[r for r in own_filings if date.fromisoformat(r['date'])<=as_of]
        qualifying=[r for r in own_filings if str(r.get('cik','')).zfill(10)==str(cik).zfill(10) and proves_trading(r.get('form','')) and r.get('path') and r.get('date')]
        if qualifying:
            item=min(qualifying,key=lambda r:r['date'])
            trading_evidence={'filing':'https://www.sec.gov/Archives/'+item['path'],'date':item['date'],'form':item['form']}
        trading=True if trading_evidence else None
        if trading is None and as_of is not None:
            for evidence_row,url,content,embedded_name in texts:
                if evidence_row['cik'].zfill(10)!=str(cik).zfill(10) or evidence_row['date']!=as_of.isoformat(): continue
                for line in content.splitlines():
                    match=re.fullmatch(r'\s*As\s+of\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}),\s+our\s+common\s+stock\s+is\s+not\s+trading\s+on\s+any\s+exchange\.?\s*',line,re.I)
                    if not match: continue
                    try: statement_date=datetime.strptime(match.group(1),'%B %d, %Y').date()
                    except ValueError: continue
                    if statement_date==as_of:
                        trading=False
                        trading_evidence={'filing':url,'date':evidence_row['date'],'section':((embedded_name+': ') if embedded_name else '')+'Trading status statement','quote':line.strip()}
                        break
                if trading is False: break
        if trading is None: gaps.append(f'{name}: trading status not established by company filings')
    except (OSError,ValueError,KeyError) as exc:
        if getattr(exc,'code',None) in (403,429): raise
        trading=None; gaps.append(f'Could not read new company submissions: {type(exc).__name__}')
    insider_evidence=[]
    for owner_row,url,content,embedded_name in texts:
        if owner_row['cik'].zfill(10)!=str(cik).zfill(10): continue
        for entry in extract_insider_statements(content,url,owner_row['date']):
            if embedded_name: entry['section']=embedded_name+': '+entry['section']
            if entry not in insider_evidence: insider_evidence.append(entry)
    record={'name':name,'cik':str(cik).zfill(10),'trading':trading,'trading_evidence':trading_evidence,'listing':listing,'listing_evidence':listing_evidence,'spinoff_evidence':evidence,'insider_evidence':insider_evidence,'factors':{}}
    registration_texts=[content for row,url,content,embedded_name in texts if row['form'] in registration_forms]
    for row,url,content,embedded_name in texts:
        if row['form'] not in registration_forms: continue
        normalized=' '.join(content.split())
        bdc=re.search(rf'\b(?:(?:the\s+)?registrant|{re.escape(name)})\s+is\s+filing\b[^.]{{0,500}}\bto\s+permit\s+it\s+to\s+file\s+an\s+election\s+to\s+be\s+regulated\s+as\s+a\s+business\s+development\s+company\b',normalized,re.I)
        if bdc and re.search(r'\b(?:not|never|without|except)\b|\brather\s+than\b',bdc.group(0),re.I): bdc=None
        if bdc:
            record['rejection']={'reason':'fund','filing':url,'date':row['date'],'section':((embedded_name+': ') if embedded_name else '')+'registration statement','quote':bdc.group(0)}
            break
        for line in content.splitlines():
            kind=None
            if re.search(r'\b(?:the\s+)?(?:registrant|company)\s+is\s+(?:a|an)\s+(?:registered\s+)?(?:investment company|mutual fund|closed.end fund)\b',line,re.I): kind='fund'
            if re.fullmatch(r'\s*(?:this\s+filing\s+is\s+)?registering\s+shares\s+already\s+owned\s+by\s+(?:selling\s+)?(?:stockholders|shareholders)\.?\s*',line,re.I): kind='already owned shares'
            if re.fullmatch(r'\s*(?:the\s+)?registrant\s+is\s+registering\s+shares\s+that\s+it\s+already\s+owns\.?\s*',line,re.I): kind='already owned shares'
            if kind:
                record['rejection']={'reason':kind,'filing':url,'date':row['date'],'section':((embedded_name+': ') if embedded_name else '')+'registration statement','quote':line}
                break
        if record.get('rejection'): break
    if 'rejection' not in record and registration_complete and registration_texts and not any(re.search(r'\binformation\s+statement\b',content,re.I) for content in registration_texts):
        record['rejection']={'reason':'no information statement','filing':folder_url(registrations[-1]),'date':registrations[-1]['date'],'section':'filing folder'}
    for key in ('parent','parent_cik','distribution_date','record_date','distribution_ratio'):
        record[key]=registry.evidence(cik,key,as_of=as_of)
        if not record[key]: gaps.append(f'{name}: {key} unavailable or conflicted')
    if not evidence: gaps.append(f'{name}: a parent distribution was not established')
    return record,gaps

def stage(record,today,window):
    if record.get('trading'):
        d=value(record,'distribution_date')
        if d:
            delta=(today-date.fromisoformat(d)).days
            if 0<=delta<=window: return 'in its window'
            if delta>window: return 'past it'
        return 'trading'
    return 'listing approved' if record.get('listing') else 'registered'

def first_close(quotes, distribution, coverage_start=None, coverage_end=None):
    distribution_day=date.fromisoformat(distribution)
    try:
        start=date.fromisoformat(coverage_start); end=date.fromisoformat(coverage_end)
    except (TypeError,ValueError): return None
    if start>distribution_day or end<=distribution_day: return None
    valid=[]; unknown=[]
    for item in quotes:
        try:
            day=date.fromisoformat(item['date'])
            if not distribution_day<day<=end: continue
            number=float(item['close'])
            if not math.isfinite(number) or number<=0: return None
            if item.get('when_issued') is False and item.get('basis')=='official_unadjusted' and item.get('source'):
                valid.append((day,number,item))
            elif item.get('when_issued') is not True: unknown.append(day)
        except (KeyError,TypeError,ValueError): return None
    if not valid: return None
    first_day=min(x[0] for x in valid)
    if any(day<=first_day for day in unknown): return None
    matches=[x for x in valid if x[0]==first_day]
    if len({x[1] for x in matches})!=1: return None
    return matches[0][2]

def validate_config(config):
    if not isinstance(config.get('window_days'),int) or config['window_days']<0: raise ValueError('window_days must be a nonnegative integer')
    factors=config.get('factors')
    if not isinstance(factors,list) or not factors: raise ValueError('Add at least one factor')
    used=set()
    for f in factors:
        if not f.get('name') or f['name'] in used or f.get('direction') not in {'higher','lower'} or not isinstance(f.get('weight'),(int,float)) or isinstance(f.get('weight'),bool) or not math.isfinite(f['weight']) or f['weight']<0: raise ValueError('Invalid factor')
        if not isinstance(f.get('threshold'),(int,float)) or isinstance(f.get('threshold'),bool) or not math.isfinite(f['threshold']): raise ValueError('Invalid factor threshold')
        used.add(f['name'])

def rank(records,factors):
    good=[]; bad=[]
    for source in records:
        r=dict(source); missing=[]
        for f in (f for f in factors if f['weight'] != 0):
            v=r.get('factors',{}).get(f['name'])
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v): missing.append(f['name'])
        if missing:
            entry={'name':r['name'],'reason':'missing factors: '+', '.join(missing)}
            if r.get('latest_close'): entry['latest_close']=r['latest_close']
            bad.append(entry); continue
        good.append(r)
    for r in good:
        r['points']={}
        for f in (f for f in factors if f['weight'] != 0):
            v=r['factors'][f['name']]
            meets = v >= f['threshold'] if f['direction']=='higher' else v <= f['threshold']
            r['points'][f['name']]=float(f['weight']) if meets else 0.0
        r['total']=sum(r['points'].values())
    return sorted(good,key=lambda r:(-r['total'],r['name'])),bad

def extract_insider_statements(text,filing,filing_date):
    """Read explicit, dated director-and-officer group ownership statements."""
    if not filing: return []
    try: filed=date.fromisoformat(filing_date)
    except (TypeError,ValueError): return []
    normalized=' '.join(text.split())
    pattern=(r'\bAs\s+of\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}),\s+our\s+'
             r'(?:directors\s+and\s+executive\s+officers|executive\s+officers\s+and\s+directors)\s+'
             r'as\s+a\s+group\s+beneficially\s+owned\s+(\d+(?:\.\d+)?)\s*%\s+'
             r'of\s+our\s+outstanding\s+common\s+stock\b')
    facts=[]
    for match in re.finditer(pattern,normalized,re.I):
        before=normalized[max(0,match.start()-8000):match.start()]
        if not re.search(r'\bsecurity\s+ownership\s+of\s+certain\s+beneficial\s+owners\s+and\s+management\b',before,re.I): continue
        try:
            day=datetime.strptime(match.group(1),'%B %d, %Y').date(); number=Decimal(match.group(2))
        except (ValueError,InvalidOperation): continue
        if day>filed or not number.is_finite() or not 0<=number<=100: continue
        facts.append({'value':str(number),'as_of':day.isoformat(),'filing_date':filing_date,
                      'filing':filing,'section':'Security ownership of certain beneficial owners and management','quote':match.group(0)})
    return facts

def select_insider_statement(entries,price_date):
    try: cutoff=date.fromisoformat(price_date)
    except (TypeError,ValueError): return None
    eligible=[]
    for entry in entries:
        try:
            asof=date.fromisoformat(entry['as_of']); filed=date.fromisoformat(entry['filing_date']); number=Decimal(str(entry['value']))
            if not entry.get('filing') or not entry.get('section') or asof>filed or filed>cutoff or not number.is_finite() or not 0<=number<=100: continue
            eligible.append((asof,filed,number,entry))
        except (TypeError,ValueError,KeyError,InvalidOperation): continue
    if not eligible: return None
    latest=max(item[0] for item in eligible)
    observations=[item for item in eligible if item[0]==latest]
    if len({item[2] for item in observations})!=1: return None
    return max(observations,key=lambda item:item[1])[3]

def fetch_companyfacts(client,cik):
    if not str(cik).isdigit() or len(str(cik))>10: raise ValueError('Invalid CIK')
    return json.loads(client.get('https://data.sec.gov/api/xbrl/companyfacts/CIK'+str(cik).zfill(10)+'.json'))

def shares_from_companyfacts(document,cik,price_date):
    """Use only a nonconflicting share count reported for the exact price date."""
    if not str(cik).isdigit() or len(str(cik))>10: raise ValueError('Invalid CIK')
    target=date.fromisoformat(price_date)
    try:
        if int(document['cik'])!=int(cik): return None
    except (KeyError,TypeError,ValueError): return None
    try: observations=document['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares']
    except (KeyError,TypeError): return None
    if not isinstance(observations,list): return None
    valid=[]
    for row in observations:
        try:
            if row.get('end')!=price_date or date.fromisoformat(row['filed'])>target: continue
            if date.fromisoformat(row['filed'])<target or row.get('form') not in {'10-K','10-K/A','10-Q','10-Q/A','8-K','8-K/A','10-12B','10-12B/A','10-12G','10-12G/A'}: continue
            if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',row['accn']) or isinstance(row['val'],bool): continue
            number=Decimal(str(row['val']))
            if not number.is_finite() or number<=0 or number!=number.to_integral_value(): continue
            valid.append((number,row))
        except (KeyError,TypeError,ValueError,InvalidOperation): continue
    if not valid or len({number for number,row in valid})!=1: return None
    number,row=valid[-1]
    return {'value':int(number),'as_of':price_date,'filing_date':row['filed'],
            'filing':f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{row['accn']}.txt",
            'section':'XBRL dei:EntityCommonStockSharesOutstanding (shares)'}

def verify_regular_listing(evidence,client):
    """Verify a narrowly worded regular-way listing in the issuer's SEC filing."""
    from urllib.parse import urlparse
    cik=str(evidence.get('cik','')); ticker=str(evidence.get('ticker','')).strip()
    exchange=str(evidence.get('exchange','')).strip(); url=str(evidence.get('listing_url',''))
    if not cik.isdigit() or not re.fullmatch(r'[A-Za-z0-9.\-]{1,20}',ticker) or not exchange: return False
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.netloc!='www.sec.gov' or parsed.query or parsed.fragment: return False
    match=re.fullmatch(r'/Archives/edgar/data/(\d+)/(\d{18})/[A-Za-z0-9_.-]+',parsed.path)
    if not match or int(match.group(1))!=int(cik): return False
    content=html_text(client.get(url))
    for sentence in re.split(r'(?<=[.!?])\s+|\n+',content):
        if len(sentence)>1000: continue
        if not re.search(r'\bregular[ -]way\s+trading\b',sentence,re.I): continue
        if not re.search(r'(?<![A-Za-z0-9])'+re.escape(ticker)+r'(?![A-Za-z0-9])',sentence,re.I): continue
        if not re.search(r'(?<![A-Za-z0-9])'+re.escape(exchange)+r'(?![A-Za-z0-9])',sentence,re.I): continue
        if re.search(r'\b(?:not|never|unless|if|may|could|expected|anticipate|subject to)\b',sentence,re.I): continue
        return True
    return False

def verified_export_snapshot(record,today,reader,client):
    """Build a dated snapshot from a declared, spot-checked export and SEC facts.

    The export's declared coverage and identity are user-supplied; its one spot
    check does not independently prove every observation or its full history.
    """
    from closes_reader import WorkspaceExportReader
    if not isinstance(reader,WorkspaceExportReader): raise TypeError('A spot-checked Workspace export reader is required')
    cik=str(record.get('cik',''))
    if not cik.isdigit() or not str(reader.mapping.get('cik','')).isdigit() or int(cik)!=int(reader.mapping['cik']):
        raise ValueError('Export CIK must match the registrant')
    distribution=value(record,'distribution_date')
    if not distribution: raise ValueError('Distribution date unavailable')
    day=date.fromisoformat(distribution)
    if not isinstance(today,date) or isinstance(today,datetime) or today<=day: raise ValueError('No post-distribution date available')
    rows=reader.daily_closes(reader.ticker,distribution,today.isoformat())
    source='Workspace export: declared regular-way, unadjusted official close; one exchange value spot-checked'
    quotes=[dict(row,when_issued=False,basis='official_unadjusted',source=source) for row in rows]
    first=first_close(quotes,distribution,reader.coverage_start.isoformat(),reader.coverage_end.isoformat())
    eligible=[row for row in quotes if day<date.fromisoformat(row['date'])<=today]
    last=max(eligible,key=lambda row:row['date']) if eligible else None
    snapshot={'first':first,'last':last,'shares':None}
    if last:
        try: snapshot['shares']=shares_from_companyfacts(fetch_companyfacts(client,cik),cik,last['date'])
        except (OSError,ValueError,KeyError) as exc:
            if getattr(exc,'code',None) in (403,429): raise
    return snapshot

class WorkspaceLiveProvider:
    """Use the user's LSEG close-field and primary-RIC assumptions for scoring."""
    def __init__(self,workspace,sec_client,ticker_data):
        self.workspace=workspace; self.sec_client=sec_client; self.ticker_data=ticker_data

    def __call__(self,record,today):
        from closes_reader import WorkspaceCandidateReader,completed_close_end,EASTERN
        cik=str(record.get('cik',''))
        if not cik.isdigit(): raise ValueError('Registrant CIK unavailable')
        symbols={str(row.get('ticker','')).strip().upper() for row in self.ticker_data.values()
                 if str(row.get('cik_str','')).isdigit() and int(row['cik_str'])==int(cik)}
        if len(symbols)!=1: raise ValueError('SEC ticker mapping missing or ambiguous')
        ticker=next(iter(symbols))
        if not re.fullmatch(r'[A-Z0-9.\-]{1,20}',ticker): raise ValueError('Invalid SEC ticker')
        found=self.workspace.discovery.search(query=ticker,view=self.workspace.discovery.Views.EQUITY_QUOTES,
            select='RIC,TickerSymbol,ExchangeName,IsPrimaryRIC,AssetState',top=100).to_dict('records')
        quotes=[row for row in found if str(row.get('TickerSymbol','')).strip().upper()==ticker
                and str(row.get('IsPrimaryRIC','')).casefold() in {'true','1'}
                and str(row.get('AssetState','')).strip().upper()=='AC'
                and row.get('ExchangeName') and row.get('RIC')]
        if len(quotes)!=1: raise ValueError('LSEG primary quote missing or ambiguous')
        distribution=value(record,'distribution_date')
        if not distribution: raise ValueError('Distribution date unavailable')
        end=completed_close_end(today.isoformat(),datetime.now(EASTERN))
        if date.fromisoformat(end)<=date.fromisoformat(distribution): raise ValueError('No completed post-distribution close')
        rows=WorkspaceCandidateReader(self.workspace).daily_closes(str(quotes[0]['RIC']),distribution,end)
        eligible=[row for row in rows if date.fromisoformat(row['date'])>date.fromisoformat(distribution)]
        source='LSEG TR.CLOSEPRICE(Adjusted=0); primary RIC and regular-way status based on supplied LSEG assumptions'
        def priced(row): return {'date':row['date'],'close':row['close'],'when_issued':False,'basis':'official_unadjusted','source':source}
        snapshot={'first':dict(priced(eligible[0]),verified_first=True) if eligible else None,
                  'last':priced(eligible[-1]) if eligible else None}
        if snapshot['last'] and self.sec_client is not None:
            try: snapshot['shares']=shares_from_companyfacts(fetch_companyfacts(self.sec_client,cik),cik,snapshot['last']['date'])
            except (OSError,ValueError,KeyError) as exc:
                if getattr(exc,'code',None) in (403,429): raise
        return snapshot

class WorkspaceOfficialProvider:
    """Connect independently checked Workspace official closes to the score snapshot."""
    def __init__(self,workspace,sec_client,evidence_by_cik):
        if not isinstance(evidence_by_cik,dict): raise ValueError('Evidence must be a CIK mapping')
        self.workspace=workspace; self.sec_client=sec_client; self.evidence={}
        for key,entry in evidence_by_cik.items():
            if not str(key).isdigit() or not isinstance(entry,dict) or not str(entry.get('cik','')).isdigit() or int(key)!=int(entry['cik']):
                raise ValueError('Invalid listing evidence CIK')
            normalized=str(int(key))
            if normalized in self.evidence: raise ValueError('Duplicate CIK evidence')
            self.evidence[normalized]=dict(entry)

    def __call__(self,record,today):
        from closes_reader import WorkspaceOfficialReader,completed_close_end,EASTERN
        cik=str(record.get('cik',''))
        if not cik.isdigit() or str(int(cik)) not in self.evidence: raise ValueError('Listing and exchange evidence unavailable')
        distribution=value(record,'distribution_date')
        if not distribution: raise ValueError('Distribution date unavailable')
        end=completed_close_end(today.isoformat(),datetime.now(EASTERN))
        reader=WorkspaceOfficialReader(self.workspace,self.evidence[str(int(cik))],lambda evidence:verify_regular_listing(evidence,self.sec_client))
        snapshot=reader.factor_snapshot(cik,distribution,end)
        last=snapshot.get('last')
        if last:
            try: snapshot['shares']=shares_from_companyfacts(fetch_companyfacts(self.sec_client,cik),cik,last['date'])
            except (OSError,ValueError,KeyError) as exc:
                if getattr(exc,'code',None) in (403,429): raise
        return snapshot

def factor_inputs(distribution,first,last,shares,insiders):
    """Build only factors with dated inputs; keep raw price series out of output."""
    factors={}; explanations={}
    try: distribution_day=date.fromisoformat(distribution)
    except (TypeError,ValueError): return factors,explanations
    def price(item):
        try:
            if not item or item.get('when_issued') is not False or item.get('basis')!='official_unadjusted' or not item.get('source'): return None
            day=date.fromisoformat(item['date']); number=Decimal(str(item['close']))
            if day<=distribution_day or not number.is_finite() or number<=0: return None
            return day,number
        except (KeyError,ValueError,InvalidOperation,TypeError): return None
    first_value=price(first); last_value=price(last)
    if first_value and last_value and first.get('verified_first') is True and first_value[0]<=last_value[0]:
        decline=(first_value[1]-last_value[1])*100/first_value[1]
        factors['weakness']=float(decline)
        explanations['weakness']=f"(first regular close after distribution − close on {last_value[0]}) / first regular close × 100 = {decline}% (first close retained only in code)."
    def sourced(item):
        try:
            if not item or not item.get('filing') or not item.get('section'): return None
            day=date.fromisoformat(item['as_of']); filed=date.fromisoformat(item['filing_date']); number=Decimal(str(item['value']))
            if not last_value or day>filed or filed>last_value[0] or not number.is_finite(): return None
            return day,number
        except (KeyError,ValueError,InvalidOperation,TypeError): return None
    share_value=sourced(shares)
    if last_value and share_value and share_value[0]==last_value[0] and share_value[1]>0:
        capitalization=share_value[1]*last_value[1]
        factors['size']=float(capitalization)
        explanations['size']=f"{share_value[1]} shares × USD {last_value[1]} per share on {last_value[0]} = USD {capitalization}; shares: {shares['filing']} ({shares['section']})."
    insider_value=sourced(insiders)
    if last_value and insider_value and insider_value[0]<=last_value[0] and 0<=insider_value[1]<=100:
        factors['insiders']=float(insider_value[1])
        explanations['insiders']=f"{insider_value[1]}% as of {insider_value[0]}; {insiders['filing']} ({insiders['section']})."
    return factors,explanations

def enrich_factor_inputs(record,snapshot,today):
    """Compute sourced factor values from a caller-supplied in-memory snapshot."""
    result=dict(record)
    result['factors']={}
    result.pop('latest_close',None)
    result.pop('factor_explanations',None)
    if not isinstance(snapshot,dict): raise ValueError('Factor snapshot must be a mapping')
    def at_or_before(item,key):
        try: return isinstance(item,dict) and date.fromisoformat(item[key])<=today
        except (KeyError,TypeError,ValueError): return False
    first=snapshot.get('first') if at_or_before(snapshot.get('first'),'date') else None
    last=snapshot.get('last') if at_or_before(snapshot.get('last'),'date') else None
    shares=snapshot.get('shares') if at_or_before(snapshot.get('shares'),'as_of') else None
    insider_entries=list(record.get('insider_evidence') or [])
    if isinstance(snapshot.get('insiders'),dict): insider_entries.append(snapshot['insiders'])
    insiders=select_insider_statement(insider_entries,last['date']) if last else None
    distribution=value(record,'distribution_date')
    factors,explanations=factor_inputs(distribution,first,last,shares,insiders)
    result['factors']=factors
    result['factor_explanations']=explanations
    try:
        day=date.fromisoformat(last['date']); n=Decimal(str(last['close']))
        if day>date.fromisoformat(distribution) and n.is_finite() and n>0 and last.get('when_issued') is False and last.get('basis')=='official_unadjusted' and last.get('source'):
            result['latest_close']={'date':day.isoformat(),'close':str(n)}
    except (TypeError,ValueError,KeyError,InvalidOperation): pass
    return result

def prepare_screen(records,start,today,window,factors):
    start_day=date.fromisoformat(start)
    active=[]; watch=[]; unranked=[]
    for source in records:
        if is_dropped(source): continue
        r=dict(source)
        distribution=value(r,'distribution_date')
        if distribution is None:
            reason='distribution date unavailable or conflicted'
            if r.get('trading') is None: reason+='; trading status unknown'
            unranked.append({'name':r['name'],'reason':reason})
            if r.get('trading') is False:
                entry={'name':r['name'],'stage':stage(r,today,window)}
                if r.get('trading_evidence'): entry['evidence']=r['trading_evidence']
                if r.get('listing_evidence'): entry['listing_evidence']=r['listing_evidence']
                watch.append(entry)
            continue
        day=date.fromisoformat(distribution)
        if day < start_day: continue
        status=stage(r,today,window)
        if r.get('trading') is None:
            unranked.append({'name':r['name'],'reason':'trading status unknown'})
            continue
        if r.get('trading') is False:
            entry={'name':r['name'],'stage':status}
            if r.get('trading_evidence'): entry['evidence']=r['trading_evidence']
            if r.get('listing_evidence'): entry['listing_evidence']=r['listing_evidence']
            watch.append(entry)
            continue
        if status=='in its window':
            r['distribution_evidence']=r.get('distribution_date')
            r['parent_evidence']=r.get('parent')
            r['distribution_date']=distribution
            r['parent']=value(r,'parent')
            r['window_ends']=(day+timedelta(days=window)).isoformat()
            active.append(r)
    ranked,missing=rank(active,factors)
    return ranked,watch,unranked+missing

def compare_weight_scenarios(records,start,today,window,factors,disabled_factor):
    """Compare two scores from the same in-memory records; return no raw prices."""
    validate_config({'window_days':window,'factors':factors})
    selected=[f for f in factors if f['name']==disabled_factor]
    if len(selected)!=1 or selected[0]['weight']==0: raise ValueError('Choose an active factor to disable')
    frozen=copy.deepcopy(records)
    changed=[dict(f,weight=0) if f['name']==disabled_factor else dict(f) for f in factors]
    def scenario(rules):
        ranked,watch,unranked=prepare_screen(frozen,start,today,window,rules)
        return {'ranked':[{'rank':i,'name':r['name'],'points':r['points'],'total':r['total']} for i,r in enumerate(ranked,1)],
                'watch':[{'name':r['name'],'stage':r['stage']} for r in watch],
                'unranked':[{'name':r['name'],'reason':r['reason']} for r in unranked]}
    return {'as_of':today.isoformat(),'disabled_factor':disabled_factor,'baseline':scenario(factors),'disabled':scenario(changed)}

def summarize_document_gaps(gaps):
    """Group repeated document gaps by SEC folder and preserve every detail."""
    pattern=re.compile(r'^(Could not (?:read|parse) document) (https://www\.sec\.gov/Archives/edgar/data/\d+/\d+/)[^\s]+: (.+)$')
    groups={}; details=[]; order=[]
    for gap in gaps:
        match=pattern.match(str(gap))
        if not match:
            order.append(('plain',gap)); continue
        kind,folder,reason=match.groups(); key=(kind,folder,reason)
        if key not in groups:
            groups[key]=[]; order.append(('group',key))
        groups[key].append(gap); details.append(gap)
    summary=[]
    for kind,value in order:
        if kind=='plain': summary.append(value); continue
        items=groups[value]
        if len(items)<5: summary.extend(items)
        else:
            action,folder,reason=value
            summary.append(f'{len(items)} documents could not be processed in {folder} ({reason}); individual paths are in the source-gap file.')
    return summary,details

def save_source_gaps(folder,gaps):
    if not gaps: raise ValueError('No source gaps to save')
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    path=folder/('source-gaps-'+datetime.now().astimezone().strftime('%Y-%m-%d_%H-%M-%S_%f_%z')+'_'+uuid.uuid4().hex[:8]+'.json')
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump({'gaps':gaps},stream,indent=2,ensure_ascii=False)
        stream.write('\n')
    return path

def save_report(folder,report_text):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    if report_text.rstrip().splitlines()[-1]!='screens, not recommendations': raise ValueError('Invalid report ending')
    path=folder/('spinoff-screen-'+datetime.now().astimezone().strftime('%Y-%m-%d_%H-%M-%S_%f_%z')+'_'+uuid.uuid4().hex[:8]+'.md')
    with path.open('x',encoding='utf-8',newline='\n') as file: file.write(report_text)
    return path

def run_screen(client,registry,start,today,config,first_year,max_candidates=None,factor_provider=None,compare_zero=None,candidate_probe=None):
    validate_config(config)
    date.fromisoformat(start)
    if compare_zero is not None: compare_weight_scenarios([],start,today,config['window_days'],config['factors'],compare_zero)
    rows,index_date,limitations=collect_indices(client,first_year,today,event_start=start)
    try:
        ticker_data=fetch_company_tickers(client)
    except (OSError,ValueError,KeyError) as exc:
        if getattr(exc,'code',None) in (403,429): raise
        ticker_data=None
        limitations.append('SEC ticker-to-CIK lookup unavailable: '+type(exc).__name__)
    groups=group_candidates(rows)
    confirmed=[]; dropped=[]
    selected=sorted(groups.items())
    if max_candidates is not None:
        if max_candidates<1: raise ValueError('Candidate limit must be positive')
        if len(selected)>max_candidates:
            limitations.append(f'Diagnostic sample only: {max_candidates} of {len(selected)} registrants reviewed.')
            selected=selected[:max_candidates]
    for number,(cik,group) in enumerate(selected,1):
        print(f'Inspecting registrant {number} of {len(groups)} (CIK {cik})',flush=True)
        try:
            record,gaps=inspect_candidate(client,cik,group,registry,start,ticker_data=ticker_data,as_of=today)
        except (OSError,ValueError,KeyError) as exc:
            if getattr(exc,'code',None) in (403,429): raise
            limitations.append(f'CIK {cik}: review failed ({type(exc).__name__})')
            continue
        finally:
            registry.flush()
        limitations.extend(gaps)
        if is_dropped(record):
            dropped.append({'name':record['name'],'reason':record['rejection']['reason'],'filing':record['rejection']['filing']})
        elif not record.get('spinoff_evidence'):
            limitations.append(f"{record['name']}: distribution by a parent not established; not classified as a spinoff")
        else:
            if candidate_probe and stage(record,today,config['window_days'])=='in its window':
                probe_record=dict(record,distribution_date=value(record,'distribution_date'))
                try:
                    result=candidate_probe(probe_record,today.isoformat())
                    for message in result.get('limitations',[]): limitations.append(record['name']+': '+str(message))
                except Exception as exc:
                    limitations.append(record['name']+': LSEG candidate lookup unavailable ('+type(exc).__name__+').')
            if factor_provider and stage(record,today,config['window_days'])=='in its window':
                try: record=enrich_factor_inputs(record,factor_provider(record,today),today)
                except Exception as exc:
                    if getattr(exc,'code',None) in (403,429): raise
                    record=enrich_factor_inputs(record,{},today)
                    limitations.append(f"{record['name']}: factor data unavailable ({type(exc).__name__})")
            confirmed.append(record)
    ranked,watch,unranked=prepare_screen(confirmed,start,today,config['window_days'],config['factors'])
    for r in unranked:
        price=r.get('latest_close')
        suffix=f" | close: {price['close']} on {price['date']}" if price else ''
        limitations.append(f"{r['name']}: unranked - {r['reason']}"+suffix)
    price_dates={r['latest_close']['date'] for r in confirmed if r.get('latest_close')}
    price_date=next(iter(price_dates)) if len(price_dates)==1 else ('multiple dates' if price_dates else None)
    comparison=compare_weight_scenarios(confirmed,start,today,config['window_days'],config['factors'],compare_zero) if compare_zero is not None else None
    return {'ranked':ranked,'watch':watch,'dropped':dropped,'limitations':limitations,'index_date':index_date,'price_date':price_date,'comparison':comparison}

def report(run_date,price_date,index_date,ranked,watch,dropped,limitations,comparison=None):
    lines=[f'Run date: {run_date} | Price date: {price_date or "unavailable"} | Index date: {index_date or "unavailable"}', '', '# Spinoff screen', '', '## In window, ranked']
    if not ranked: lines.append('None established.')
    for i,r in enumerate(ranked,1):
        lines.append(f"{i}. {r['name']} | parent: {r.get('parent') or 'unavailable'} | distribution: {r.get('distribution_date') or 'unavailable'} | window ends: {r.get('window_ends') or 'unavailable'} | {r['total']:.2f} points: " + ', '.join(f'{k}: {v:.2f}' for k,v in r['points'].items()))
        for label,key in (('parent source','parent_evidence'),('distribution source','distribution_evidence')):
            evidence=r.get(key)
            if isinstance(evidence,dict) and evidence.get('filing') and evidence.get('section'):
                filed=f" | filed {evidence['filing_date']}" if evidence.get('filing_date') else ''
                lines.append(f"   {label}: {evidence['filing']} ({evidence['section']}){filed}")
        p=r.get('latest_close')
        lines.append(f"   close: {p['close']} on {p['date']}" if p else '   close: unavailable')
        for factor,explanation in r.get('factor_explanations',{}).items():
            if factor in r['points']: lines.append(f'   {factor}: {explanation}')
    lines+=['','## Watch list']
    for item in watch:
        entry=f"- {item['name']} - {item.get('stage','registered')}"
        evidence=item.get('evidence')
        if evidence and evidence.get('filing') and evidence.get('section'):
            entry+=f" | {evidence['filing']} ({evidence['section']}), filed {evidence.get('date','unavailable')}"
        listing=item.get('listing_evidence')
        if listing and listing.get('filing') and listing.get('section'):
            entry+=f" | listing source: {listing['filing']} ({listing['section']}), filed {listing.get('date','unavailable')}"
        lines.append(entry)
    if not watch: lines.append('None established.')
    lines+=['','## Dropped']
    lines += [f"- {x['name']} — {x['reason']} ({x['filing']})" for x in dropped] or ['None.']
    lines+=['','## Data limits and unranked names']+(['- '+str(x) for x in limitations] or ['- No limitations reported.'])
    if comparison is not None:
        lines+=['','## Same-input weight comparison',f"Factor set to zero: {comparison['disabled_factor']} | as of {comparison['as_of']}"]
        for label,key in (('Original weights','baseline'),('Selected factor at zero','disabled')):
            lines+=['',f'### {label}']
            outcome=comparison[key]
            if not outcome['ranked']: lines.append('None ranked.')
            for item in outcome['ranked']:
                points=', '.join(f'{name}: {value:.2f}' for name,value in item['points'].items()) or 'no active factor points'
                lines.append(f"- {item['rank']}. {item['name']} | {item['total']:.2f} points | {points}")
            for item in outcome['unranked']: lines.append(f"- {item['name']}: unranked - {item['reason']}")
    return '\n'.join(lines)+'\n\nscreens, not recommendations\n'

def main():
    parser=argparse.ArgumentParser(description='Spinoff seeker prototype; see skill instructions')
    parser.add_argument('--start',required=True,type=date.fromisoformat)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--env',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--index-from',type=int)
    parser.add_argument('--max-registrants',type=int)
    parser.add_argument('--partial',action='store_true')
    parser.add_argument('--lseg-candidates',action='store_true',help='Probe LSEG candidates without using them for scoring')
    parser.add_argument('--lseg-evidence',type=Path,help='JSON CIK mapping to independently checked listing and exchange evidence')
    parser.add_argument('--compare-zero',help='Compare the same inputs with one active factor set to zero')
    args=parser.parse_args()
    from dotenv import dotenv_values
    today=date.today()
    if args.start>today: raise SystemExit('Start date cannot be in the future.')
    config=json.loads(args.config.read_text(encoding='utf-8-sig'))
    validate_config(config)
    settings=dotenv_values(args.env)
    client=CachedIndexClient(SecClient((settings.get('SEC_USER_AGENT') or '').strip()),args.output/'sec_index_cache')
    first_year=args.index_from if args.index_from is not None else max(1994,args.start.year-1)
    print('Reading SEC indexes and filing folders.',flush=True)
    options={'max_candidates':args.max_registrants}
    if args.compare_zero is not None: options['compare_zero']=args.compare_zero
    workspace=None; price_issue=None
    try:
        if not args.partial or args.lseg_candidates or args.lseg_evidence:
            try:
                import lseg.data as ld
                from closes_reader import WorkspaceCandidateProbe,open_workspace_session
                workspace=ld
                open_workspace_session(ld,settings.get('LSEG_APP_KEY'))
                if args.lseg_candidates:
                    options['candidate_probe']=WorkspaceCandidateProbe(ld,fetch_company_tickers(client))
                if args.lseg_evidence:
                    evidence=json.loads(args.lseg_evidence.read_text(encoding='utf-8-sig'))
                    options['factor_provider']=WorkspaceOfficialProvider(ld,client,evidence)
                elif not args.partial:
                    options['factor_provider']=WorkspaceLiveProvider(ld,client,fetch_company_tickers(client))
            except Exception as exc:
                if getattr(exc,'code',None) in (403,429): raise
                price_issue='LSEG prices unavailable ('+type(exc).__name__+'); affected names remain unranked.'
        registry_path=new_registry_path(args.output)
        result=run_screen(client,Registry(registry_path,autosave=False),args.start.isoformat(),today,config,first_year,**options)
    finally:
        if workspace is not None: workspace.close_session()
    summarized_gaps,source_gaps=summarize_document_gaps(result['limitations'])
    gap_file=save_source_gaps(args.output,source_gaps) if source_gaps else None
    limitations=[f'Registration indexes before {first_year} were not searched.' + (' PARTIAL diagnostic.' if args.partial else ''),
                 'The filing reader recognizes only a narrow set of explicit labels and may miss spinoffs and facts.',
                 ('LSEG official prices require listing and exchange evidence.' if args.lseg_evidence else ('The screen is not connected to a verified live reader; one user-supplied exchange close matched the candidate field, but instrument identity and full coverage remain unverified.' if args.partial else 'LSEG TR.CLOSEPRICE(Adjusted=0) and the selected primary RIC are used under the user-supplied official-close and regular-way assumptions; historical completeness and listing-exchange identity are not independently verified.')) ,
                 'The exclusion rules and report have not been validated end-to-end against live filings.',
                 'SEC index responses may be cached for up to one hour; the first-line index date is the date reported by the index.']+summarized_gaps
    if price_issue: limitations.append(price_issue)
    if gap_file: limitations.append('Full source-gap details: '+gap_file.name)
    limitations.append('Fact registry: '+registry_path.name)
    text=report(today,result.get('price_date'),result['index_date'],result['ranked'],result['watch'],result['dropped'],limitations,comparison=result.get('comparison'))
    path=save_report(args.output,text)
    print('Screen report: '+str(path.resolve()),flush=True)
    print('Fact registry: '+str(registry_path.resolve()),flush=True)

if __name__=='__main__':
    main()
