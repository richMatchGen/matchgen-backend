from django.core.management.base import BaseCommand
from graphicpack.models import GraphicPack, Template, TemplateElement, StringElement


class Command(BaseCommand):
    help = 'Create test templates for graphic packs'

    def handle(self, *args, **options):
        # Create a test graphic pack if it doesn't exist
        pack, created = GraphicPack.objects.get_or_create(
            name="Test Pack",
            defaults={
                'description': 'Test graphic pack with templates',
                'preview_image_url': 'https://via.placeholder.com/400x300',
            }
        )
        
        if created:
            self.stdout.write(f'Created graphic pack: {pack.name}')
        else:
            self.stdout.write(f'Using existing graphic pack: {pack.name}')

        # Create a matchday template
        template, created = Template.objects.get_or_create(
            graphic_pack=pack,
            content_type='matchday',
            defaults={
                'image_url': 'https://via.placeholder.com/800x600',
                'sport': 'football'
            }
        )
        
        if created:
            self.stdout.write(f'Created matchday template: {template.id}')
        else:
            self.stdout.write(f'Using existing matchday template: {template.id}')

        # Create some template elements
        elements_data = [
            {
                'type': 'text',
                'content_key': 'match_title',
                'x': 400,
                'y': 100,
                'use_percentage': False,
                'z_index': 1,
                'visible': True
            },
            {
                'type': 'text',
                'content_key': 'date',
                'x': 400,
                'y': 150,
                'use_percentage': False,
                'z_index': 2,
                'visible': True
            },
            {
                'type': 'text',
                'content_key': 'venue',
                'x': 400,
                'y': 200,
                'use_percentage': False,
                'z_index': 3,
                'visible': True
            }
        ]

        for element_data in elements_data:
            element, created = TemplateElement.objects.get_or_create(
                template=template,
                content_key=element_data['content_key'],
                defaults=element_data
            )
            
            if created:
                self.stdout.write(f'Created element: {element.content_key}')
                
                # Create string element for text elements
                if element.type == 'text':
                    string_element, created = StringElement.objects.get_or_create(
                        template_element=element,
                        defaults={
                            'text_content': f'Sample {element.content_key}',
                            'font_size': 24,
                            'color': '#FFFFFF',
                            'alignment': 'center'
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'Created string element for: {element.content_key}')

        self.stdout.write(
            self.style.SUCCESS('Successfully created test templates!')
        )

