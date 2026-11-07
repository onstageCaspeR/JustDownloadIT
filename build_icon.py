"""Generate a multi-size Windows icon from the supplied app logo.

The original logo artwork is preserved; only the square canvas corners are
rounded and made transparent.

Run: python build_icon.py (requires Pillow)
"""
import os
from PIL import Image, ImageDraw

# All sizes Windows may request (1x and common DPI-scaled shell sizes).
SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
APP_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
SOURCE_CANDIDATES = ("app_logo.png", "app_logo.png.jpg", "app_logo.jpg")
CORNER_RADIUS = 0.16


def load_rounded_logo():
    source_path = next(
        (os.path.join(APP_DIR, name) for name in SOURCE_CANDIDATES
         if os.path.isfile(os.path.join(APP_DIR, name))),
        None,
    )
    if source_path is None:
        raise FileNotFoundError(
            "Logo not found. Put app_logo.png (or app_logo.png.jpg) next to build_icon.py."
        )

    image = Image.open(source_path).convert("RGBA")
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side))

    # Build the mask at source resolution so the downscaled ICO frames retain
    # smooth edges while leaving all of the logo artwork untouched.
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    radius = round(side * CORNER_RADIUS)
    draw.rounded_rectangle((0, 0, side - 1, side - 1), radius=radius, fill=255)
    image.putalpha(mask)
    print(f"Using logo: {source_path} ({side}x{side})")
    return image


def build_ico(out_path=OUT_PATH):
    logo = load_rounded_logo()
    images = [logo.resize((s, s), Image.Resampling.LANCZOS) for s in SIZES]
    master = images[-1]  # 256x256 - must be the base so Pillow keeps every size

    # Use the largest frame as the ICO base; Pillow otherwise skips sizes larger
    # than the base image.
    master.save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=images[:-1],
    )

    with Image.open(out_path) as ico:
        embedded = sorted(getattr(ico, "info", {}).get("sizes", set()))
    print(f"Wrote {out_path}")
    print(f"Embedded sizes: {[w for (w, _h) in embedded]}")

    expected = {(s, s) for s in SIZES}
    missing = expected - set(embedded)
    if missing:
        raise SystemExit(f"ERROR: icon is missing sizes {sorted(missing)}")
    print("OK: all sizes embedded.")


if __name__ == "__main__":
    build_ico()
