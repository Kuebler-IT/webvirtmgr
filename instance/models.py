# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from servers.models import Compute

class Instance(models.Model):
    compute = models.ForeignKey(Compute)
    name = models.CharField(max_length=20)
    uuid = models.CharField(max_length=36)
    # display_name = models.CharField(max_length=50)
    # display_description = models.CharField(max_length=255)

