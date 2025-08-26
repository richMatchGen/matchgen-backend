from django.core.management.base import BaseCommand
from graphicpack.models import TextElement
from users.models import Club


class Command(BaseCommand):
    help = 'Add opponent logo image element to user\'s selected graphic pack'

    def add_arguments(self, parser):
        parser.add_argument('--user-email', type=str, help='User email to find their club')

    def handle(self, *args, **options):
        try:
            # Find user by email or use first club
            if options['user_email']:
                club = Club.objects.get(user__email=options['user_email'])
            else:
                club = Club.objects.first()
            
            if not club:
                self.stdout.write(self.style.ERROR('No club found'))
                return
            
            if not club.selected_pack:
                self.stdout.write(self.style.ERROR(f'Club {club.name} has no selected pack'))
                return
            
            pack = club.selected_pack
            self.stdout.write(f'Using club: {club.name} with pack: {pack.name}')
            
            # Check if opponent logo element already exists
            existing_element = TextElement.objects.filter(
                graphic_pack=pack,
                content_type='matchday',
                element_name='opponent_logo'
            ).first()
            
            if existing_element:
                self.stdout.write(self.style.WARNING(f'Opponent logo element already exists: {existing_element.id}'))
                return
            
            # Create the opponent logo image element
            element = TextElement.objects.create(
                graphic_pack=pack,
                content_type='matchday',
                element_name='opponent_logo',
                element_type='image',
                position_x=400,
                position_y=200,
                image_width=150,
                image_height=150,
                maintain_aspect_ratio=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Created opponent logo element: {element.id} for pack {pack.name}')
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))

