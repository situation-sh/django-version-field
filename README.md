# django-version-field

A field to handle software version information in Django models. Our main goal is to have useful lookups, i.e. to be able to make order comparisons between versions. This requires transforming the input into an integer. We have two desired properties:

1. To be able to reconstruct the input without losing information.
2. To preserve the order when transforming inputs into integers.

The main constraint is the max size of the interger that can be stored in the database (8-bytes). This constraint forces us to reject inputs that are too large to fit into our scheme. Please read the *Internals* section below for more details.

## Usage

> [!IMPORTANT]
> Invalid version strings, versions with local version information and inputs too large to be encoded will be rejected. Please read the *Internals* section for details.

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
assert TestModel.objects.filter(version___gte="1.2").count() == 2
```

## Testing

To run tests:

```shell
poetry run python runtests.py
```

To run an interactive server with the test app:

```shell
poetry run python dev.py
```

Then you can visit [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) with `admin/admin` credentials.

## Internals

The field parses the input string using the packaging.version `parse` method. `parse` expects an input complying with the following scheme,
```
[N!]N(.N)*[{a|b|rc}N][.postN][.devN]
```
where `N` are positive integers. Inputs not satisfying this condition with raise the `InvalidVersion` error.
Once the input is parsed, the field tries to create a bit stream by concatenating:

- The epoch number encoded into 4 bits.
- The major encoded into 12 bits.
- The minor encoded into 8 bits.
- The patch number (micro) encoded into 16 bits.
- The 4th part of the 'release' segment encoded into 8 bits.
- The pre-release number and symbol (`a`,`b` or `rc`) encoded into 6 bits and 2 bits, respectively.
- The post-release number and post-release flag encoded into 4 bits (3 bits for the number).
- The dev-release number encoded into 4 bits.

Inputs where a segment is too large to be encoded are rejected, raising `ValueError`.
The local version information is not encoded in our scheme, so inputs with local version information are rejected.
The input can contain more than 4 parts in the 'release' segment, but these must contain only '0', otherwise the input is rejected.

![Segment structure diagram](images/Version_Segment_Structure.pdf "Segment structure diagram")
