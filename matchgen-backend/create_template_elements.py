#!/usr/bin/env python
"""
Script to create sample template elements for graphic generation.
Run this with: python manage.py shell < create_template_elements.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from graphicpack.models import GraphicPack, Template, TemplateElement, StringElement, ImageElement

def create_sample_template_elements():
    """Create sample template elements for testing."""
    
    # Get the first graphic pack (or create one if none exists)
    try:
        pack = GraphicPack.objects.first()
        if not pack:
            pack = GraphicPack.objects.create(
                name="Classic Football Pack",
                description="A classic football graphic pack"
            )
            print(f"Created graphic pack: {pack.name}")
    except Exception as e:
        print(f"Error getting/creating graphic pack: {e}")
        return

    # Create or get matchday template
    template, created = Template.objects.get_or_create(
        graphic_pack=pack,
        content_type="matchday",
        defaults={
            "image_url": "https://via.placeholder.com/800x600/1976d2/ffffff?text=Matchday+Template",
            "sport": "football"
        }
    )
    
    if created:
        print(f"Created matchday template: {template.id}")
    else:
        print(f"Using existing matchday template: {template.id}")

    # Clear existing elements
    template.elements.all().delete()
    print("Cleared existing template elements")

    # Create text elements
    text_elements_data = [
        {
            "content_key": "club_name",
            "x": 400, "y": 100,
            "strings": [{"content_key": "club_name", "font_family": "Arial.ttf", "font_size": 36, "color": "#FFFFFF", "alignment": "center"}]
        },
        {
            "content_key": "Versus",
            "x": 400, "y": 150,
            "strings": [{"content_key": "Versus", "font_family": "Arial.ttf", "font_size": 24, "color": "#FFFFFF", "alignment": "center"}]
        },
        {
            "content_key": "opponent",
            "x": 400, "y": 200,
            "strings": [{"content_key": "opponent", "font_family": "Arial.ttf", "font_size": 36, "color": "#FFFFFF", "alignment": "center"}]
        },
        {
            "content_key": "date",
            "x": 400, "y": 300,
            "strings": [{"content_key": "date", "font_family": "Arial.ttf", "font_size": 24, "color": "#FFFFFF", "alignment": "center"}]
        },
        {
            "content_key": "start",
            "x": 400, "y": 350,
            "strings": [{"content_key": "start", "font_family": "Arial.ttf", "font_size": 20, "color": "#FFFFFF", "alignment": "center"}]
        },
        {
            "content_key": "time",
            "x": 400, "y": 380,
            "strings": [{"content_key": "time", "font_family": "Arial.ttf", "font_size": 24, "color": "#FFFFFF", "alignment": "center"}]
        },
        {
            "content_key": "venue",
            "x": 400, "y": 450,
            "strings": [{"content_key": "venue", "font_family": "Arial.ttf", "font_size": 20, "color": "#FFFFFF", "alignment": "center"}]
        },
    ]

    for element_data in text_elements_data:
        element = TemplateElement.objects.create(
            template=template,
            type="text",
            content_key=element_data["content_key"],
            x=element_data["x"],
            y=element_data["y"]
        )
        
        for string_data in element_data["strings"]:
            StringElement.objects.create(
                template=element,
                content_key=string_data["content_key"],
                font_family=string_data["font_family"],
                font_size=string_data["font_size"],
                color=string_data["color"],
                alignment=string_data["alignment"]
            )
        
        print(f"Created text element: {element_data['content_key']}")

    # Create image elements
    image_elements_data = [
        {
            "content_key": "club_logo",
            "x": 200, "y": 100, "width": 100, "height": 100
        },
        {
            "content_key": "opponent_logo",
            "x": 500, "y": 100, "width": 100, "height": 100
        },
    ]

    for element_data in image_elements_data:
        element = TemplateElement.objects.create(
            template=template,
            type="image",
            content_key=element_data["content_key"],
            x=element_data["x"],
            y=element_data["y"],
            width=element_data["width"],
            height=element_data["height"]
        )
        
        ImageElement.objects.create(
            template=element,
            content_key=element_data["content_key"],
            maintain_aspect_ratio=True
        )
        
        print(f"Created image element: {element_data['content_key']}")

    print(f"\n✅ Successfully created template elements for {pack.name}")
    print(f"Template ID: {template.id}")
    print(f"Text elements: {template.elements.filter(type='text').count()}")
    print(f"Image elements: {template.elements.filter(type='image').count()}")

if __name__ == "__main__":
    create_sample_template_elements()
