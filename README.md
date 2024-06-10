# django-version-field

A field to handle versions in Django models

## Usage

> [!IMPORTANT]
> The field stores every part [MAJOR].[MINOR].[PATCH] in 2 unsigned bytes so it raises error if one of this part is not within [0, 65535]

### Model

```python
from django.db import models

from django_version_field import VersionField


class TestModel(models.Model):
    version = VersionField()

```

### Comparison

Comparison in python

```python
M0 = TestModel(version="5.2")
M1 = TestModel(version="4.9.12")
assert M0.version > M1.version
```

### Lookup

Comparison in the database

```python
TestModel.objects.bulk_create([
    TestModel(version="1.0.5"),
    TestModel(version="1.2.17"),
    TestModel(version="2.0.1"),
])
assert TestModel.objects.filter(version_ge="1.2").count() == 2
```

## Testing

To run tests:

```shell
poetry run python runtests.py
```

To run an interactive server with the test app

```shell
poetry run python dev.py
```

Then you could visit [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) with `admin/admin` credentials.

## Internals

VersionField is stored as an ...
