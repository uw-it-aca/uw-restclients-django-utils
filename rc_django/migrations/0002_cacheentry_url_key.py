# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-03 23:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rc_django', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cacheentry',
            name='url_key',
            field=models.SlugField(max_length=40, null=True),
        ),
    ]