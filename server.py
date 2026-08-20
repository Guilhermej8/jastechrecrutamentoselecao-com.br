
import os, json, secrets, hashlib, hmac
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import psycopg2
import psycopg2.extras

ROOT=os.path.dirname(os.path.abspath(__file__))
DATABASE_URL=os.environ.get('DATABASE_URL','')
ADMIN_PASSWORD=os.environ.get('ADMIN_PASSWORD','')
if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL não configurada.')
if not ADMIN_PASSWORD:
    raise RuntimeError('ADMIN_PASSWORD não configurada.')

DEFAULT={"name":"JasTech Recrutamento & Seleção","cnpj":"","location":"Carandaí/MG e região.","heroTitle":"Conectando talentos às melhores oportunidades.","heroText":"A JasTech aproxima empresas e profissionais e organiza as etapas de recrutamento e seleção.","whatsapp":"5531999999999","primary":"#1769ff","nav":"#071b3a","bg":"#f5f8fc","text":"#10213d","layout":"classic","buttonStyle":"rounded","mediaImage":"","mediaVideo":"","music":[],"password":"","jobs":[{"id":1,"title":"Auxiliar Administrativo","area":"Administrativo","city":"Carandaí/MG","type":"Efetivo","active":True},{"id":2,"title":"Vendedor(a)","area":"Vendas","city":"Carandaí/MG","type":"Efetivo","active":True},{"id":3,"title":"Auxiliar de Produção","area":"Produção","city":"Região","type":"Efetivo","active":True}],"candidates":[],"companies":[],"finance":{"transactions":[]},"stages":["Cadastro recebido","Triagem de currículo","Entrevista JasTech","Finalista / encaminhado para entrevista","Aprovado","Não aprovado"]}
SESSIONS={}

def db(): return psycopg2.connect(DATABASE_URL, sslmode='require')
def init_db():
    with db() as c:
        with c.cursor() as cur:
            cur.execute('CREATE TABLE IF NOT EXISTS app_state (id INTEGER PRIMARY KEY, data JSONB NOT NULL, updated_at TIMESTAMPTZ DEFAULT NOW())')
            cur.execute('SELECT data FROM app_state WHERE id=1')
            if not cur.fetchone():
                cur.execute('INSERT INTO app_state(id,data) VALUES(1,%s)',(json.dumps(DEFAULT),))

def load():
    with db() as c:
        with c.cursor() as cur:
            cur.execute('SELECT data FROM app_state WHERE id=1')
            row=cur.fetchone()
            return row[0] if row else DEFAULT.copy()

def save(d):
    with db() as c:
        with c.cursor() as cur:
            cur.execute('INSERT INTO app_state(id,data) VALUES(1,%s ON CONFLICT(id) DO UPDATE SET data=EXCLUDED.data,updated_at=NOW()',(json.dumps(d,ensure_ascii=False),))

def public_state(d):
    out=dict(d)
    out.pop('password',None); out.pop('candidates',None); out.pop('companies',None); out.pop('finance',None)
    return out

def token_ok(handler):
    t=handler.headers.get('Authorization','').replace('Bearer ','',1).strip()
    return bool(t and t in SESSIONS)

