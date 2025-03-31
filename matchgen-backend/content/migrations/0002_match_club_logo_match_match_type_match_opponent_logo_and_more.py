# Generated by Django 5.1.7 on 2025-03-31 10:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='club_logo',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='match_type',
            field=models.CharField(default='League', max_length=255),
        ),
        migrations.AddField(
            model_name='match',
            name='opponent_logo',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='sponsor',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='time_start',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='venue',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='match',
            name='location',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
