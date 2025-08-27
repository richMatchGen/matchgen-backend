from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Club, ClubMembership, UserRole
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Fix club memberships for existing users who have clubs but no memberships'

    def handle(self, *args, **options):
        self.stdout.write('🔧 Fixing club memberships...')
        
        # Get or create the owner role
        owner_role, created = UserRole.objects.get_or_create(
            name='owner',
            defaults={'description': 'Club owner with full permissions'}
        )
        if created:
            self.stdout.write('✅ Created owner role')
        
        # Find users who have clubs but no memberships
        users_with_clubs = User.objects.filter(clubs__isnull=False).distinct()
        
        fixed_count = 0
        for user in users_with_clubs:
            clubs = user.clubs.all()
            
            for club in clubs:
                # Check if membership already exists
                membership_exists = ClubMembership.objects.filter(
                    user=user,
                    club=club
                ).exists()
                
                if not membership_exists:
                    # Create membership for the user as owner of their club
                    ClubMembership.objects.create(
                        user=user,
                        club=club,
                        role=owner_role,
                        status='active'
                    )
                    self.stdout.write(f'✅ Created membership for {user.email} as owner of {club.name}')
                    fixed_count += 1
                else:
                    self.stdout.write(f'ℹ️  Membership already exists for {user.email} in {club.name}')
        
        self.stdout.write(f'🎉 Fixed {fixed_count} club memberships!')
        
        # Show summary
        total_clubs = Club.objects.count()
        total_memberships = ClubMembership.objects.count()
        active_memberships = ClubMembership.objects.filter(status='active').count()
        
        self.stdout.write(f'\n📊 Summary:')
        self.stdout.write(f'   Total Clubs: {total_clubs}')
        self.stdout.write(f'   Total Memberships: {total_memberships}')
        self.stdout.write(f'   Active Memberships: {active_memberships}')
