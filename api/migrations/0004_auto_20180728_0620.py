# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-07-28 11:20
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_auto_20180728_0618'),
    ]

    operations = [
        migrations.RenameField(
            model_name='answers',
            old_name='question_id',
            new_name='question',
        ),
    ]