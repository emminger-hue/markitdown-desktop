"""Generate the application icon in every format Briefcase needs.

Run: python tools/make_icon.py
Writes src/markitdown_desktop/resources/icon.png (1024 px), icon-<size>.png, icon.icns, icon.ico.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "src" / "markitdown_desktop" / "resources"
SIZES = (16, 32, 48, 64, 128, 256, 512, 1024)
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def render(size: int = 1024) -> Image.Image:
    s = size
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = int(s * 0.06)
    radius = int(s * 0.22)
    draw.rounded_rectangle(
        (margin, margin, s - margin, s - margin), radius=radius, fill=(31, 95, 191, 255)
    )
    # white "page" with a folded corner
    left, top = int(s * 0.26), int(s * 0.18)
    right, bottom = int(s * 0.74), int(s * 0.82)
    fold = int(s * 0.12)
    draw.polygon(
        [(left, top), (right - fold, top), (right, top + fold), (right, bottom), (left, bottom)],
        fill=(255, 255, 255, 255),
    )
    draw.polygon(
        [(right - fold, top), (right - fold, top + fold), (right, top + fold)],
        fill=(205, 220, 245, 255),
    )
    # "M↓" glyphs
    text_font = font(int(s * 0.34))
    draw.text((s * 0.5, s * 0.56), "M", fill=(31, 95, 191, 255), font=text_font, anchor="mm")
    arrow_font = font(int(s * 0.16))
    draw.text((s * 0.5, s * 0.75), "↓", fill=(31, 95, 191, 255), font=arrow_font, anchor="mm")
    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    master = render(1024)
    master.save(OUT / "icon.png")
    for size in SIZES:
        master.resize((size, size), Image.Resampling.LANCZOS).save(OUT / f"icon-{size}.png")
    master.save(OUT / "icon.icns", sizes=[(n, n) for n in SIZES if n >= 16])
    master.save(OUT / "icon.ico", sizes=[(n, n) for n in (16, 32, 48, 64, 256)])
    print("wrote icons to", OUT)


if __name__ == "__main__":
    main()
