from django.test import TestCase
from .models import TestModel
from .data import data
from .test_params import test_size_for_instance_comparison
from django_version_field.field import VersionCodex
from packaging.version import parse, InvalidVersion
import random


class VersionTestCase(TestCase):
    def setUp(self) -> None:
        """
        Initialize the database used in other tests. 
        The creation of the model with VersionField and the parsing of the version string are tested in this function. 
        """
        total_examples = 0
        faulty_inputs = 0
        overflow_errors = 0
        for item in data[:50000]:
            total_examples += 1
            try:
                _, _ = TestModel.objects.get_or_create(
                    version=item, # Stored in the VersionField as an int for lookups
                    version_string=item, # Stored as exact version_strings
                    )
            except InvalidVersion as error: # Triggers when 'parse' encounters a faulty input.
                # print(f"{error}: '{item}' is not a valid version string.")
                faulty_inputs += 1
                continue
            except ValueError as error: # Triggers when a version segment is too large to be encoded.
                overflow_errors += 1
                # print(f"Cannot encode '{item}'. {error}")
                continue
        valid_inputs = total_examples - faulty_inputs
        overflow_percentage = overflow_errors / valid_inputs * 100
        valid_input_percentage = valid_inputs / total_examples * 100
        print(
            f"Total examples visited: {total_examples}, Faulty inputs: {faulty_inputs}, Percentage of valid inputs: {valid_input_percentage}%"
        )
        print(
            f"Overflow errors: {overflow_errors}, Percentage of valid examples ignored due to overflow: {overflow_percentage}%"
        )

    def test_input_reconstruction(self) -> None:
        """"Test that the version object recovered from the database is equal to the original input."""
        for version_model in TestModel.objects.all():
            version_str = version_model.version_string
            version_obj = version_model.version
            try: 
                assert version_obj == parse(version_str)
            except AssertionError:
                print(version_obj)
                print(version_str)

    def test_instance_comparison(self):
        """"Test that the ordering of the encoded integers stored in the database is the same as the ordering
        of the version objects.
        """
        q_set = list(TestModel.objects.all())
        indx_set = range(len(q_set))
        for _ in range(test_size_for_instance_comparison): #TODO: Set parameters
            i, j = random.choice(indx_set), random.choice(indx_set)
            version_str1, version_str2 = q_set[i].version_string, q_set[j].version_string
            # Version objects constructed from original version strings
            version_obj1, version_obj2 = parse(version_str1), parse(version_str2) 
            # Encoded version as it is stored in the database
            version_int1, version_int2 = (
                VersionCodex.version2int(version_str1),
                VersionCodex.version2int(version_str2),
                )            
            assert (version_obj1 > version_obj2) == (version_int1 > version_int2)

    def test_lookup(self):
        q_set = TestModel.objects.all()
        for version_model in q_set:
            version_obj = version_model.version

            # Find a bigger version            
            if version_obj.micro < 65535:
                version_obj_bigger = parse(f'{version_obj.epoch}!{version_obj.major}.{version_obj.minor}.{version_obj.micro + 1}')
            elif version_obj.minor < 255:
                version_obj_bigger = parse(f'{version_obj.epoch}!{version_obj.major}.{version_obj.minor + 1}')
            elif version_obj.major < 4095:
                version_obj_bigger = parse(f'{version_obj.epoch}!{version_obj.major + 1}')
            else:
                version_obj_bigger = parse('15!4095.255.65535.255post7')

            # Find a smaller version
            if not version_obj.is_devrelease:
                version_obj_smaller = parse(f'{version_obj.epoch}!{version_obj.major}.{version_obj.minor}.{version_obj.micro}dev14')
            elif version_obj.micro > 0:
                version_obj_smaller = parse(f'{version_obj.epoch}!{version_obj.major}.{version_obj.minor}.{version_obj.micro - 1}')
            elif version_obj.minor > 0:
                version_obj_smaller = parse(f'{version_obj.epoch}!{version_obj.major}.{version_obj.minor - 1}')
            elif version_obj.major > 0:
                version_obj_smaller = parse(f'{version_obj.epoch}!{version_obj.major - 1}')   
            else:
                version_obj_smaller = parse('0.0.0.0dev0')

            query = q_set.filter(version__lte=version_obj_bigger.__str__(), version__gte=version_obj_smaller.__str__())
            version_list = [test_model.version for test_model in query]
            assert version_obj in version_list
