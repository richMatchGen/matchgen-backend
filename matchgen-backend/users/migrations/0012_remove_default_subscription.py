# Generated manually to remove default subscription assignment

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_user_email_verification_sent_at_and_more'),
    ]

    operations = [
        # First, make subscription_start_date nullable
        migrations.AlterField(
            model_name='club',
            name='subscription_start_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        # Then update the other fields
        migrations.AlterField(
            model_name='club',
            name='subscription_active',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='club',
            name='subscription_tier',
            field=models.CharField(blank=True, choices=[('basic', 'Basic Gen'), ('semipro', 'SemiPro Gen'), ('prem', 'Prem Gen')], max_length=20, null=True),
        ),
    ]
