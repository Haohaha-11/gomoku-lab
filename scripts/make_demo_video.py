"""Convert a genuine browser recording to MP4, extract a poster, and retain provenance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'.agent/recording/gomoku-demo.webm'
OUTPUT=ROOT/'static/media'


def main():
    ffmpeg=shutil.which('ffmpeg')
    ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:
        raise SystemExit('Install official FFmpeg and make ffmpeg/ffprobe available on PATH.')
    if not SOURCE.is_file():
        raise SystemExit('No real browser recording yet. Run make_demo_receiver.py and open its recording URL.')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    video=OUTPUT/'gomoku-demo.mp4'
    subprocess.run([ffmpeg,'-y','-i',str(SOURCE),'-an','-vf','fps=30,format=yuv420p','-c:v','libx264','-preset','medium','-crf','20','-movflags','+faststart',str(video)],check=True)
    probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_entries','format=duration,size:stream=codec_name,width,height,avg_frame_rate','-of','json',str(video)]))
    duration=float(probe['format']['duration'])
    assert 30<=duration<=50, f'Unexpected recording duration: {duration}'
    poster=OUTPUT/'gomoku-demo-poster.jpg'
    subprocess.run([ffmpeg,'-y','-ss',str(max(0,duration-2)),'-i',str(video),'-frames:v','1','-update','1','-q:v','2',str(poster)],check=True)
    meta={
        'capture':'Real app Three.js renderer + the same loaded stage scenery, captured with browser MediaRecorder. No image-generation frames.',
        'replay':'14 legal plies; first 7 scripted opening; black continuation scripted; white continuation from actual depth-3 Alpha-Beta searches.',
        'timing':'Edited/accelerated replay pacing; displayed per-move search milliseconds were measured by the Python engine.',
        'claims':'This is a gameplay and tactical demonstration, not a playing-strength evaluation.',
        'video':probe,'video_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
        'game_sha256':hashlib.sha256((OUTPUT/'demo-game.json').read_bytes()).hexdigest(),
        'visual_sources_sha256':{name:hashlib.sha256((ROOT/'static'/name).read_bytes()).hexdigest()
                                 for name in ('app.js','victory-ink.js','demo-recorder.js')
                                 if (ROOT/'static'/name).is_file()},
        'poster':'gomoku-demo-poster.jpg',
    }
    (OUTPUT/'demo-provenance.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'video':str(video),'poster':str(poster),'duration':duration,'bytes':video.stat().st_size},ensure_ascii=False))


if __name__=='__main__':
    main()
