# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-04 21:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rc_django', '0002_auto_20170504_2132'),
    ]

    operations = [
        migrations.AddField(
            model_name='cacheentry',
            name='url_key',
            field=models.SlugField(max_length=40, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='cacheentry',
            unique_together=set([]),
        ),
        migrations.AlterField(
            model_name='cacheentry',
            name='url',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='cacheentry',
            name='url_key',
            field=models.SlugField(max_length=40, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='cacheentry',
            unique_together=set([('service', 'url_key')]),
        ),
    ]
