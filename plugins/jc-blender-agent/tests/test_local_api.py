"""Use fake keys in an isolated credential namespace, never user credentials."""
import json,os,subprocess,sys,tempfile,unittest,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from bridge import local_api as store


class LocalAPITests(unittest.TestCase):
    def test_endpoint_validation_and_isolation(self):
        self.assertEqual(store.normalize_endpoint('https://EXAMPLE.com:443/v1/'),'https://example.com/v1')
        self.assertNotEqual(store.target_name('https://a.invalid/v1'),store.target_name('https://b.invalid/v1'))
        self.assertNotEqual(store.target_name('https://a.invalid/v1'),store.target_name('https://a.invalid/custom'))
        for bad in ('http://remote.invalid/v1','https://user:pass@a.invalid/v1','https://a.invalid/v1?key=x'):
            with self.assertRaises(ValueError):store.target_name(bad)

    def test_settings_allowlist_never_writes_key(self):
        with tempfile.TemporaryDirectory() as root:
            store.save_settings(root,{'base_url':'https://fixture.invalid/v1/','protocol':'responses','api_model':'fixture-model','remember_api_key':True,'api_key':'TEST_KEY_NOT_FOR_JSON','unknown':'TEST_KEY_NOT_FOR_JSON','max_steps':12})
            raw=(Path(root)/store.SETTINGS).read_text()
            self.assertNotIn('TEST_KEY_NOT_FOR_JSON',raw);self.assertNotIn('api_key',json.loads(raw))
            saved=store.load_settings(root);self.assertEqual(saved['api_model'],'fixture-model')
            self.assertEqual(saved['base_url'],'https://fixture.invalid/v1')

    @unittest.skipUnless(os.name=='nt','Windows credential integration')
    def test_windows_credential_survives_process_and_can_be_cleared(self):
        namespace='JCBlenderAgent/TEST/'+uuid.uuid4().hex+'/'
        base='https://key-fixture.invalid/v1';sentinel='FAKE_CREDENTIAL_SENTINEL_'+uuid.uuid4().hex
        try:
            store.save_key(base,sentinel,namespace)
            self.assertEqual(store.read_key(base,namespace),sentinel)
            self.assertEqual(store.read_key('https://other-fixture.invalid/v1',namespace),'')
            code="import sys;sys.path.insert(0,sys.argv[1]);from bridge.local_api import read_key;assert read_key(sys.argv[2],sys.argv[3])==sys.argv[4];print('fresh_process_credential_read_passed')"
            # Fake sentinel only; no real user key is ever passed to a subprocess.
            r=subprocess.run([sys.executable,'-I','-c',code,str(ROOT),base,namespace,sentinel],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            store.delete_key(base,namespace);self.assertEqual(store.read_key(base,namespace),'')
            store.delete_key(base,namespace)
        finally:store.delete_key(base,namespace)


if __name__=='__main__':unittest.main(verbosity=2)
