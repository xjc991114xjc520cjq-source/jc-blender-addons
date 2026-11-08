import bpy,json,pathlib
out=pathlib.Path('F:/BlenderAgentBridge/evidence/attachment-fixtures');out.mkdir(exist_ok=True)
scene=bpy.context.scene
scene.sequence_editor_create()
scene.sequence_editor.strips.new_effect(name='red',type='COLOR',channel=1,frame_start=1,length=6).color=(1,0,0)
scene.sequence_editor.strips.new_effect(name='blue',type='COLOR',channel=1,frame_start=7,length=6).color=(0,0,1)
scene.render.fps=6
scene.frame_start=1;scene.frame_end=12
scene.render.resolution_x=320;scene.render.resolution_y=180;scene.render.resolution_percentage=100
scene.render.use_sequencer=True
scene.view_settings.view_transform='Standard'
scene.render.image_settings.media_type='VIDEO'
scene.render.image_settings.file_format='FFMPEG'
scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264';scene.render.ffmpeg.constant_rate_factor='MEDIUM'
scene.render.filepath=str(out/'reference-video.mp4')
bpy.ops.render.render(animation=True)
(out/'reference-notes.txt').write_text('附件路径引用测试：前半段红色，后半段蓝色。\n只检查，不修改当前场景。',encoding='utf-8')
print('ATTACHMENT_FIXTURE_READY')


