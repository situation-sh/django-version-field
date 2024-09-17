from typing import Any

from django.db import models
from packaging.version import Version, parse


class VersionCodex:
    """Helper class to transform version strings into 8-byte signed integer representations"""

    # The first two bits in the pre-release byte encode the letter portion of the pre-release segment
    pre_release_dict = {
        "a": "01",
        "b": "10",
        "rc": "11",
    }
    inv_pre_release_dict = {
        "01": "a",
        "10": "b",
        "11": "rc",
    }

    @classmethod
    def version2int(cls, version: str) -> int:
        """Encode version string into an 8-byte unsigned integer representation.
        version: str. packaging.version.parse will check that the input is a valid version string.
        This function preserves ordering of the public portion of 'Version' objects from 'packaging.version'.
        Does not preserve all information, notably:
            -Local release information is lost.
        Also, the data must fulfil certain constraints:
            -The epoch number must fit 4 bits.
            -The major must fit 12 bits.
            -The minor must fit 8 bits.
            -The patch number must fit 16 bits.
            -The 4th part of the 'release' segment must fit 8 bits.
            -Additional parts of the 'release' segment must contain only '0'.
            -The pre-release number must fit 6 bits.
            -The post-release number must fit 3 bits.
            -The dev-release number must fit 4 bits.
        The bit stream is form as: [epoch + release + pre + post + dev]. This order is chosen to preserve the ordering established by packaging.version Version objects.
        """

        # Parse the version string
        version_obj = parse(version)

        if version_obj.local is not None:
            raise ValueError("Cannot store local version information")

        # Epoch information
        epoch = version_obj.epoch
        if (
            epoch > 15
        ):  # The value of the epoch is caped at '15' since only 4 bits are reserved for this field
            raise ValueError("Epoch number larger than 15")
        bit_stream = bin(epoch)[2:].rjust(4, "0")

        # Release information
        release = version_obj.release
        len_release = len(release)
        if len_release > 4:
            for i in range(
                4, len_release
            ):  # If there is only 0s after the 4th component we can ignore the 0s and still reconstruct the string
                if release[i] != 0:
                    raise ValueError(
                        "release segment has more than 4 components"
                    )

        major = version_obj.major
        if (
            major > 4095
        ):  # The value of major is caped at '4095' since only 12 bits are reserved for this field
            raise ValueError("Major release number larger than 4095")
        bit_stream += bin(major)[2:].rjust(12, "0")

        minor = version_obj.minor
        if (
            minor > 255
        ):  # The value of minor is caped at '255' since only 8 bits are reserved for this field
            raise ValueError("Minor release number larger than 255")
        bit_stream += bin(minor)[2:].rjust(8, "0")

        patch = version_obj.micro
        if (
            patch > 65535
        ):  # The value of patch is caped at '65535' since only 16 bits are reserved for this field
            raise ValueError("Patch release number larger than 65535")
        bit_stream += bin(patch)[2:].rjust(16, "0")

        if len_release > 3:
            add_release = release[3]
            if (
                add_release > 255
            ):  # The value of the additional release field is caped at '255' since only 8 bits are reserved for this field
                raise ValueError("Additional release field larger than 255")
            bit_stream += bin(add_release)[2:].rjust(8, "0")
        else:
            bit_stream += "00000000"

        # Post-release information
        if version_obj.is_postrelease:
            post_number = version_obj.post
            if (
                post_number > 7
            ):  # The value of post is caped at '7' since only 3 bits are reserved for it
                raise ValueError("Post number larger than 7")
            # The first bit is a flag indicating that the version is a post version
            post_bit_stream = "1" + bin(post_number)[2:].rjust(3, "0")
        else:
            post_bit_stream = "0000"

        # Pre-release and dev-release information
        if version_obj.is_devrelease and version_obj.pre:
            pre_letter, pre_number = version_obj.pre
            if pre_number > 62:
                raise ValueError(
                    "Pre-release number larger than 62"
                )  #  The value of pre is caped at '62' since only 6 bits are reserved for it and
                # .rc63 translates to '11111111', which is reserved for 'not pre-release'.
            pre_bit_stream = cls.pre_release_dict[pre_letter] + bin(
                pre_number
            )[2:].rjust(
                6, "0"
            )  # The pre-release letter is encoded in 2 bits
            dev_number = version_obj.dev
            if (
                dev_number > 15
            ):  # The value of dev is caped at '15' since only 4 bits are reserved for it
                raise ValueError("Dev number larger than 15")
            dev_bit_stream = bin(dev_number)[2:].rjust(4, "0")
        elif version_obj.is_devrelease and version_obj.pre is None:
            pre_bit_stream = "00000000"
            dev_number = version_obj.dev
            if (
                dev_number > 15
            ):  # The value of dev is caped at '15' since only 4 bits are reserved for it
                raise ValueError("Dev number larger than 15")
            dev_bit_stream = bin(dev_number)[2:].rjust(4, "0")
        elif not version_obj.is_devrelease and version_obj.pre:
            pre_letter, pre_number = version_obj.pre
            if pre_number > 62:
                raise ValueError(
                    "Pre-release number larger than 62"
                )  #  The value of pre is caped at '62' since only 6 bits are reserved for it and
                # .rc63 translates to '11111111', which is reserved for 'not pre-release'.
            pre_bit_stream = cls.pre_release_dict[pre_letter] + bin(
                pre_number
            )[2:].rjust(
                6, "0"
            )  # The pre-release letter is encoded in 2 bits
            dev_bit_stream = "1111"
        else:
            pre_bit_stream = "11111111"
            dev_bit_stream = "1111"

        bit_stream += pre_bit_stream + post_bit_stream + dev_bit_stream
        return int("0b" + bit_stream, 2)

    @classmethod
    def int2version(cls, integer: int) -> str:
        """Inverse transformation of 'version2int'. Decodes input 8-byte unsigned integer into a version string.
        integer: int. An integer number produced by 'version2int'.
        Values are transformed into a string that conforms with the expected input pattern of 'packaging.version.parse'.
        To understand the expected format of the bit stream please look at the documentation of version2int.
        """
        if not (0 <= integer <= 18446744073709551615):  # Validate the input
            raise ValueError("Input must be 8-byte unsigned integer")

        bit_stream = bin(integer)[2:].rjust(64, "0")
        epoch_bits = bit_stream[:4]
        major_bits = bit_stream[4:16]
        minor_bits = bit_stream[16:24]
        patch_bits = bit_stream[24:40]
        add_bits = bit_stream[40:48]
        pre_bits = bit_stream[48:56]
        post_bits = bit_stream[56:60]
        dev_bits = bit_stream[60:64]

        version_string = ""

        # Epoch information
        if not (epoch_bits == "0000"):
            epoch_num = int("0b" + epoch_bits, 2)
            version_string += str(epoch_num) + "!"

        # Release information
        major_num = int("0b" + major_bits, 2)
        version_string += str(major_num) + "."
        minor_num = int("0b" + minor_bits, 2)
        version_string += str(minor_num) + "."
        patch_num = int("0b" + patch_bits, 2)
        version_string += str(patch_num) + "."
        add_num = int("0b" + add_bits, 2)
        version_string += str(add_num)

        # Post-release information
        post_string = ""
        if not (
            post_bits[0] == "0"
        ):  # The first bit in the post section is a flag
            post_num = int("0b" + post_bits[1:], 2)
            post_string = "post" + str(post_num)

        # Pre-release and dev-release information
        pre_string, dev_string = "", ""
        if pre_bits == "00000000":  # Only dev information
            dev_num = int("0b" + dev_bits, 2)
            dev_string = "dev" + str(dev_num)
        elif (
            pre_bits != "11111111" and dev_bits == "1111"
        ):  # Only pre-release information
            pre_code = cls.inv_pre_release_dict[
                pre_bits[:2]
            ]  # The two first bits determine the prefix
            pre_num = int(pre_bits[2:], 2)
            pre_string = pre_code + str(pre_num)
        elif pre_bits != "11111111":  # Pre-release and dev information
            pre_code = cls.inv_pre_release_dict[
                pre_bits[:2]
            ]  # The two first bits determine the prefix
            pre_num = int(pre_bits[2:], 2)
            dev_num = int("0b" + dev_bits, 2)
            pre_string = pre_code + str(pre_num)
            dev_string = "dev" + str(dev_num)

        version_string += pre_string + post_string + dev_string
        return version_string


class VersionField(models.PositiveBigIntegerField):
    description = "Software versions encoded in 8-byte signed integers. Ideal for comparing software versions on lookups."

    def from_db_value(
        self, value: Any, expression: str, connection: Any
    ) -> None | Version:
        if value is None:
            return value
        return Version(VersionCodex.int2version(value))

    def to_python(self, value: Any) -> None | str:
        if isinstance(value, str):
            return value

        if value is None:
            return value

        return VersionCodex.int2version(value)

    def get_prep_value(self, value: str) -> int:
        if isinstance(value, int):
            return value
        return VersionCodex.version2int(value)
