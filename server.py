import json, os, sqlite3, threading, time, uuid, hmac
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).parent
from storage import create_store, decode_poster, StorageError
STORE=create_store(ROOT)
changed=threading.Condition(); revision=0

def read(): return STORE.read()

def field(data,key,limit=100,required=True):
 v=str(data.get(key,'')).strip()
 if (required and not v) or len(v)>limit: raise ValueError('입력 내용을 확인해 주세요: '+key)
 return v
class Handler(BaseHTTPRequestHandler):
 def send(self,status,obj):
  raw=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
 def do_GET(self):
  if self.path in ('/api/works', '/healthz'):
   try:
    works=read()
    return self.send(200,works if self.path=='/api/works' else {'ok':True})
   except (StorageError, KeyError, sqlite3.Error): return self.send(503,{'error':'저장소 연결을 확인해 주세요.'})
  if self.path=='/api/events':
   self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.send_header('Cache-Control','no-cache'); self.send_header('X-Accel-Buffering','no'); self.end_headers()
   try:
    seen=-1
    while True:
     with changed:
      changed.wait_for(lambda: revision != seen, timeout=20)
      seen=revision
     self.wfile.write(b'data: refresh\n\n'); self.wfile.flush()
   except (BrokenPipeError,ConnectionResetError): pass
   return
  if self.path.split('?')[0] not in ('/','/index.html'): return self.send(404,{'error':'찾을 수 없습니다.'})
  raw=(ROOT/'index.html').read_bytes(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
 def require_password(self, data, variable):
  expected=os.environ.get(variable, '')
  if not expected:
   self.send(503,{'error':'선생님이 비밀번호를 설정한 후 사용할 수 있습니다.'})
   return False
  supplied=data.get('password','')
  if not isinstance(supplied,str) or not hmac.compare_digest(supplied.encode(),expected.encode()):
   self.send(403,{'error':'비밀번호가 올바르지 않습니다.'})
   return False
  return True
 def do_POST(self):
  global revision
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size>6000000: return self.send(413,{'error':'이미지는 4MB 이하로 선택해 주세요.'})
   d=json.loads(self.rfile.read(size))
   if not isinstance(d,dict): raise ValueError('올바른 등록 정보를 입력해 주세요.')
   parts=self.path.strip('/').split('/')
   if self.path=='/api/works':
    if not self.require_password(d,'GALLERY_REGISTRATION_PASSWORD'): return
    w={k:field(d,k,200 if k=='members' else 100) for k in ('school','grade','team','members')}; w['title']=field(d,'title',100,False) or w['team']+'의 작품'; w['url']=field(d,'url',2000)
    if urlparse(w['url']).scheme not in ('http','https') or not urlparse(w['url']).netloc: raise ValueError('올바른 웹사이트 주소를 입력해 주세요.')
    poster=field(d,'poster',5600000,False)
    decode_poster(poster)
    w.update(id=uuid.uuid4().hex,poster=poster,created=time.time(),reactions={},comments=[]); STORE.add(w)
   elif len(parts)==4 and parts[:2]==['api','works']:
    if parts[3]=='delete':
     if not self.require_password(d,'GALLERY_ADMIN_PASSWORD'): return
     STORE.delete(parts[2])
     with changed:
      revision+=1
      changed.notify_all()
     return self.send(200,{'ok':True})
    if parts[3]=='react':
     data={'client':field(d,'client',100),'emoji':field(d,'emoji',10)}
     if data['emoji'] not in ['👍','💗','😮','💡']: raise ValueError('반응을 확인해 주세요.')
    elif parts[3]=='comments':
     data={'id':uuid.uuid4().hex,'name':field(d,'name',40),'text':field(d,'text',500),'created':time.time()}
    else: return self.send(404,{'error':'찾을 수 없습니다.'})
    STORE.update(parts[2],parts[3],data)
   else: return self.send(404,{'error':'찾을 수 없습니다.'})
   with changed:
    revision+=1
    changed.notify_all()
   self.send(200,{'ok':True})
  except KeyError: self.send(404,{'error':'작품을 찾을 수 없습니다.'})
  except (StorageError,sqlite3.Error): self.send(503,{'error':'저장소에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.'})
  except (ValueError,TypeError) as e: self.send(400,{'error':str(e)})
if __name__=='__main__':
 print('Gallery listening on port '+os.environ.get('PORT','8080'),flush=True)
 ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','8080'))),Handler).serve_forever()
