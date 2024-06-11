from django.db import models

from django_version_field import VersionField


class TestModel(models.Model):
    version = VersionField()
    version_string = models.CharField(max_length=50)
