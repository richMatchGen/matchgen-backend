#!/usr/bin/env python
"""
Script to create missing templates for a graphic pack.
This script will create templates for all the content types that the backend expects.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from graphicpack.models import GraphicPack, Template, TemplateElement, StringElement
from django.db import transaction

def create_missing_templates():
    """Create missing templates for all graphic packs."""
    
    # Get all graphic packs
    graphic_packs = GraphicPack.objects.all()
    
    # Define the content types that the backend expects
    content_types = [
        "matchday",
        "upcomingFixture", 
        "startingXI",
        "goal",
        "sub",
        "halftime",
        "fulltime"
    ]
    
    for pack in graphic_packs:
        print(f"\nProcessing Graphic Pack: {pack.name} (ID: {pack.id})")
        
        # Check existing templates
        existing_templates = Template.objects.filter(graphic_pack=pack)
        existing_content_types = [t.content_type for t in existing_templates]
        
        print(f"Existing templates: {existing_content_types}")
        
        # Create missing templates
        for content_type in content_types:
            if content_type not in existing_content_types:
                print(f"Creating template for content_type: {content_type}")
                
                try:
                    with transaction.atomic():
                        # Create the template
                        template = Template.objects.create(
                            graphic_pack=pack,
                            content_type=content_type,
                            image_url=f"https://via.placeholder.com/800x600/1976d2/ffffff?text={content_type}+Template",
                            sport="football"
                        )
                        
                        print(f"  Created template ID: {template.id}")
                        
                        # Create some basic template elements based on content type
                        if content_type == "matchday":
                            # Create elements for matchday template
                            elements_data = [
                                {
                                    'type': 'text',
                                    'content_key': 'date',
                                    'x': 200,
                                    'y': 150,
                                    'use_percentage': False,
                                    'z_index': 1,
                                    'visible': True
                                },
                                {
                                    'type': 'text',
                                    'content_key': 'time',
                                    'x': 400,
                                    'y': 150,
                                    'use_percentage': False,
                                    'z_index': 2,
                                    'visible': True
                                },
                                {
                                    'type': 'text',
                                    'content_key': 'venue',
                                    'x': 300,
                                    'y': 250,
                                    'use_percentage': False,
                                    'z_index': 3,
                                    'visible': True
                                }
                            ]
                        elif content_type == "upcomingFixture":
                            # Create elements for upcoming fixture template
                            elements_data = [
                                {
                                    'type': 'text',
                                    'content_key': 'opponent',
                                    'x': 300,
                                    'y': 200,
                                    'use_percentage': False,
                                    'z_index': 1,
                                    'visible': True
                                },
                                {
                                    'type': 'text',
                                    'content_key': 'date',
                                    'x': 300,
                                    'y': 250,
                                    'use_percentage': False,
                                    'z_index': 2,
                                    'visible': True
                                }
                            ]
                        else:
                            # Default elements for other templates
                            elements_data = [
                                {
                                    'type': 'text',
                                    'content_key': 'title',
                                    'x': 300,
                                    'y': 200,
                                    'use_percentage': False,
                                    'z_index': 1,
                                    'visible': True
                                }
                            ]
                        
                        # Create template elements
                        for element_data in elements_data:
                            element = TemplateElement.objects.create(
                                template=template,
                                **element_data
                            )
                            
                            # Create string element for text elements
                            if element.type == 'text':
                                StringElement.objects.create(
                                    template_element=element,
                                    content_key=element_data['content_key'],
                                    font_family='Arial',
                                    font_size=24,
                                    color='#FFFFFF',
                                    alignment='center'
                                )
                            
                            print(f"    Created element: {element.content_key}")
                        
                        print(f"  Successfully created template for {content_type}")
                        
                except Exception as e:
                    print(f"  Error creating template for {content_type}: {str(e)}")
            else:
                print(f"Template for {content_type} already exists")
    
    print("\nTemplate creation completed!")

if __name__ == "__main__":
    create_missing_templates()

