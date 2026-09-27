"""Build the bundled interface fonts in assets/fonts from their OFL sources.

Sources (SIL Open Font License 1.1), from https://github.com/google/fonts:
  ofl/playfairdisplay/PlayfairDisplay[wght].ttf, PlayfairDisplay-Italic[wght].ttf
  ofl/sourceserif4/SourceSerif4[opsz,wght].ttf
  ofl/jetbrainsmono/JetBrainsMono[wght].ttf
  ofl/nanummyeongjo/NanumMyeongjo-Regular.ttf, NanumMyeongjo-Bold.ttf

The variable Latin faces become static weights (Windows font matching is
reliable only with static files) cut to Latin and punctuation. Playfair
Display and Source Serif carry Reserved Font Names, so their modified
versions are renamed "YoonDF Display" and "YoonDF Text" as the OFL requires;
copyright notices stay. JetBrains Mono has no reserved name. Nanum Myeongjo is
copied unmodified.

Usage: python scripts/build_fonts.py SOURCE_FOLDER
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import shutil
import sys
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

OUT = Path(__file__).resolve().parent.parent / "assets" / "fonts"
LATIN = "U+0020-007E,U+00A0-017F,U+2010-2027,U+2030-203A,U+2190-2199,U+2212,U+00D7,U+25A0-25CF"
STYLE = {400: "Regular", 600: "SemiBold", 700: "Bold", 900: "Black"}


def unicodes(spec):
    out = []
    for part in spec.split(","):
        a, _, b = part[2:].partition("-")
        out += range(int(a, 16), int(b or a, 16) + 1)
    return out


def rename(font, family):
    """One family name for every weight (Windows and Qt group by it); the
    weight class tells them apart. No typographic or variable names left."""
    weight = font["OS/2"].usWeightClass
    italic = bool(font["OS/2"].fsSelection & 1)
    style = ("Italic" if weight == 400 else STYLE[weight] + " Italic") if italic else STYLE[weight]
    name = font["name"]
    for nid in (16, 17, 21, 22, 25):
        name.removeNames(nameID=nid)
    full = family + ("" if style == "Regular" else " " + style)
    ps = (family + "-" + style).replace(" ", "")
    sub = "Bold Italic" if weight == 700 and italic else "Bold" if weight == 700 else "Italic" if italic else "Regular"
    for nid, value in ((1, family), (2, sub), (3, ps + ";YoonDF"), (4, full), (6, ps)):
        name.setName(value, nid, 3, 1, 0x409)
        name.setName(value, nid, 1, 0, 0)
    selection = font["OS/2"].fsSelection & ~(1 | 32 | 64)
    font["OS/2"].fsSelection = selection | (1 if italic else 0) | (32 if weight == 700 else 0) | (64 if style == "Regular" else 0)
    font["head"].macStyle = (1 if weight == 700 else 0) | (2 if italic else 0)


def static(source, axes, family, target):
    font = instancer.instantiateVariableFont(TTFont(source), axes)
    font["OS/2"].usWeightClass = int(axes["wght"])
    for table in ("STAT", "MVAR", "HVAR", "avar", "cvar", "fvar", "gvar"):
        if table in font: del font[table]
    rename(font, family)
    options = subset.Options()
    options.layout_features = ["*"]; options.name_IDs = ["*"]; options.name_languages = ["*"]
    options.hinting = True; options.notdef_outline = True
    cutter = subset.Subsetter(options); cutter.populate(unicodes=unicodes(LATIN)); cutter.subset(font)
    font.save(OUT / target)
    print(target, (OUT / target).stat().st_size // 1024, "KB")


def main(source):
    source = Path(source)
    playfair, italic = source / "PlayfairDisplay[wght].ttf", source / "PlayfairDisplay-Italic[wght].ttf"
    serif, mono = source / "SourceSerif4[opsz,wght].ttf", source / "JetBrainsMono[wght].ttf"
    static(playfair, {"wght": 700}, "YoonDF Display", "YoonDFDisplay-Bold.ttf")
    static(playfair, {"wght": 900}, "YoonDF Display", "YoonDFDisplay-Black.ttf")
    static(italic, {"wght": 400}, "YoonDF Display", "YoonDFDisplay-Italic.ttf")
    static(serif, {"wght": 400, "opsz": 14}, "YoonDF Text", "YoonDFText-Regular.ttf")
    static(serif, {"wght": 600, "opsz": 14}, "YoonDF Text", "YoonDFText-SemiBold.ttf")
    static(mono, {"wght": 400}, "JetBrains Mono", "JetBrainsMono-Regular.ttf")
    static(mono, {"wght": 700}, "JetBrains Mono", "JetBrainsMono-Bold.ttf")
    for weight in ("Regular", "Bold"):
        shutil.copyfile(source / f"NanumMyeongjo-{weight}.ttf", OUT / f"NanumMyeongjo-{weight}.ttf")


if __name__ == "__main__":
    main(sys.argv[1])
