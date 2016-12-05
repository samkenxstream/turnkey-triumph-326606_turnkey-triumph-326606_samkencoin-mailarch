# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0003_auto_20161026_1151'),
    ]

    operations = [
        migrations.RenameField('Message', 'in_reply_to', 'in_reply_to_value'),
    ]
