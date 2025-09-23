from django.core.management.base import BaseCommand
from users.models import Feature, SubscriptionTierFeature

class Command(BaseCommand):
    help = 'Set up comprehensive feature catalog with subscription tier mappings'

    def handle(self, *args, **options):
        self.stdout.write('🏗️  Setting up comprehensive feature catalog...')
        
        # Define all features
        features_data = [
            # Post Types
            {
                'name': 'Upcoming Fixture Posts',
                'code': 'post.upcoming',
                'description': 'Create posts for upcoming fixtures and matches'
            },
            {
                'name': 'Matchday Posts',
                'code': 'post.matchday',
                'description': 'Create matchday announcement posts'
            },
            {
                'name': 'Starting XI Posts',
                'code': 'post.startingxi',
                'description': 'Create team lineup announcement posts'
            },
            {
                'name': 'Substitution Posts',
                'code': 'post.substitution',
                'description': 'Create player substitution announcement posts'
            },
            {
                'name': 'Half Time Posts',
                'code': 'post.halftime',
                'description': 'Create half-time score update posts'
            },
            {
                'name': 'Full Time Posts',
                'code': 'post.fulltime',
                'description': 'Create final result announcement posts'
            },
            {
                'name': 'Goal Posts',
                'code': 'post.goal',
                'description': 'Create goal celebration posts'
            },
            {
                'name': 'Player of the Match Posts',
                'code': 'post.potm',
                'description': 'Create man of the match announcement posts'
            },
            
            # Team Management
            {
                'name': 'Multiple Teams',
                'code': 'team.multiple',
                'description': 'Support for managing multiple teams'
            },
            {
                'name': 'Team Management',
                'code': 'team.manage',
                'description': 'Full team management capabilities'
            },
            
            # Templates
            {
                'name': 'Basic Templates',
                'code': 'template.basic',
                'description': 'Access to basic post templates'
            },
            {
                'name': 'Enhanced Templates',
                'code': 'template.enhanced',
                'description': 'Access to enhanced post templates'
            },
            {
                'name': 'Bespoke Templates',
                'code': 'template.bespoke',
                'description': 'Access to custom bespoke templates'
            },
            
            # Analytics & Insights
            {
                'name': 'Basic Analytics',
                'code': 'analytics.basic',
                'description': 'Basic post performance analytics'
            },
            {
                'name': 'Advanced Analytics',
                'code': 'analytics.advanced',
                'description': 'Advanced analytics and insights'
            },
            
            # Support
            {
                'name': 'Email Support',
                'code': 'support.email',
                'description': 'Email support access'
            },
            {
                'name': 'Priority Support',
                'code': 'support.priority',
                'description': 'Priority support with faster response times'
            },
            
            # Advanced Features
            {
                'name': 'Bulk Post Generation',
                'code': 'post.bulk',
                'description': 'Generate multiple posts at once'
            },
            {
                'name': 'Post Scheduling',
                'code': 'post.schedule',
                'description': 'Schedule posts for future publication'
            },
            {
                'name': 'Custom Branding',
                'code': 'branding.custom',
                'description': 'Custom branding and logo placement'
            },
            {
                'name': 'API Access',
                'code': 'api.access',
                'description': 'API access for integrations'
            }
        ]
        
        # Create features
        created_features = []
        for feature_data in features_data:
            feature, created = Feature.objects.get_or_create(
                code=feature_data['code'],
                defaults={
                    'name': feature_data['name'],
                    'description': feature_data['description'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'✅ Created feature: {feature.name}')
            else:
                self.stdout.write(f'ℹ️  Feature already exists: {feature.name}')
            created_features.append(feature)
        
        # Define subscription tier feature mappings
        tier_features = {
            'basic': [
                'post.upcoming',
                'post.matchday',
                'post.startingxi',
                'template.basic',
                'support.email'
            ],
            'semipro': [
                'post.upcoming',
                'post.matchday',
                'post.startingxi',
                'post.substitution',
                'post.halftime',
                'post.fulltime',
                'post.goal',
                'template.enhanced',
                'support.email',
                'analytics.basic'
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
                'team.multiple',
                'team.manage',
                'template.bespoke',
                'support.priority',
                'analytics.advanced',
                'post.bulk',
                'post.schedule',
                'branding.custom',
                'api.access'
            ]
        }
        
        # Create subscription tier feature mappings
        self.stdout.write('\n🔗 Creating subscription tier feature mappings...')
        
        # Clear existing mappings
        SubscriptionTierFeature.objects.all().delete()
        self.stdout.write('🗑️  Cleared existing tier mappings')
        
        for tier, feature_codes in tier_features.items():
            self.stdout.write(f'\n📋 Setting up {tier.upper()} tier features:')
            for feature_code in feature_codes:
                try:
                    feature = Feature.objects.get(code=feature_code)
                    mapping, created = SubscriptionTierFeature.objects.get_or_create(
                        subscription_tier=tier,
                        feature=feature
                    )
                    if created:
                        self.stdout.write(f'  ✅ {feature.name}')
                    else:
                        self.stdout.write(f'  ℹ️  {feature.name} (already mapped)')
                except Feature.DoesNotExist:
                    self.stdout.write(f'  ❌ Feature not found: {feature_code}')
        
        # Summary
        self.stdout.write('\n📊 Feature Catalog Summary:')
        self.stdout.write(f'  Total Features: {Feature.objects.count()}')
        self.stdout.write(f'  Total Mappings: {SubscriptionTierFeature.objects.count()}')
        
        for tier in ['basic', 'semipro', 'prem']:
            feature_count = SubscriptionTierFeature.objects.filter(subscription_tier=tier).count()
            self.stdout.write(f'  {tier.upper()} Tier: {feature_count} features')
        
        self.stdout.write('\n🎉 Feature catalog setup complete!')
