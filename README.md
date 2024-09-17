# django-version-field

[![build](https://github.com/situation-sh/django-version-field/actions/workflows/build.yml/badge.svg)](https://github.com/situation-sh/django-version-field/actions/workflows/build.yml)
[![test](https://github.com/situation-sh/django-version-field/actions/workflows/test.yml/badge.svg)](https://github.com/situation-sh/django-version-field/actions/workflows/test.yml)

A field to handle software version information in Django models.

Our main goal is to have useful lookups, i.e. to be able to make order comparisons between versions. This requires **transforming the input into an integer**. We have two desired properties:

1. To be able to reconstruct the input without losing information.
2. To preserve the order when transforming inputs into integers.

The main constraint is the max size of the integer that can be stored in the database (8-bytes). This constraint forces us to reject inputs that are too large to fit into our scheme. Please read the _Internals_ section below for more details.

## Install

Currently the package is not available on PyPI because of name collision (`django-version-field` is too close to another package, maybe `django-versionfield`). So you must install it from this repo:

```shell
pip install git+https://github.com/situation-sh/django-version-field@v0.3.0
```

## Usage

> [!IMPORTANT]
> Invalid version strings, versions with local version information and inputs too large to be encoded will be rejected. Please read the _Internals_ section for details.

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

where `N` are positive integers. Inputs not satisfying this condition will raise the `InvalidVersion` error.
Once the input is parsed, the field tries to create a bit stream by concatenating:

- The epoch number encoded into 4 bits.
- The major encoded into 12 bits.
- The minor encoded into 8 bits.
- The patch number (micro) encoded into 16 bits.
- The 4th part of the 'release' segment encoded into 8 bits.
- The pre-release number and symbol (`a`,`b` or `rc`) encoded into 6 bits and 2 bits, respectively.
- The post-release number and post-release flag encoded into 4 bits (3 bits for the number).
- The dev-release number encoded into 4 bits.

<table>
  <thead>
    <tr>
      <th>Byte</th>
      <th>0</th>
      <th>1</th>
      <th>2</th>
      <th>3</th>
      <th>4</th>
      <th>5</th>
      <th>6</th>
      <th>7</th>
      <th>8</th>
      <th>9</th>
      <th>10</th>
      <th>11</th>
      <th>12</th>
      <th>13</th>
      <th>14</th>
      <th>15</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>0</td>
      <td colspan="4">Epoch</td>
      <td colspan="12">Major</td>
    </tr>
    <tr>
      <td>2</td>
      <td colspan="8">Minor</td>
      <td colspan="8">Patch</td>
    </tr>
    <tr>
      <td>4</td>
      <td colspan="8">Patch</td>
      <td colspan="8">Additional release segment</td>
    </tr>
    <tr>
      <td>6</td>
      <td colspan="2">F</td>
      <td colspan="6">Pre-release</td>
      <td></td>
      <td colspan="3">Post-release</td>
      <td colspan="4">Dev-release</td>
    </tr>
  </tbody>
</table>

Inputs where a segment is too large to be encoded are rejected, raising `ValueError`.
The local version information is not encoded in our scheme, so inputs with local version information are rejected.
The input can contain more than 4 parts in the 'release' segment, but these must contain only '0', otherwise the input is rejected.

### Post-release

After comparing the release portion of two versions, a version which is **post-release** should be greater than a version which is **not post-release**. E.g. `'1.1post0'>'1.1'` and `'1.2'>'1.1post0'`. The post-release flag in our code is used to distinguish between post-release versions where the post-release number is `0` (such as `'1.1post0'`) and pure release versions (such as `'1.1'`).

### Pre-release

After comparing the release portion of two versions, a version which is **pre-release** should be lesser than a version which is **not pre-release**. E.g. `'1.1a3'<'1.1'` and `'1.2a3'>'1.1post0'`. After comparing the release portion of two versions, a version which is **dev-release** should be lesser than any other version, including **pre-release** versions. E.g. `'1.1dev5'<'1.1'`, `'1.1dev5'<'1.1a5'`, and naturally `'1.1a5dev5'<'1.1a5'`.

## Test Data

Test data was extracted from the Common Platform Enumeration (CPE) records from the National Vulnerability Database (NVD), the [CPE dictionary version 2.3](https://nvd.nist.gov/feeds/xml/cpe/dictionary/official-cpe-dictionary_v2.3.xml.gz), which contains an exhaustive list of software products with their versions.

The data was extracted and separated into three categories:

- "error": versions that do not respect the syntax established by `packaging.version`.
- "warning": versions that respect the correct syntax but are to large to encode with our 8-byte scheme, causing potential loss of information.
- "white": versions that respect the correct syntax and can be encoded correctly.
