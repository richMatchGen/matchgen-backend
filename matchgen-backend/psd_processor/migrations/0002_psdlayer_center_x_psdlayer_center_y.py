# Generated manually for center point fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('psd_processor', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='psdlayer',
            name='center_x',
            field=models.FloatField(default=0.0, help_text='Center X coordinate of layer'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='psdlayer',
            name='center_y',
            field=models.FloatField(default=0.0, help_text='Center Y coordinate of layer'),
            preserve_default=False,
        ),
    ]






