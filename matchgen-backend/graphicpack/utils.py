import os
import re
from typing import Tuple, List

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont


def get_font(font_filename, size, weight="normal", style="normal"):
    """Get font with enhanced styling support."""
    try:
        # Join the filename with the STATIC_FONT_DIR
        font_path = os.path.join(settings.STATIC_FONT_DIR, font_filename)
        
        print(f"🧠 Attempting to load font: {font_path}")
        font = ImageFont.truetype(font_path, size)
        
        # Note: PIL doesn't support font weight/style directly, but we can handle it
        # by using different font files or post-processing
        return font
    except Exception as e:
        print(f"⚠️ Failed to load font {font_filename}: {e}")
        return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: float, draw: ImageDraw.Draw) -> List[str]:
    """Wrap text to fit within max_width."""
    if not max_width:
        return [text]
    
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Single word is too long, force it
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


def calculate_text_position(
    x: float, 
    y: float, 
    text: str, 
    font: ImageFont.FreeTypeFont, 
    alignment: str, 
    draw: ImageDraw.Draw,
    use_percentage: bool = False,
    image_width: int = 800,
    image_height: int = 600
) -> Tuple[float, float]:
    """Calculate text position with support for percentage-based positioning."""
    
    # Convert percentage to pixels if needed
    if use_percentage:
        x = (x / 100) * image_width
        y = (y / 100) * image_height
    
    # Handle text alignment
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    
    if alignment == "center":
        x = x - (text_width / 2)
    elif alignment == "right":
        x = x - text_width
    
    return x, y


def render_text_with_shadow(
    draw: ImageDraw.Draw,
    text: str,
    position: Tuple[float, float],
    font: ImageFont.FreeTypeFont,
    color: str,
    shadow_color: str = "#000000",
    shadow_offset: Tuple[int, int] = (2, 2)
) -> None:
    """Render text with shadow effect."""
    x, y = position
    
    # Draw shadow first
    shadow_x = x + shadow_offset[0]
    shadow_y = y + shadow_offset[1]
    draw.text((shadow_x, shadow_y), text, font=font, fill=shadow_color)
    
    # Draw main text
    draw.text((x, y), text, font=font, fill=color)


def parse_color(color_str: str) -> str:
    """Parse and validate color string."""
    # Remove any whitespace
    color_str = color_str.strip()
    
    # Check if it's a valid hex color
    if re.match(r'^#[0-9A-Fa-f]{6}$', color_str):
        return color_str
    
    # Check if it's a valid hex color without #
    if re.match(r'^[0-9A-Fa-f]{6}$', color_str):
        return f"#{color_str}"
    
    # Default to white if invalid
    print(f"⚠️ Invalid color format: {color_str}, using white")
    return "#FFFFFF"
