import os
from django.conf import settings

def get_static_font_path(font_family, bold=False, italic=False):
    style = ""
    if bold and italic:
        style = "BoldItalic"
    elif bold:
        style = "Bold"
    elif italic:
        style = "Italic"
    else:
        style = "Regular"

    filename = f"{font_family}.ttf"
    return os.path.join(settings.BASE_DIR, "static", "fonts", filename)