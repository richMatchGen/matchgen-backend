# Generated manually for scheduled subscription downgrades

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_add_subscription_fields_final'),
    ]

    operations = [
        migrations.AddField(
            model_name='club',
            name='scheduled_tier',
            field=models.CharField(
                max_length=20, 
                choices=[('basic', 'Basic Gen'), ('semipro', 'SemiPro Gen'), ('prem', 'Prem Gen')], 
                blank=True, 
                null=True,
                help_text='Tier scheduled to take effect at the end of current billing period'
            ),
        ),
    ]








