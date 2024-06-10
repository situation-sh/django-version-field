#!/usr/bin/env python
import os
import shutil
from pathlib import Path

import django
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.management.commands.collectstatic import (
    Command as CollectStaticCommand,
)
from django.core import management
from django.core.management.commands import makemigrations, migrate, runserver

BASE_PATH = Path(__file__).parent

if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"
    os.environ["DJANGO_SUPERUSER_PASSWORD"] = "admin"
    django.setup()

    # collect static files
    management.call_command(
        CollectStaticCommand(),
        no_input=True,
        clear=True,
        interactive=False,
        verbosity=0,
    )
    # make migrations
    management.call_command(makemigrations.Command(), "tests")
    # migrate
    management.call_command(migrate.Command())
    # create superuser
    User = get_user_model()
    admin, _ = User.objects.get_or_create(username="admin")
    admin.is_superuser = True
    admin.set_password("admin")
    admin.save()

    # runserver
    management.call_command(runserver.Command())
    # clean all
    db = settings.DATABASES["default"]["NAME"]
    if os.path.exists(db):
        print(f"\nRemoving {db}")
        os.remove(db)
    if os.path.exists(settings.STATIC_ROOT):
        shutil.rmtree(settings.STATIC_ROOT)
    if os.path.exists(BASE_PATH / "tests" / "migrations"):
        shutil.rmtree(BASE_PATH / "tests" / "migrations")
