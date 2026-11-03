"""Small, authored 2.5D movements over original artwork, without generated faces.

Compact support keeps unrelated scenery fixed. Rigid region interiors preserve
facial proportions; only the surrounding hair/cloak blends the displacement.
This is breathing/sway animation, not full-body performance or lip sync.
"""
import json
import math
from pathlib import Path

PROFILES = Path(__file__).with_name('character-motion.json')


class CharacterMotion:
    def __init__(self, image, regions):
        import cv2
        import numpy as np
        self.source = np.array(image, dtype=np.uint8)
        self.height, self.width = self.source.shape[:2]
        self.regions = regions
        self.fields = []
        self.max_displacement = 0.0
        for region in regions:
            cx, cy, rx, ry = region['area']
            if not all(math.isfinite(v) for v in (cx, cy, rx, ry)) or not (0 < rx < 1 and 0 < ry < 1):
                raise ValueError('Invalid authored character region')
            x0, x1 = max(0, int((cx-rx)*self.width)), min(self.width, math.ceil((cx+rx)*self.width))
            y0, y1 = max(0, int((cy-ry)*self.height)), min(self.height, math.ceil((cy+ry)*self.height))
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            radius = np.sqrt(((xx-cx*self.width)/(rx*self.width))**2 + ((yy-cy*self.height)/(ry*self.height))**2)
            # The central 55% translates rigidly; an eased annulus joins the still.
            q = np.clip((radius-.55)/.45, 0, 1)
            weight = (1-q*q*(3-2*q)).astype(np.float32)
            ax, ay = region['travel_px_at_1080']
            if abs(ax) > 4 or abs(ay) > 4 or not 1 <= region['period'] <= 12:
                raise ValueError('Authored movement must remain restrained')
            self.fields.append((x0,x1,y0,y1,xx,yy,weight,region))
            self.max_displacement += math.hypot(ax,ay)*self.width/1080
        cv2.setNumThreads(2)

    def frame(self, seconds):
        import cv2
        import numpy as np
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Invalid character clock')
        result = self.source.copy()
        # Independent authored supports do not replace or synthesize any artwork.
        for x0,x1,y0,y1,xx,yy,weight,r in self.fields:
            phase = r.get('phase',0)
            wave = math.sin(seconds*2*math.pi/r['period']+phase)-math.sin(phase)
            ax,ay = r['travel_px_at_1080']
            dx = weight*(ax*self.width/1080*wave)
            dy = weight*(ay*self.width/1080*wave)
            patch = cv2.remap(self.source,xx-dx,yy-dy,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
            active = weight > 0
            target = result[y0:y1,x0:x1]
            target[active] = patch[active]
        return result

    def audit(self):
        import numpy as np
        baseline = self.frame(0)
        sample = self.frame(.87)
        delta = np.abs(sample.astype(np.float32)-baseline.astype(np.float32))
        return {'region_count':len(self.regions), 'changed_pixels':int(np.any(delta>0,axis=2).sum()),
                'mean_pixel_change':round(float(delta.mean()),6),
                'max_travel_px':round(self.max_displacement*2,3),
                'technique':'authored-breathing-sway-v1'}


def for_artwork(image, path):
    profiles = json.loads(PROFILES.read_text())
    regions = profiles.get(Path(path).parent.name,{}).get(Path(path).stem,[])
    return CharacterMotion(image,regions) if regions else None
