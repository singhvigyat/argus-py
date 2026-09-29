from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.logging_config import get_logger
from app.models.schemas import DOMElement

logger = get_logger(__name__)

BADGE_COLOR = (29, 78, 216, 255)
BADGE_SIZE = (22, 20)


def _load_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in ("arial.ttf", "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(path, 11)
        except OSError:
            continue
    return ImageFont.load_default()


def generate_labeled_screenshot(
    screenshot_path: Path,
    elements: list[DOMElement],
    output_path: Path,
) -> None:
    valid = [el for el in elements if el.width > 0 and el.height > 0]
    if not valid:
        logger.warning("No valid elements for SoM labeling at %s", screenshot_path)
        return

    img = Image.open(screenshot_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _load_font()

    for el in valid:
        x, y = el.x, el.y
        draw.rounded_rectangle(
            [x, y, x + BADGE_SIZE[0], y + BADGE_SIZE[1]],
            radius=3,
            fill=BADGE_COLOR,
        )
        draw.text((x + 3, y + 2), str(el.id), fill="white", font=font)

    combined = Image.alpha_composite(img, overlay)
    combined.convert("RGB").save(output_path)
    logger.info("SoM screenshot saved: %s (%d labels)", output_path, len(valid))