def hash_pw(v): return hashlib.sha256(v.encode()).hexdigest()
def json_body(h):
    n=int(h.headers.get('Content-Length','0')); return json.loads(h.rfile.read(n).decode('utf-8'))

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=ROOT,**kwargs)
    def send_json(self,obj,status=200):
        raw=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/' or path=='/index.html':
            self.path = '/index.html'
            return super().do_GET()
        if path=='/admin' or path=='/admin/':
            self.path = '/admin/index.html'
            return super().do_GET()
        if path=='/api/public': return self.send_json(public_state(load()))
        if path=='/api/jobs': return self.send_json([j for j in load().get('jobs',[]) if j.get('active') is True])
        if path=='/api/admin/state':
            if not token_ok(self): return self.send_json({'error':'Não autorizado'},401)
            return self.send_json(load())
        if path=='/api/state': return self.send_json({'error':'Use /api/public ou /api/admin/state'},410)
        return super().do_GET()
    def do_POST(self):
        path=urlparse(self.path).path
        try: body=json_body(self)
        except Exception as e: return self.send_json({'error':str(e)},400)
        if path=='/api/admin/login':
            if body.get('user','').strip().lower()!='admin' or not hmac.compare_digest(str(body.get('password','')),ADMIN_PASSWORD): return self.send_json({'ok':False,'error':'Usuário ou senha incorretos.'},401)
            t=secrets.token_urlsafe(32); SESSIONS[t]=True; return self.send_json({'ok':True,'token':t})
        if path=='/api/admin/state':
            if not token_ok(self): return self.send_json({'error':'Não autorizado'},401)
            if not isinstance(body,dict) or not isinstance(body.get('jobs'),list): return self.send_json({'ok':False,'error':'estado inválido'},400)
            body['password']=''; save(body); return self.send_json({'ok':True,'state':body})
        if path=='/api/candidates':
            d=load(); email=str(body.get('email','')).strip().lower()
            if not email or not body.get('jobId'): return self.send_json({'ok':False,'error':'Dados obrigatórios ausentes'},400)
            if any(str(x.get('email','')).lower()==email for x in d.get('candidates',[])): return self.send_json({'ok':False,'error':'Este e-mail já possui um acesso de candidato.'},409)
            job=next((j for j in d.get('jobs',[]) if str(j.get('id'))==str(body.get('jobId')) and j.get('active') is True),None)
            if not job: return self.send_json({'ok':False,'error':'Vaga indisponível'},400)
            x={k:body.get(k,'') for k in ['name','phone','email','city','role','jobTitle','area','experience','resume','passwordHash']}; x.update({'id':secrets.randbelow(10**12),'jobId':job['id'],'stage':'Cadastro recebido','feedback':'','createdAt':__import__('datetime').datetime.utcnow().isoformat()+'Z'})
            d.setdefault('candidates',[]).append(x); save(d); return self.send_json({'ok':True})
        if path=='/api/companies':
            d=load(); email=str(body.get('email','')).strip().lower()
            if not email or not body.get('role'): return self.send_json({'ok':False,'error':'Dados obrigatórios ausentes'},400)
            if any(str(x.get('email','')).lower()==email for x in d.get('companies',[])): return self.send_json({'ok':False,'error':'Este e-mail já possui um acesso de empresa.'},409)
            cid=secrets.randbelow(10**12); jid=secrets.randbelow(10**12)
            c={k:body.get(k,'') for k in ['company','contact','phone','email','passwordHash']}; c.update({'id':cid,'paid':False,'createdAt':__import__('datetime').datetime.utcnow().isoformat()+'Z','jobs':[jid]})
            j={k:body.get(k,'') for k in ['title','city','salary','requirements']}; j.update({'id':jid,'title':body.get('role',''),'area':'','type':'A definir','active':False,'companyId':cid,'quantity':int(body.get('quantity') or 1),'processStatus':'Solicitação recebida','approvedByAdmin':False})
            d.setdefault('companies',[]).append(c); d.setdefault('jobs',[]).append(j); save(d); return self.send_json({'ok':True})
        if path=='/api/portal/login':
            d=load(); email=str(body.get('email','')).strip().lower(); ph=str(body.get('passwordHash',''))
            typ=body.get('type')
            arr=d.get('companies',[]) if typ=='company' else d.get('candidates',[])
            found=next((x for x in arr if str(x.get('email','')).lower()==email and hmac.compare_digest(str(x.get('passwordHash','')),ph)),None)
            if not found: return self.send_json({'ok':False,'error':'E-mail ou senha incorretos.'},401)
            
            if typ=='company':
                jobs=[j for j in d.get('jobs',[]) if str(j.get('companyId'))==str(found.get('id'))]
                ids={str(j.get('id')) for j in jobs}
                candidates=[x for x in d.get('candidates',[]) if str(x.get('jobId')) in ids]
                return self.send_json({'ok':True,'account':found,'state':{'jobs':jobs,'candidates':candidates,'stages':d.get('stages',[])}})
            return self.send_json({'ok':True,'account':found,'state':{'stages':d.get('stages',[])}})
        return self.send_json({'error':'Not found'},404)

if __name__=='__main__':
    init_db(); port=int(os.environ.get('PORT','10000')); print(f'JasTech online na porta {port}'); ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
