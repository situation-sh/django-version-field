import copy
import logging
import os
import random
import time
from datetime import date
from typing import List, Tuple

from django.test import TestCase
from packaging.version import InvalidVersion, Version, _cmpkey, _Version

from django_version_field.field import VersionCodex

from .data import data
from .models import TestModel
from .test_params import test_size_for_instance_comparison

log_file_name = f"tests/logs/tests-{date.today()}.log"
os.makedirs(os.path.dirname(log_file_name), exist_ok=True)
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=log_file_name, encoding="utf-8", level=logging.DEBUG
)


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
    def test_white_data_parsing(self) -> None:
        """Test that the input string can be parsed and transformed into an integer."""
        for item in data["white"]:
            _ = VersionCodex.version2int(item)

    def test_warning_data_parsing(self) -> None:
        """Test that large input strings raise a value error."""
        logger.info("Started test_warning_data_parsing")
        for item in data["warning"]:
            try:
                _ = VersionCodex.version2int(item)
            except ValueError as error:
                logger.error(f"{item} cannot be encoded: {error}")
        logger.info("Finished test_warning_data_parsing")

    def test_error_data_parsing(self) -> None:
        """Test that faulty input strings raise an invalid version error."""
        logger.info("Started test_error_data_parsing")
        for item in data["error"]:
            try:
                _ = VersionCodex.version2int(item)
            except InvalidVersion as error:
                logger.error(f"{error}")
        logger.info("Finished test_error_data_parsing")

    def test_print_stats_nvd_records(self) -> None:
        total_examples = len(data["white"] + data["warning"] + data["error"])
        faulty_inputs = len(data["error"])
        value_errors = len(data["warning"])
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


#
# Test with bit shifts
#
CHUNKS = [
    ("epoch", 4),
    ("major", 12),
    ("minor", 8),
    ("patch", 16),
    ("release", 8),
    ("pre_l", 2),
    ("pre", 6),
    ("post", 4),
    ("dev", 4),
]


def pretty_print(value: int, chunks: List[Tuple[str, int]] = CHUNKS):

    def underline(size: int) -> str:
        if size <= 1:
            return "-"
        else:
            return "\u2570" + (size - 2) * "\u2500" + "\u256F"

    total_size = sum(size for _, size in chunks)
    value_bin = bin(value)[2:].rjust(total_size, "0")
    index = 0
    out: List[str] = []
    blocks: List[str] = []
    names: List[str] = []
    for name, size in chunks:
        out.append(value_bin[index : (index + size)])
        blocks.append(underline(size))
        names.append(name)
        index += size

    for i, (name, _) in enumerate(chunks):
        w = max(len(name), len(out[i]))
        out[i] = out[i].rjust(w, " ")
        blocks[i] = blocks[i].rjust(w, " ")
        names[i] = names[i].rjust(w, " ")

    print(" ".join(out))
    print(" ".join(blocks))
    print(" ".join(names))


