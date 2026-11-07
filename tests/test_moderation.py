import json,os,subprocess,tempfile,time,unittest,urllib.request,urllib.error,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Moderation(unittest.TestCase):
 def test_passwords_and_deletion(self):
  with tempfile.TemporaryDirectory() as directory:
   with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
   env={**os.environ,'GALLERY_BACKEND':'sqlite','GALLERY_DATA_DIR':directory,'PORT':str(port),'GALLERY_REGISTRATION_PASSWORD':'class-test','GALLERY_ADMIN_PASSWORD':'teacher-test'}
   proc=subprocess.Popen(['python3',str(ROOT/'server.py')],env=env,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
   base=f'http://127.0.0.1:{port}'
   def post(path,data):
    try:
     with urllib.request.urlopen(urllib.request.Request(base+path,json.dumps(data).encode(),{'Content-Type':'application/json'})) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:return e.code,json.load(e)
   def read():return json.load(urllib.request.urlopen(base+'/api/works'))
   try:
    proc.stdout.readline()
    data=dict(school='test',grade='5',team='team',members='member',url='https://example.com')
    self.assertEqual(post('/api/works',data)[0],403)
    self.assertEqual(post('/api/works',{**data,'password':'wrong'})[0],403)
    self.assertEqual(read(),[])
    self.assertEqual(post('/api/works',{**data,'password':'class-test'})[0],200)
    w=read()[0];self.assertNotIn('password',w)
    path='/api/works/'+w['id']+'/delete'
    self.assertEqual(post(path,{})[0],403)
    self.assertEqual(post(path,{'password':'class-test'})[0],403)
    self.assertEqual(len(read()),1)
    stream=urllib.request.urlopen(base+'/api/events',timeout=3);stream.readline();stream.readline()
    self.assertEqual(post(path,{'password':'teacher-test'})[0],200)
    self.assertEqual(stream.readline(),b'data: refresh\n');stream.close()
    self.assertEqual(read(),[])
    self.assertEqual(post(path,{'password':'teacher-test'})[0],404)
   finally:proc.terminate();proc.wait();proc.stdout.close()
 def test_unconfigured_password_fails_closed(self):
  import sys
  sys.path.insert(0,str(ROOT))
  from unittest.mock import patch
  # Exercise handler authentication directly without opening or changing a database.
  import importlib.util
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'GALLERY_BACKEND':'sqlite','GALLERY_DATA_DIR':d,'GALLERY_ADMIN_PASSWORD':'','GALLERY_REGISTRATION_PASSWORD':''}):
   spec=importlib.util.spec_from_file_location('moderation_server',ROOT/'server.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   handler=object.__new__(module.Handler);results=[];handler.send=lambda status,obj:results.append(status)
   for key in ['GALLERY_ADMIN_PASSWORD','GALLERY_REGISTRATION_PASSWORD']:self.assertFalse(handler.require_password({'password':''},key))
   self.assertEqual(results,[503,503])
