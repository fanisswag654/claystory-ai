"""DepthFlow adapter: verified stills to gentle, continuous portrait parallax.

Heavy ML/OpenGL imports stay out of the approval webhook and offline tests.
No publishing, network service, paid API, or voice change lives here.
"""
import argparse
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

FPS = 30
DEPTH_MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
REVISION = "depthflow-gentle-v1"


def camera_offset(progress, reverse=False):
    if not math.isfinite(progress) or not 0 <= progress <= 1:
        raise ValueError("Camera progress must be within the scene clock")
    # Ease from left to right without a mid-scene restart or fast orbit.
    x = 0.14 * (2 * (progress * progress * (3 - 2 * progress)) - 1)
    return (-x if reverse else x, 0.025 * math.sin(math.pi * progress))


def validate_clip(path, frames, width=1080, height=1920):
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-count_frames", "-show_streams", "-of", "json", str(path)]))
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    if (video["width"], video["height"]) != (width, height):
        raise ValueError("DepthFlow returned incorrect portrait dimensions")
    if video.get("codec_name") != "h264" or video.get("pix_fmt") != "yuv420p":
        raise ValueError("DepthFlow clip must be H.264 yuv420p")
    if Fraction(video.get("r_frame_rate", "0")) != FPS:
        raise ValueError("DepthFlow scene must be 30fps")
    if int(video.get("nb_read_frames", 0)) != frames:
        raise ValueError("DepthFlow returned an incomplete scene clock")


def get_scene():
    """Create one fresh graphics context per worker process."""
    import torch
    from attrs import define
    from depthflow.scene import DepthScene
    torch.set_num_threads(2)

    @define
    class GentleScene(DepthScene):
        reverse_pan: bool = False

        def update(self):
            self.state.offset = camera_offset(min(1.0, max(0.0, self.tau)), self.reverse_pan)

    return GentleScene(backend="headless")


def _render_scene(image, output, frames, reverse=False, width=1080, height=1920):
    if frames < 2 or width * 16 != height * 9 or width % 2 or height % 2:
        raise ValueError("Expected a positive portrait 9:16 scene clock")
    from PIL import Image, ImageOps
    from depthflow.state import DepthState

    # Fit both axes proportionally before estimating depth; never squash a face.
    with Image.open(image) as source:
        fitted = ImageOps.pad(source.convert("RGB"), (width, height),
                              method=Image.Resampling.LANCZOS, color="black")
    scene = get_scene()
    scene.reverse_pan = reverse
    scene.input(image=fitted)
    scene.state = DepthState(height=0.08, steady=0.30, isometric=0.60, zoom=0.98)
    scene.ffmpeg.h264(preset="veryfast", crf=22)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # One full scene preserves camera continuity across the narration.
    scene.main(output=output, width=width, height=height, fps=FPS,
               time=frames / FPS, ssaa=1.0, turbo=False)
    validate_clip(output, frames, width, height)
    return output


def render_scene(image, output, frames, reverse=False, width=1080, height=1920):
    if frames < 2 or width * 16 != height * 9 or width % 2 or height % 2:
        raise ValueError("Expected a positive portrait 9:16 scene clock")
    # ShaderFlow 0.13 can retain shader uniforms between inputs. A process per
    # scene prevents redeclaration errors and releases all ML/OpenGL memory.
    subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker",
                    str(Path(image).resolve()), str(Path(output).resolve()),
                    str(frames), str(int(reverse)), str(width), str(height)], check=True)
    validate_clip(output, frames, width, height)
    return Path(output)


def main():
    if len(sys.argv) == 8 and sys.argv[1] == "--worker":
        _render_scene(Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]),
                      bool(int(sys.argv[5])), int(sys.argv[6]), int(sys.argv[7]))
        return
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="mataora-niwareka-moko")
    parser.add_argument("--scene", type=int, default=1, choices=range(1, 9))
    parser.add_argument("--seconds", type=float, default=2)
    parser.add_argument("--width", type=int, default=270)
    parser.add_argument("--output", type=Path, default=Path("automation/output/depthflow-smoke.mp4"))
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 0.1 <= args.seconds <= 20:
        parser.error("Smoke test duration must be 0.1–20 seconds")
    from cinematic_assets import verify_assets
    image = verify_assets(args.topic)[args.scene - 1]
    render_scene(image, args.output, round(args.seconds * FPS),
                 bool(args.scene % 2), args.width, args.width * 16 // 9)


if __name__ == "__main__":
    main()
