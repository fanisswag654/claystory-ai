"""Render deterministic portrait H.264/AAC MP4s for Photos, without real-time recording."""
import base64
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import shutil
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'videos'
FPS = 24

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def render():
    DEST.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=shutil.which("chromium"), args=["--no-sandbox"])
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}')
            for key, opener in [('fish-nz', 'openFishStory'), ('maui-nz', 'openMauiStory')]:
                timing = json.loads((ROOT / 'audio' / f'{key}-timing.json').read_text())
                total = sum(timing['durations'])
                page.evaluate(f'{opener}()')
                page.wait_for_function('(durations)=>cloudAudioAvailable && mixedFxReady && JSON.stringify(timelineDurations())===JSON.stringify(durations)', arg=timing['durations'])
                video = DEST / f'{key}-picture.mp4'
                process = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'image2pipe',
                    '-framerate', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'fast',
                    '-crf', '19', '-pix_fmt', 'yuv420p', str(video)], stdin=subprocess.PIPE)
                try:
                    for frame in range(int(total * FPS) + 1):
                        png = page.evaluate('(t)=>{draw(t);return canvas.toDataURL("image/png").split(",")[1]}', min(total, frame/FPS))
                        process.stdin.write(base64.b64decode(png))
                    process.stdin.close()
                    if process.wait() != 0:
                        raise RuntimeError('Video encoding failed')
                except BaseException:
                    process.kill()
                    process.wait()
                    raise
                for mix in ('soft', 'balanced', 'bold', 'voice'):
                    audio = ROOT / 'audio' / (f'{key}-full.mp3' if mix == 'voice' else f'{key}-mix-{mix}.mp3')
                    target = DEST / f'{key}-{mix}.mp4'
                    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(video), '-i', str(audio),
                        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
                        '-t', str(total), '-movflags', '+faststart', str(target)], check=True)
                    print(f'Rendered {target.name}: {total:.3f}s', flush=True)
                video.unlink()
            browser.close()
    finally:
        server.shutdown()

if __name__ == '__main__':
    render()
