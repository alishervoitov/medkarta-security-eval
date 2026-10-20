import json,os,glob,re,collections
D='sa_out'
def load_b(c):
    j=json.load(open(f'{D}/bandit_{c}.json')); out=collections.Counter()
    for r in j['results']:
        f=r['filename'].split(f'/{c}/',1)[-1]
        out[(f,r['test_id'],r['code'].strip()[:0] or r['line_range'][0]*0)]+=1  # location-insensitive
    return out, len(j['results'])
def load_s(c):
    j=json.load(open(f'{D}/semgrep_{c}.json')); out=collections.Counter()
    for r in j['results']:
        f=r['path'].split(f'/{c}/',1)[-1]
        out[(f,r['check_id'].split('.')[-1],0)]+=1
    return out, len(j['results']), len(j.get('errors',[]))
conds=sorted(os.path.basename(p)[7:-5] for p in glob.glob(f'{D}/bandit_*.json'))
def base_of(c):
    t=c.split('__')[0]; return t+'__BASE'
rows=[]
for c in conds:
    b,nb=load_b(c); s,ns,ne=load_s(c)
    bb,_=load_b(base_of(c)); sb,_,_=load_s(base_of(c))
    db=(b-bb); dbm=(bb-b); ds=(s-sb); dsm=(sb-s)
    rows.append((c,nb,ns,ne,sum(db.values()),sum(dbm.values()),sum(ds.values()),sum(dsm.values()),db,dbm,ds,dsm))
print('cond | bandit_total | semgrep_total | sg_errors | bandit +new/-gone | semgrep +new/-gone')
for r in rows: print(r[0],r[1],r[2],r[3],f'+{r[4]}/-{r[5]}',f'+{r[6]}/-{r[7]}')
print()
for r in rows:
    if r[0].endswith('__BASE'): continue
    if r[4] or r[5] or r[6] or r[7]:
        print('==',r[0]); 
        for k,v in r[8].items(): print('  bandit +',k[:2],v)
        for k,v in r[9].items(): print('  bandit -',k[:2],v)
        for k,v in r[10].items(): print('  semgrep +',k[:2],v)
        for k,v in r[11].items(): print('  semgrep -',k[:2],v)
