import os
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

def get_font(font_path, size):
    try:
        # Resolve relative paths based on BASE_DIR
        if not os.path.isabs(font_path):
            font_path = os.path.join(settings.BASE_DIR, font_path.lstrip("/"))
        return ImageFont.truetype(font_path, size)
    except:
        return ImageFont.load_default()