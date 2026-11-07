import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import SQLiteStore, SupabaseStore, StorageError, decode_poster
from deploy.migrate_supabase import migrate


def work():
    return dict(id='test', school='학교', grade='5', team='모둠', members='별명',
                title='작품', url='https://example.com', poster='', created=1, reactions={}, comments=[])


class FakeRemote(SupabaseStore):
    """Protocol fixture, not a live Supabase verification."""
    def __init__(self):
        super().__init__('https://test.supabase.co','sb_secret_test')
        self.rows={}; self.calls=[]
    def request(self,path,method='GET',data=None,headers=None,raw=False):
        self.calls.append((path,method,copy.deepcopy(data),headers,raw))
        if path.startswith('/storage/'): return {'Key':'poster'}
        if method=='GET': return [{'payload':copy.deepcopy(x)} for x in self.rows.values()]
        if method=='POST' and path.startswith('/rest/v1/gallery_works'):
            self.rows.setdefault(data['id'],copy.deepcopy(data['payload']))
        elif path=='/rest/v1/rpc/gallery_update': return False


class Tests(unittest.TestCase):
    def test_sqlite_concurrent_updates(self):
        with tempfile.TemporaryDirectory() as d:
            store=SQLiteStore(d);store.add(work())
            def visitor(i):
                store.update('test','react',{'client':str(i),'emoji':'👍'})
                store.update('test','comments',{'name':str(i),'text':'응원','id':str(i),'created':1})
            with ThreadPoolExecutor(max_workers=10) as pool:list(pool.map(visitor,range(30)))
            self.assertEqual(len(store.read()[0]['comments']),30)
            self.assertEqual(len(store.read()[0]['reactions']),30)
            store.update('test','react',{'client':'0','emoji':'👍'})
            self.assertEqual(len(SQLiteStore(d).read()[0]['reactions']),29)

    def test_upload_and_retry_migration_preserves_new_data(self):
        with tempfile.TemporaryDirectory() as d:
            source=SQLiteStore(d);w=work();w['poster']='data:image/png;base64,aGVsbG8='
            source.add(w);target=FakeRemote()
            self.assertEqual(migrate(source.path,target)['imported'],1)
            self.assertTrue(target.read()[0]['poster'].startswith('https://test.supabase.co/storage/v1/object/public/'))
            target.rows['test']['comments'].append({'text':'새 댓글'})
            self.assertEqual(migrate(source.path,target)['skipped'],1)
            self.assertEqual(target.read()[0]['comments'],[{'text':'새 댓글'}])
            self.assertTrue(source.read()[0]['poster'].startswith('data:'))

    def test_missing_work_and_invalid_poster(self):
        with self.assertRaises(KeyError):FakeRemote().update('missing','react',{'client':'x','emoji':'👍'})
        with self.assertRaises(ValueError):decode_poster('data:image/svg+xml;base64,aGVsbG8=')
        with self.assertRaises(ValueError):decode_poster('data:image/png;base64,%%%')
        with self.assertRaises(ValueError):SupabaseStore('http://test.supabase.co','key')

    def test_secret_header_and_redacted_error(self):
        store=SupabaseStore('https://test.supabase.co','sb_secret_example')
        def fail(req,timeout):
            self.assertEqual(req.get_header('Apikey'),'sb_secret_example')
            self.assertIsNone(req.get_header('Authorization'))
            raise urllib.error.HTTPError(req.full_url,403,'sensitive upstream',{},None)
        with patch('urllib.request.urlopen',side_effect=fail):
            with self.assertRaises(StorageError) as caught:store.read()
            self.assertNotIn('secret',str(caught.exception))
            self.assertNotIn('sensitive',str(caught.exception))

if __name__=='__main__':unittest.main()
