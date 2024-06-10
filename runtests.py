#!/usr/bin/env python
# see https://docs.djangoproject.com/en/5.0/topics/testing/advanced/#id3

import os
import sys
from pathlib import Path

import django
from django.conf import settings
from django.test.utils import get_runner

BASE_PATH = Path(__file__).parent

if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"
    django.setup()
    runner_class = get_runner(settings)
    failures = runner_class().run_tests(["tests"])
    sys.exit(bool(failures))
