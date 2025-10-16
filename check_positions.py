import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from graphicpack.models import TextElement

club = TextElement.objects.filter(element_name='club_logo').first()
opponent = TextElement.objects.filter(element_name='opponent_logo').first()

if club and opponent:
    print('Club Logo:')
    print(f'  Position: ({club.position_x}, {club.position_y})')
    print(f'  Home: ({club.home_position_x}, {club.home_position_y})')
    print(f'  Away: ({club.away_position_x}, {club.away_position_y})')
    print()
    print('Opponent Logo:')
    print(f'  Position: ({opponent.position_x}, {opponent.position_y})')
    print(f'  Home: ({opponent.home_position_x}, {opponent.home_position_y})')
    print(f'  Away: ({opponent.away_position_x}, {opponent.away_position_y})')
else:
    print('No logo elements found')




