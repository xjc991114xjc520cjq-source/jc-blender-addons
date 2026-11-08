"""Two fresh Blender processes prove autosave/restore without user settings."""
import bpy,os,sys,json,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
assert 'api-015-' in os.environ['JC_BLENDER_CREDENTIAL_PROFILE']
assert Path(bpy.utils.user_resource('CONFIG')).resolve()==Path(os.environ['BLENDER_USER_CONFIG']).resolve()
sys.path.insert(0,str(ROOT/'addon'))
import jc_blender_agent as addon
addon.register();rt=addon.runtime();rt.auto_models=False
A='https://credential-fixture-a.invalid/v1';B='https://credential-fixture-b.invalid/v1'
FAKE='JC_FAKE_KEY_RESTART_SENTINEL';FAKE_B='JC_FAKE_KEY_OTHER_ENDPOINT'
state=addon.state_root();phase=os.environ['JC_API_TEST_PHASE'];store=addon.local_api()
if phase=='write':
    rt.base_url=A;rt.protocol='responses';rt.api_model='fixture-model';rt.vision=False;rt.max_steps=11
    rt.api_key=FAKE
    assert store.read_key(A)==FAKE
    rt.base_url=B
    assert rt.api_key=='' and addon.effective_api_key()==''
    rt.api_key=FAKE_B
    assert store.read_key(B)==FAKE_B
    rt.base_url=A
    assert rt.api_key=='' and addon.effective_api_key()==FAKE
    raw=(state/'api-settings.json').read_text(encoding='utf-8')
    assert FAKE not in raw and FAKE_B not in raw
    # Keep a nonempty draft while saving to test SKIP_SAVE, not just an empty UI field.
    rt.api_key=FAKE
    bpy.ops.wm.save_as_mainfile(filepath=str(state/'key-persistence.blend'))
    assert FAKE.encode() not in (state/'key-persistence.blend').read_bytes()
    print('JC_API_KEY_BLENDER_WRITE_PASS')
else:
    try:
        assert rt.api_key==''
        assert rt.base_url==A and rt.protocol=='responses' and rt.api_model=='fixture-model'
        assert rt.vision is False and rt.max_steps==11
        assert addon.effective_api_key()==FAKE
        bpy.ops.wm.open_mainfile(filepath=str(state/'key-persistence.blend'))
        rt=addon.runtime();rt.auto_models=False
        assert rt.api_key=='' and addon.effective_api_key()==FAKE
        rt.agent='api'
        assert addon.model_profile()['api_key']==FAKE
        item=rt.models.add();item.identifier='fixture-model';item.name='fixture-model'
        rt.model_index=0
        assert len(rt.models)==1, 'Choosing a model must not clear/refetch the model list'
        # The send operator must use the saved key too, with no real network/agent.
        captured=[]
        def fake_http(path,payload=None,**kwargs):
            if path=='/jobs':captured.append(payload);return {'id':'b'*32}
            return {}
        addon.http=fake_http;addon._instance='a'*32;rt.prompt='仅测试保存的Key取用，不发送网络请求'
        assert bpy.ops.jc_agent.send()=={'FINISHED'}
        assert captured[0]['profile']['api_key']==FAKE
        rt.remember_api_key=False;assert addon.effective_api_key()==''
        rt.remember_api_key=True;assert addon.effective_api_key()==FAKE
        assert bpy.ops.jc_agent.clear_api_key()=={'FINISHED'}
        assert store.read_key(A)=='' and store.read_key(B)==FAKE_B
        (ROOT/'evidence/local-api-015-result.json').write_text(json.dumps({'passed':True,'blender_version':bpy.app.version_string,'fresh_process_restore':True,'key_absent_in_blend_and_json':True,'model_refresh_and_send_use_saved_key':True,'endpoint_isolation':True,'remember_optout_and_clear':True,'real_provider_tested':False},indent=2),encoding='utf-8')
        print('JC_API_KEY_BLENDER_RESTART_PASS')
    finally:
        store.delete_key(A);store.delete_key(B)
addon.unregister()
