import random

from django.test import TestCase
from packaging.version import InvalidVersion, Version

from django_version_field.field import VersionCodex

from .data import data
from .models import TestModel
from .test_params import test_size_for_instance_comparison


class DeclinationsTestCase(TestCase):
    ver_list = [
        "1!1.1.1.1post",
        "1!1.1.1.1",
        "1!1.1.1.1a0post",
        "1!1.1.1.1a0post0dev",
        "1!1.1.1.1a0",
        "1!1.1.1.1a0dev",
        "1!1.1.1.1dev",
    ]

    def setUp(self) -> None:
        _ = TestModel.objects.bulk_create(
            [TestModel(version=v, version_string=v) for v in self.ver_list]
        )

    def test_ordering_declinations(self) -> None:
        """Test that all possible declinations of a version are ordered correctly in the database"""
        q_set = TestModel.objects.order_by("-version")
        for i in range(len(self.ver_list)):
            assert Version(self.ver_list[i]) == q_set[i].version


class DataParsingTestCase(TestCase):
    def test_data_parsing(self) -> None:
        """Counts the number of faulty inputs from the NIST NVD CPE records."""
        total_examples = 0
        faulty_inputs = 0
        value_errors = 0
        for item in data["white"] + data["warning"] + data["error"]:
            total_examples += 1
            try:
                _ = Version(item)
                try:
                    _ = VersionCodex.version2int(item)
                except ValueError:
                    value_errors += 1
            except InvalidVersion:
                faulty_inputs += 1
        valid_inputs = total_examples - faulty_inputs
        value_error_percentage = value_errors / valid_inputs * 100
        valid_input_percentage = valid_inputs / total_examples * 100
        print(
            f"Total examples visited: {total_examples}, Faulty inputs: {faulty_inputs}, Percentage of valid inputs: {valid_input_percentage:.2f}%"
        )
        print(
            f"Value errors: {value_errors}, Percentage of valid examples ignored due to value errors: {value_error_percentage:.2f}%"
        )


class NvdCpeRecordsTestCase(TestCase):
    def setUp(self) -> None:
        _ = TestModel.objects.bulk_create(
            [TestModel(version=v, version_string=v) for v in data["white"]]
        )

    def test_input_reconstruction(self) -> None:
        """Test that the version object recovered from the database is equal to the original input."""
        for version_model in TestModel.objects.all():
            version_str = version_model.version_string
            version_obj = version_model.version
            assert version_obj == Version(
                version_str
            ), f"The reconstructed object '{version_obj.__str__()}' is semantically different from the original version '{version_str}'"

    def test_instance_comparison(self):
        """ "Test that the ordering of the encoded integers stored in the database is the same as the ordering
        of the version objects.
        """
        q_set = list(TestModel.objects.all())
        indx_set = range(len(q_set))
        for _ in range(test_size_for_instance_comparison):
            i, j = random.choice(indx_set), random.choice(indx_set)
            test_model1, test_model2 = q_set[i], q_set[j]
            version_str1, version_str2 = (
                test_model1.version_string,
                test_model2.version_string,
            )
            if Version(version_str1) > Version(version_str2):
                assert TestModel.objects.filter(
                    version__lt=version_str1, id=test_model2.id
                ).exists()
            else:
                assert TestModel.objects.filter(
                    version__gte=version_str1, id=test_model2.id
                ).exists()

    def test_lookup(self):
        for version_model in TestModel.objects.all():
            version_obj = version_model.version

            # Find a bigger version
            if version_obj.micro < 65535:
                version_obj_bigger = Version(
                    f"{version_obj.epoch}!{version_obj.major}.{version_obj.minor}.{version_obj.micro + 1}"
                )
            elif version_obj.minor < 255:
                version_obj_bigger = Version(
                    f"{version_obj.epoch}!{version_obj.major}.{version_obj.minor + 1}"
                )
            elif version_obj.major < 4095:
                version_obj_bigger = Version(
                    f"{version_obj.epoch}!{version_obj.major + 1}"
                )
            else:
                version_obj_bigger = Version("15!4095.255.65535.255post7")

            # Find a smaller version
            if not version_obj.is_devrelease:
                version_obj_smaller = Version(
                    f"{version_obj.epoch}!{version_obj.major}.{version_obj.minor}.{version_obj.micro}dev14"
                )
            elif version_obj.micro > 0:
                version_obj_smaller = Version(
                    f"{version_obj.epoch}!{version_obj.major}.{version_obj.minor}.{version_obj.micro - 1}"
                )
            elif version_obj.minor > 0:
                version_obj_smaller = Version(
                    f"{version_obj.epoch}!{version_obj.major}.{version_obj.minor - 1}"
                )
            elif version_obj.major > 0:
                version_obj_smaller = Version(
                    f"{version_obj.epoch}!{version_obj.major - 1}"
                )
            else:
                version_obj_smaller = Version("0.0.0.0dev0")

            assert TestModel.objects.filter(
                version__lte=version_obj_bigger.__str__(),
                version__gte=version_obj_smaller.__str__(),
                id=version_model.id,
            ).exists()
