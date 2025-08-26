from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import UserRole, Feature, SubscriptionTierFeature


class Command(BaseCommand):
    help = 'Set up initial RBAC system with roles, features, and subscription tiers'

    def handle(self, *args, **options):
        self.stdout.write('Setting up RBAC system...')
        
        with transaction.atomic():
            # Create user roles
            roles_data = [
                {
                    'name': 'owner',
                    'description': 'Full access to all club features including billing and team management'
                },
                {
                    'name': 'admin',
                    'description': 'Can manage players, fixtures, posts, and team members'
                },
                {
                    'name': 'editor',
                    'description': 'Can create posts and manage fixtures/players'
                },
                {
                    'name': 'viewer',
                    'description': 'Can view/download generated assets only'
                }
            ]
            
            for role_data in roles_data:
                role, created = UserRole.objects.get_or_create(
                    name=role_data['name'],
                    defaults={'description': role_data['description']}
                )
                if created:
                    self.stdout.write(f'Created role: {role.name}')
                else:
                    self.stdout.write(f'Role already exists: {role.name}')
            
            # Create features
            features_data = [
                {
                    'name': 'Upcoming Fixture Posts',
                    'code': 'post.upcoming',
                    'description': 'Generate posts for upcoming fixtures'
                },
                {
                    'name': 'Matchday Posts',
                    'code': 'post.matchday',
                    'description': 'Generate matchday announcement posts'
                },
                {
                    'name': 'Starting XI Posts',
                    'code': 'post.startingxi',
                    'description': 'Generate starting lineup posts'
                },
                {
                    'name': 'Substitution Posts',
                    'code': 'post.substitution',
                    'description': 'Generate substitution announcement posts'
                },
                {
                    'name': 'Half Time Posts',
                    'code': 'post.halftime',
                    'description': 'Generate half-time score posts'
                },
                {
                    'name': 'Full Time Posts',
                    'code': 'post.fulltime',
                    'description': 'Generate full-time result posts'
                },
                {
                    'name': 'Goal Posts',
                    'code': 'post.goal',
                    'description': 'Generate goal announcement posts'
                },
                {
                    'name': 'Player of the Match Posts',
                    'code': 'post.potm',
                    'description': 'Generate player of the match posts'
                },
                {
                    'name': 'Bespoke Templates',
                    'code': 'template.bespoke',
                    'description': 'Access to custom designed templates'
                },
                {
                    'name': 'Multiple Teams',
                    'code': 'team.multiple',
                    'description': 'Support for multiple teams'
                }
            ]
            
            for feature_data in features_data:
                feature, created = Feature.objects.get_or_create(
                    code=feature_data['code'],
                    defaults={
                        'name': feature_data['name'],
                        'description': feature_data['description']
                    }
                )
                if created:
                    self.stdout.write(f'Created feature: {feature.name}')
                else:
                    self.stdout.write(f'Feature already exists: {feature.name}')
            
            # Create subscription tier feature mappings
            tier_features = {
                'basic': [
                    'post.upcoming',
                    'post.matchday',
                    'post.startingxi'
                ],
                'semipro': [
                    'post.upcoming',
                    'post.matchday',
                    'post.startingxi',
                    'post.substitution',
                    'post.halftime',
                    'post.fulltime'
                ],
                'prem': [
                    'post.upcoming',
                    'post.matchday',
                    'post.startingxi',
                    'post.substitution',
                    'post.halftime',
                    'post.fulltime',
                    'post.goal',
                    'post.potm',
                    'template.bespoke',
                    'team.multiple'
                ]
            }
            
            for tier, feature_codes in tier_features.items():
                for feature_code in feature_codes:
                    try:
                        feature = Feature.objects.get(code=feature_code)
                        tier_feature, created = SubscriptionTierFeature.objects.get_or_create(
                            subscription_tier=tier,
                            feature=feature
                        )
                        if created:
                            self.stdout.write(f'Added {feature.name} to {tier} tier')
                    except Feature.DoesNotExist:
                        self.stdout.write(f'Warning: Feature {feature_code} not found')
            
            self.stdout.write(self.style.SUCCESS('RBAC system setup completed successfully!'))
