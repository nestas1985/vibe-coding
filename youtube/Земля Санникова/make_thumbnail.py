"""
Наложение текста на обложку Земли Санникова — 2 варианта шрифта (Impact, Arial Black).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
SRC = HERE / "thumb_raw" / "nanabanana.jpg"
OUT_DIR = HERE / "ctr"
OUT_DIR.mkdir(exist_ok=True)

W, H = 1280, 720

PLAQUE_TEXT = "1902, АРКТИКА"
MAIN_TEXT = ["ОСТРОВ-", "ПРИЗРАК"]

FONTS = {
    "impact": r"C:\Windows\Fonts\impact.ttf",
    "arialbd": r"C:\Windows\Fonts\arialbd.ttf",
}


def load_and_crop(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGB")
    # исходник уже 16:9 (2560x1440) — просто уменьшаем, без обрезки
    img = img.resize((W, H))
    return img


def add_top_gradient(img: Image.Image, height: int, max_alpha: int = 140):
    """Лёгкое затемнение сверху — гарантирует читаемость текста на любом фоне."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    grad = ImageDraw.Draw(overlay)
    for y in range(height):
        alpha = int(max_alpha * (1 - y / height))
        grad.line([(0, y), (img.width, y)], fill=(5, 10, 25, alpha))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


def draw_text_with_outline(draw, xy, text, font, fill, outline, outline_width):
    x, y = xy
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def make_variant(font_key: str, font_path: str):
    img = load_and_crop(SRC)
    img = add_top_gradient(img, height=320)
    draw = ImageDraw.Draw(img)

    # красная плашка с датой (верх, справа)
    plaque_font = ImageFont.truetype(font_path, 34)
    bbox = draw.textbbox((0, 0), PLAQUE_TEXT, font=plaque_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 24, 14
    plaque_w, plaque_h = tw + pad_x * 2, th + pad_y * 2
    px, py = W - plaque_w - 50, 40
    draw.rectangle([px, py, px + plaque_w, py + plaque_h], fill=(200, 30, 30))
    draw.text((px + pad_x, py + pad_y - bbox[1]), PLAQUE_TEXT, font=plaque_font, fill=(255, 255, 255))

    # основной текст — ледяной белый/голубой с тёмно-синей обводкой
    main_font = ImageFont.truetype(font_path, 92)
    y = py + plaque_h + 30
    for line in MAIN_TEXT:
        bbox = draw.textbbox((0, 0), line, font=main_font)
        tw = bbox[2] - bbox[0]
        x = W - tw - 60
        draw_text_with_outline(draw, (x, y), line, main_font, fill=(225, 245, 255), outline=(10, 20, 40), outline_width=6)
        y += bbox[3] - bbox[1] + 22

    out_path = OUT_DIR / f"thumbnail_sannikov_{font_key}.jpg"
    img.save(out_path, quality=95)
    print(f"OK -> {out_path}")


if __name__ == "__main__":
    for key, path in FONTS.items():
        make_variant(key, path)
