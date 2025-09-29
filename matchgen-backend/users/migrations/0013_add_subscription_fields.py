# Generated manually for subscription cancellation features

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_remove_default_subscription'),
    ]

    operations = [
        migrations.AddField(
            model_name='club',
            name='subscription_canceled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='club',
            name='stripe_subscription_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]





