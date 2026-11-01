import unittest
from render_cinematic import validate_reel
class ReelsExport(unittest.TestCase):
 def setUp(self):
  self.probe={"streams":[{"codec_type":"video","codec_name":"h264","width":1080,"height":1920,"pix_fmt":"yuv420p","r_frame_rate":"30/1","duration":"67"},{"codec_type":"audio","codec_name":"aac","duration":"67"}]}
 def test_portrait_export(self):validate_reel(self.probe,67)
 def test_landscape_rejected(self):
  self.probe["streams"][0].update(width=1920,height=1080)
  with self.assertRaises(ValueError):validate_reel(self.probe,67)
 def test_missing_audio_rejected(self):
  self.probe["streams"].pop()
  with self.assertRaises(ValueError):validate_reel(self.probe,67)
 def test_incomplete_picture_rejected(self):
  self.probe["streams"][0]["duration"]="58"
  with self.assertRaises(ValueError):validate_reel(self.probe,67)
 def test_unsupported_pixel_format_rejected(self):
  self.probe["streams"][0]["pix_fmt"]="yuv444p"
  with self.assertRaises(ValueError):validate_reel(self.probe,67)

class ProportionalFitting(unittest.TestCase):
 def test_circle_and_full_image_survive_different_aspects(self):
  import subprocess,tempfile
  from pathlib import Path
  from render_cinematic import image_fit_filter
  # A red circle on each source detects anisotropic scaling in the actual
  # FFmpeg output, while green corners detect accidental cropping.
  for w,h in ((640,360),(360,640),(400,400)):
   with self.subTest(source=(w,h)),tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);src=p/"source.ppm";out=p/"out.ppm";radius=60
    raw=bytearray()
    for y in range(h):
     for x in range(w):
      circle=(x-w/2)**2+(y-h/2)**2<=radius**2
      corner=(x<8 or x>=w-8) and (y<8 or y>=h-8)
      raw.extend((255,0,0) if circle else ((0,255,0) if corner else (0,0,0)))
    src.write_bytes(f"P6\n{w} {h}\n255\n".encode()+raw)
    subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y","-i",str(src),"-vf",image_fit_filter(),"-frames:v","1","-pix_fmt","rgb24","-f","rawvideo",str(out)],check=True)
    pixels=out.read_bytes();xs=[];ys=[];green=0
    for i in range(0,len(pixels),3):
     r,g,b=pixels[i:i+3]
     if r>180 and g<70 and b<70:xs.append((i//3)%1080);ys.append((i//3)//1080)
     if g>180 and r<70 and b<70:green+=1
    self.assertGreater(green,20)
    self.assertAlmostEqual((max(xs)-min(xs)+1)/(max(ys)-min(ys)+1),1,delta=.015)

class GentleCameraPan(unittest.TestCase):
 def test_motion_preserves_roundness_and_moves_only_slightly(self):
  import subprocess,tempfile
  from pathlib import Path
  from render_cinematic import image_fit_filter
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);src=p/"circle.ppm";dst=p/"motion.rgb";w,h=360,640
   raw=bytearray()
   for y in range(h):
    for x in range(w):
     raw.extend((255,0,0) if (x-180)**2+(y-320)**2<=40**2 else (0,0,0))
   src.write_bytes(f"P6\n{w} {h}\n255\n".encode()+raw)
   subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y","-loop","1","-i",str(src),"-vf",image_fit_filter(2,0),"-frames:v","2","-pix_fmt","rgb24","-f","rawvideo",str(dst)],check=True)
   frames=dst.read_bytes();size=1080*1920*3
   self.assertEqual(len(frames),size*2)
   centres=[]
   for frame in (frames[:size],frames[size:]):
    xs=[];ys=[]
    for y in range(740,1150):
     for x in range(300,800):
      n=(y*1080+x)*3;r,g,b=frame[n:n+3]
      if r>180 and g<70 and b<70:xs.append(x);ys.append(y)
    self.assertAlmostEqual((max(xs)-min(xs)+1)/(max(ys)-min(ys)+1),1,delta=.015)
    centres.append(((max(xs)+min(xs))/2,(max(ys)+min(ys))/2))
   self.assertGreater(centres[0][0]-centres[1][0],5)
   self.assertLess(centres[0][0]-centres[1][0],30)
