# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0004_auto_20161201_1451'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='in_reply_to',
            field=models.ForeignKey(related_name='replies', to='archive.Message', null=True),
            preserve_default=True,
        ),
    ]
