"""Prepare the 윤DF character art for the interface.

From art/character/standing.webp (the character on white paper) this cuts the
character out, clears the floor shadow and the pocket between the legs,
takes the white paper out of the fur's soft edge, and writes:
  assets/character/standing.png   the whole character, transparent
  assets/character/face.png       head and bow tie, for small places
  assets/character/wave-body.png, wave-forearm.png
                                  the figure split at the right elbow, so the
                                  forearm can turn up and wave (ui/WavingCharacter.qml)
From art/character/jumping.webp it writes assets/character/jumping.jpg.

Needs Pillow and NumPy (tools only; the app does not use them).
Usage: python scripts/make_character.py
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "art" / "character"
OUT = ROOT / "assets" / "character"


def flood(passable, seeds):
    """Pixels reachable from `seeds` through `passable`."""
    h, w = passable.shape
    reached = np.zeros((h, w), bool)
    queue = deque()
    for y, x in seeds:
        if passable[y, x] and not reached[y, x]:
            reached[y, x] = True; queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y+1, x), (y-1, x), (y, x+1), (y, x-1)):
            if 0 <= ny < h and 0 <= nx < w and passable[ny, nx] and not reached[ny, nx]:
                reached[ny, nx] = True; queue.append((ny, nx))
    return reached


def cut_out(image):
    a = np.asarray(image.convert("RGB")).astype(np.int32)
    h, w, _ = a.shape
    spread = a.max(-1) - a.min(-1)
    bright = a.mean(-1)
    paper = (spread < 14) & (bright > 200)
    floor = np.zeros((h, w), bool); floor[int(h * .82):, :] = True
    paper |= floor & (spread < 18) & (bright > 120)          # the contact shadow is grey
    border = [(y, x) for x in range(w) for y in (0, h-1)] + [(y, x) for y in range(h) for x in (0, w-1)]
    background = flood(paper, border)
    # The gap between the legs is closed off by the feet: clear enclosed paper low down.
    pocket = paper & ~background & (bright > 228)
    low = np.zeros((h, w), bool); low[int(h * .75):, :] = True
    loose = paper | ((bright > 200) & (spread < 30))
    for y, x in zip(*np.nonzero(pocket & low)):
        if background[y, x]: continue
        blob = flood(loose & ~background, [(y, x)])
        if blob.sum() > 40: background |= blob
    below = np.zeros((h, w), bool); below[int(h * .83):, :] = True
    background |= below & (bright > 150) & (spread < 40)
    alpha = Image.fromarray(((~background) * 255).astype(np.uint8))
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0))
    al = np.asarray(alpha).astype(np.float32) / 255
    # Defringe: the soft edge takes its colour from the solid fur beside it,
    # not from the white paper, so the character sits on any background.
    rgb = a.astype(np.float32)
    known = al > .98
    for _ in range(10):
        total = np.zeros_like(rgb); count = np.zeros((h, w), np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                k = np.roll(np.roll(known, dy, 0), dx, 1)
                total += np.roll(np.roll(rgb, dy, 0), dx, 1) * k[..., None]; count += k
        fill = ~known & (count > 0)
        rgb[fill] = total[fill] / count[fill][:, None]
        known |= fill
    out = Image.fromarray(np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), (al * 255).astype(np.uint8)]), "RGBA")
    left, top, right, bottom = out.getbbox()
    return out.crop((max(0, left-12), max(0, top-12), min(w, right+12), min(h, bottom+12)))


# The right arm (on the viewer's right) in the cut-out figure's pixels: the
# region past the torso, the elbow where the forearm turns, and the elbow's
# round joint shared by both layers so the bend never shows a cut. The QML
# side uses ELBOW divided by the figure's size (printed below).
ARM = [(736, 704), (1045, 704), (1045, 1010), (905, 1010), (806, 928), (756, 889), (749, 872)]
SHOULDER, PAW = (744, 758), (915, 945)
ELBOW, JOINT = (791, 822), 41


def split_arm(figure):
    """Body (with the upper arm) and forearm layers of the same size."""
    w, h = figure.size
    ys, xs = np.mgrid[0:h, 0:w]
    region = Image.new("L", (w, h), 0); ImageDraw.Draw(region).polygon(ARM, fill=255)
    arm = np.asarray(region) > 0
    axis = np.array(PAW, float) - np.array(SHOULDER, float); axis /= np.linalg.norm(axis)
    beyond = (xs - ELBOW[0]) * axis[0] + (ys - ELBOW[1]) * axis[1] >= 0
    joint = (xs - ELBOW[0]) ** 2 + (ys - ELBOW[1]) ** 2 <= JOINT ** 2
    def soft(mask):
        return np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1))).astype(np.float32) / 255
    rgba = np.asarray(figure)
    alpha = rgba[..., 3].astype(np.float32)
    layer = lambda keep: Image.fromarray(np.dstack([rgba[..., :3], (alpha * soft(keep)).astype(np.uint8)]), "RGBA")
    return layer(~(arm & beyond & ~joint)), layer((arm & beyond) | joint)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    standing = cut_out(Image.open(ART / "standing.webp"))
    scale = 720 / standing.width
    standing.resize((720, round(standing.height * scale)), Image.LANCZOS).save(OUT / "standing.png", optimize=True)
    # Head and bow tie: the top two thirds of the figure.
    face = standing.crop((0, 0, standing.width, int(standing.height * .66)))
    face.resize((320, round(face.height * 320 / face.width)), Image.LANCZOS).save(OUT / "face.png", optimize=True)
    body, forearm = split_arm(standing)
    for name, layer in (("wave-body", body), ("wave-forearm", forearm)):
        layer.resize((720, round(layer.height * scale)), Image.LANCZOS).save(OUT / f"{name}.png", optimize=True)
    print("elbow at", round(ELBOW[0] / standing.width, 4), round(ELBOW[1] / standing.height, 4), "of the figure")
    jumping = Image.open(ART / "jumping.webp").convert("RGB")
    jumping.resize((760, round(jumping.height * 760 / jumping.width)), Image.LANCZOS).save(OUT / "jumping.jpg", quality=86, optimize=True)
    for path in sorted(OUT.iterdir()):
        print(path.relative_to(ROOT), path.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
