"""Run only inside a separate factory Blender process; never opens a user .blend."""
import json
import pathlib
import sys
import traceback
import bpy


def main(config):
    source = pathlib.Path(config["source"])
    folder = pathlib.Path(config["output"])
    scene = bpy.context.scene
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    frames = []
    duration = None
    if config["kind"] == "image":
        image = bpy.data.images.load(str(source),check_existing=False)
        width,height = image.size
        if not width or not height:raise ValueError("无法读取图片尺寸")
        scale = min(1,1024/max(width,height))
        if scale<1:image.scale(max(1,int(width*scale)),max(1,int(height*scale)))
        image.save_render(str(folder/"frame-00.png"),scene=scene)
        frames.append({"file":"frame-00.png"})
    else:
        editor=scene.sequence_editor_create()
        strips=getattr(editor,"strips",None)
        if strips is None:strips=editor.sequences
        strip=strips.new_movie(name="Reference",filepath=str(source),frame_start=1,channel=1)
        source_fps=getattr(strip,"fps",0)
        if source_fps>0:
            scene.render.fps=max(1,round(source_fps))
            scene.render.fps_base=scene.render.fps/source_fps
        count = int(strip.frame_final_duration)
        fps = scene.render.fps / scene.render.fps_base
        if count<1 or fps<=0:raise ValueError("视频没有可读取帧")
        duration = count / fps
        element = strip.elements[0]
        width,height = element.orig_width,element.orig_height
        scale = min(1,1024/max(width,height))
        strip.transform.scale_x=scale
        strip.transform.scale_y=scale
        scene.render.resolution_x=max(4,int(width*scale))
        scene.render.resolution_y=max(4,int(height*scale))
        scene.render.resolution_percentage=100
        scene.render.use_sequencer=True
        scene.render.use_compositing=False
        samples=min(config["frames"],count)
        for i in range(samples):
            frame=1+round((count-1)*i/max(1,samples-1))
            scene.frame_set(frame)
            name=f"frame-{i:02d}.png"
            scene.render.filepath=str(folder/name)
            bpy.ops.render.render(write_still=True)
            frames.append({"file":name,"seconds":round((frame-1)/fps,3)})
    return {"state":"ready","frames":frames,"duration":duration}


if __name__=="__main__":
    request=pathlib.Path(sys.argv[sys.argv.index("--")+1])
    config=json.loads(request.read_text(encoding="utf-8"))
    try:result=main(config)
    except Exception:result={"state":"failed","error":traceback.format_exc()[-2000:]}
    (pathlib.Path(config["output"])/"result.json").write_text(json.dumps(result,ensure_ascii=False),encoding="utf-8")
