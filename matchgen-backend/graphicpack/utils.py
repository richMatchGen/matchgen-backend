import os
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

def get_font(font_filename, size):
    from django.conf import settings
    import os
    from PIL import ImageFont

    try:
        # Join the filename with the STATIC_FONT_DIR
        font_path = os.path.join(settings.STATIC_FONT_DIR, font_filename)

        print(f"🧠 Attempting to load font: {font_path}")
        return ImageFont.truetype(font_path, size)
    except Exception as e:
        print(f"⚠️ Failed to load font {font_filename}: {e}")
        return ImageFont.load_default()
