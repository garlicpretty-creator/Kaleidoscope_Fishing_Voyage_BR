import json,os,re,sys,glob
root=sys.argv[1] if len(sys.argv)>1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__))); BP=os.path.join(root,'Kaleidoscope Fishing Voyage [BP]'); RP=os.path.join(root,'Kaleidoscope Fishing Voyage [RP]')
bad=[]
def load(p):
    t=open(p,encoding='utf-8-sig').read()
    try: return json.loads(t)
    except Exception:
        try: return json.loads(re.sub(r'(?m)^\s*//.*$','',t))
        except Exception as e: bad.append(('PARSE',p,str(e))); return None
alljson={}
for p in glob.glob(glob.escape(root)+'/**/*.json',recursive=True): alljson[p]=load(p)
defined=set()
for p,d in alljson.items():
    if not d: continue
    for k in ('minecraft:item','minecraft:block','minecraft:entity'):
        if isinstance(d,dict) and k in d: defined.add(d[k]['description']['identifier'])
# blocks placed via block_placer count as items too
ids_used={}
txt=open(os.path.join(BP,'scripts/data/generated.js'),encoding='utf-8').read()
gb=json.loads(json.loads(re.search(r'^export const GUIDEBOOK_JSON = (.*);$',txt,re.M).group(1)))
for p,d in alljson.items():
    if d is None or '[BP]' not in p or '/scripts/' in p: continue
    if any(s in p.replace(os.sep,'/') for s in ('/recipes/','/loot_tables/','/item_catalog/','/trading/','/spawn_rules/','/feature_rules/','/features/')):
        for m in re.findall(r'"(kaleidoscope_fishing:[a-z0-9_]+)"',json.dumps(d)): ids_used.setdefault(m,set()).add(os.path.basename(p))
for m in re.findall(r'(kaleidoscope_fishing:[a-z0-9_]+)',re.sub(r'^export const GUIDEBOOK_JSON.*$','',txt,flags=re.M)):
    ids_used.setdefault(m,set()).add('generated.js')
for m in re.findall(r'(kaleidoscope_fishing:[a-z0-9_]+)',json.dumps(gb)): ids_used.setdefault(m,set()).add('guidebook')
IGN=re.compile(r'kaleidoscope_fishing:(itemGroup|board|wok|stockpot|steamer|pot|oven|tea|guidebook|cutting|fry|grill|mill|bowl|recipe|kc|cat|minigame|evt|api_|register|line_tune|plus|leave|style|part|food_stage|dir|fish$|size$|dashi$|fish_stock$|tray$|fish_bank|wants|want_|tamed|is_|bd$|title|credit|spent|record|sizes)')
# names that are not items: each recipe / feature / feature rule's own identifier, and structure names
own=set()
def own_ids(o):
    if isinstance(o,dict):
        d=o.get('description')
        if isinstance(d,dict) and isinstance(d.get('identifier'),str): own.add(d['identifier'])
        if isinstance(o.get('structure_name'),str): own.add(o['structure_name'])
        for v in o.values(): own_ids(v)
    elif isinstance(o,list):
        for v in o: own_ids(v)
for p,d in alljson.items():
    if d is not None and '[BP]' in p and any(s in p.replace(os.sep,'/') for s in ('/recipes/','/features/','/feature_rules/')): own_ids(d)
for i,src in sorted(ids_used.items()):
    if i not in defined and i not in own and not IGN.match(i): bad.append(('UNDEFINED_ID',i,sorted(src)[:3]))
# icons -> item_texture
it=load(os.path.join(RP,'textures/item_texture.json'))['texture_data']; tt=load(os.path.join(RP,'textures/terrain_texture.json'))['texture_data']
def texfile(path):
    return any(os.path.exists(os.path.join(RP,path+e)) for e in ('.png','.tga','.texture_set.json'))
for k,v in list(it.items())+list(tt.items()):
    ts=v['textures']; ts=ts if isinstance(ts,list) else [ts]
    for t in ts:
        t=t if isinstance(t,str) else t.get('path')
        if not texfile(t): bad.append(('MISSING_TEX',k,t))
for p,d in alljson.items():
    if not d or '[BP]' not in p: continue
    if isinstance(d,dict) and 'minecraft:item' in d:
        ic=d['minecraft:item']['components'].get('minecraft:icon')
        ic=ic if isinstance(ic,str) else (ic or {}).get('texture') or ((ic or {}).get('textures') or {}).get('default')
        if ic and ic not in it: bad.append(('ICON',os.path.basename(p),ic))
    if isinstance(d,dict) and 'minecraft:block' in d:
        def walk(o):
            if isinstance(o,dict):
                for k,v in o.items():
                    if k=='texture' and isinstance(v,str) and v not in tt: bad.append(('BLOCKTEX',os.path.basename(p),v))
                    walk(v)
            elif isinstance(o,list):
                for x in o: walk(x)
        walk(d)
        lt=d['minecraft:block']['components'].get('minecraft:loot')
        # a table under loot_tables/kaleidoscope_cookery/ is Cookery's own (Kombu Tea reuses its empty table)
        if lt and not lt.startswith('loot_tables/kaleidoscope_cookery/') and not os.path.exists(os.path.join(BP,lt)): bad.append(('LOOT',os.path.basename(p),lt))
# geometry ids
geos=set()
for p,d in alljson.items():
    if d and '[RP]' in p and isinstance(d,dict) and 'minecraft:geometry' in d:
        for g in d['minecraft:geometry']: geos.add(g['description']['identifier'])
for p,d in alljson.items():
    if not d: continue
    for g in re.findall(r'"(geometry\.kaleidoscope_fishing[a-z0-9_.]*)"',json.dumps(d)):
        if g not in geos: bad.append(('GEO',os.path.basename(p),g))
# lang keys for display names
for lang in ('en_US','zh_TW','zh_CN'):
    keys=set()
    for f in (os.path.join(BP,'texts',lang+'.lang'),os.path.join(RP,'texts',lang+'.lang')):
        for l in open(f,encoding='utf-8'):
            if '=' in l and not l.startswith('#'): keys.add(l.split('=',1)[0].strip())
    for p,d in alljson.items():
        if not d or '[BP]' not in p: continue
        for k in re.findall(r'%(kaleidoscope_fishing\.[a-zA-Z0-9_.]+)',json.dumps(d)):
            if k not in keys: bad.append(('LANG',lang,k))
    js=''.join(open(f,encoding='utf-8').read() for f in glob.glob(glob.escape(BP)+'/scripts/**/*.js',recursive=True) if not f.endswith('generated.js'))
    for k in set(re.findall(r'(?:translate: |t\(|hint\([^,]*, )["`](\$\{NS\}\.[a-z_.]+|kaleidoscope_fishing\.[a-z_.]+)["`]',js)):
        k=k.replace('${NS}','kaleidoscope_fishing')
        if k not in keys: bad.append(('LANG_JS',lang,k))
print('defined',len(defined),'json',len(alljson))
for b in bad: print(*b)
print('PROBLEMS',len(bad))