class TestBitshift(TestCase):
    """
    +-------+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
    | Octet |  0 |  1 |  2 |  3 |  4 |  5 |  6 |  7 |  8 |  9 | 10 | 11 | 12 | 13 | 14 | 15 |
    +-------+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
    |     0 |       Epoch       |                           Major                           |
    +-------+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
    |     2 |              Minor                    |                 Patch                 |
    +-------+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
    |     4 |              Patch                    |      Additional release segment       |
    +-------+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
    |     6 |   Flag  |        Pre-release          |    | Post-release |    Dev-release    |
    +-------+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
    """

    BITS_1 = 0b1
    BITS_2 = 0b11
    BITS_3 = 0b111
    BITS_4 = 0b1111
    BITS_6 = 0b11_1111
    BITS_8 = 0b1111_1111
    BITS_12 = 0b1111_1111_1111
    BITS_16 = 0b1111_1111_1111_1111

    ALPHA = 0b01
    BETA = 0b10
    RELEASE_CANIDATE = 0b11

    PRE = {
        "a": ALPHA,
        "b": BETA,
        "rc": RELEASE_CANIDATE,
        None: 0,
    }
    PRE_INV = {v: k for k, v in PRE.items()}

    DUMMY_VERSION = Version("0.0.0")

    def version_to_int(self, v: Version) -> int:
        # Validate the input
        if (
            v.epoch > 15
        ):  # The value of the epoch is caped at '15' since only 4 bits are reserved for this field
            raise ValueError("Epoch number larger than 15")
        len_release = len(v.release)
        if len_release > 4:
            for i in range(
                4, len_release
            ):  # If there is only 0s after the 4th component we can ignore the 0s and still reconstruct the string
                if v.release[i] != 0:
                    raise ValueError(
                        "release segment has more than 4 components"
                    )
        if (
            v.major > 4095
        ):  # The value of major is caped at '4095' since only 12 bits are reserved for this field
            raise ValueError("Major release number larger than 4095")
        if (
            v.minor > 255
        ):  # The value of minor is caped at '255' since only 8 bits are reserved for this field
            raise ValueError("Minor release number larger than 255")
        if (
            v.micro > 65535
        ):  # The value of patch is caped at '65535' since only 16 bits are reserved for this field
            raise ValueError("Patch release number larger than 65535")
        if len_release > 3:
            if (
                v.release[3] > 255
            ):  # The value of the additional release field is caped at '255' since only 8 bits are reserved for this field
                raise ValueError("Additional release field larger than 255")
        if v.is_postrelease:
            if (
                v.post > 7
            ):  # The value of post is caped at '7' since only 3 bits are reserved for it
                raise ValueError("Post number larger than 7")
        if v.pre:
            if v.pre[1] > 62:
                raise ValueError(
                    "Pre-release number larger than 62"
                )  #  The value of pre is caped at '62' since only 6 bits are reserved for it and
                # .rc63 translates to '11111111', which is reserved for 'not pre-release'.
        if v.is_devrelease:
            if (
                v.dev > 15
            ):  # The value of dev is caped at '15' since only 4 bits are reserved for it
                raise ValueError("Dev number larger than 15")

        release = v.release[3] if len(v.release) >= 4 else 0
        # if v.pre is set we take it.
        # Otherwise it depends if we are in prerelease (prerelease = pre || dev).
        # If we are in dev, we set it to 0 otherwise to 1.
        pre = (
            v.pre[1]
            if v.pre is not None
            else (0 if v.is_prerelease else self.BITS_16)
        )
        # same as above
        pre_l = (
            self.PRE[v.pre[0]]
            if (v.pre is not None)
            else (0 if v.is_prerelease else self.BITS_16)
        )
        # the first value is a flag that indicates this is a post release
        post = (1, v.post) if v.is_postrelease else (0, 0)
        dev = v.dev if v.dev is not None else self.BITS_16

        return (
            (
                (v.epoch & self.BITS_4) << 60
            )  # The epoch number encoded into 4 bits.
            + (
                (v.major & self.BITS_12) << 48
            )  # The major encoded into 12 bits
            + ((v.minor & self.BITS_8) << 40)  # The minor encoded into 8 bits
            + (
                (v.micro & self.BITS_16) << 24
            )  # The patch number (micro) encoded into 16 bits
            + (
                (release & self.BITS_8) << 16
            )  # The 4th part of the 'release' segment encoded into 8 bits.
            + ((pre_l & self.BITS_2) << 14)  # alpha, beta, rc
            + ((pre & self.BITS_6) << 8)  # pre release number
            + (
                (post[0] & self.BITS_1) << 7
            )  # The first bit is a flag indicating that the version is a post version
            + ((post[1] & self.BITS_3) << 4)  # The value of post
            + ((dev & self.BITS_4))
        )

    def int_to_version(self, n: int) -> Version:
        epoch = (n >> 60) & self.BITS_4
        major = (n >> 48) & self.BITS_12
        minor = (n >> 40) & self.BITS_8
        micro = (n >> 24) & self.BITS_16
        release = (n >> 16) & self.BITS_8

        # if dev and pre are all at one, we are not in prerelease
        is_prerelease = not (
            ((n & self.BITS_4) == self.BITS_4)
            and (((n >> 8) & self.BITS_8) == self.BITS_8)
        )

        pre = (
            (self.PRE_INV[(n >> 14) & self.BITS_2], (n >> 8) & self.BITS_6)
            if (is_prerelease and ((n >> 14) & self.BITS_2) != 0)
            else None
        )
        post = (
            ("post", (n >> 4) & self.BITS_3)
            if (((n >> 7) & self.BITS_1) == self.BITS_1)
            else None
        )
        dev = (
            ("dev", n & self.BITS_4)
            if ((n & self.BITS_4) != self.BITS_4)
            else None
        )

        _version = _Version(
            epoch=epoch,
            release=(major, minor, micro, release),
            dev=dev,
            pre=pre,
            post=post,
            local=None,
        )

        # get a copy of a version object
        v = copy.deepcopy(self.DUMMY_VERSION)
        # do like the Version constructor (update the internals)
        v._version = _version
        v._key = _cmpkey(
            _version.epoch,
            _version.release,
            _version.pre,
            _version.post,
            _version.dev,
            _version.local,
        )
        return v

    def test_edge_case(self):
        dev = "1.5.13b5dev1"
        pre = "1.5.13pre1"
        assert Version(dev) < Version(pre)

        for v in [dev, pre]:
            codex = VersionCodex.version2int(v)
            local = self.version_to_int(Version(v))
            pretty_print(local)
            pretty_print(codex)

    def test_version_to_int(self):
        for v in data["white"]:
            version = Version(v)
            codex = VersionCodex.version2int(v)
            local = self.version_to_int(version)
            assertion_msg = f"{codex} != {local}\n"
            assertion_msg += f"RAW: {v}\nVERSION: {version}\nLOCAL BIN: {bin(local)}\nCODEX BIN: {bin(codex)}"

            try:
                assert codex == local, assertion_msg
            except AssertionError as err:
                print("-" * 80)
                pretty_print(local)
                pretty_print(codex)
                print(v)
                print(err)
                raise err

    def test_int_to_version(self):
        for v in data["white"]:
            version = Version(v)
            codex = VersionCodex.version2int(v)
            local = self.int_to_version(codex)
            assertion_msg = f"{version} != {local}\n"
            # assertion_msg += f"RAW: {v}\nVERSION: {version}\nLOCAL BIN: {bin(local)}\nCODEX BIN: {bin(codex)}"

            try:
                assert version == local, assertion_msg
            except AssertionError as err:
                print("-" * 80)
                print(local)
                pretty_print(codex)
                print(v)
                print(err)
                raise err

    def test_speed(self):
        print(
            "Speed Test: transform a version string into integer and then back into a version object"
        )
        print("Using white data")
        # bin version
        start1 = time.time()
        for item in data["white"]:
            _ = Version(
                VersionCodex.int2version(VersionCodex.version2int(item))
            )
        end1 = time.time()
        print(f"VersionCodex took {end1-start1} seconds.")
        # bit shift version
        start2 = time.time()
        for item in data["white"]:
            _ = self.int_to_version(self.version_to_int(Version(item)))
        end2 = time.time()
        print(f"Bit-shift took {end2-start2} seconds.")
