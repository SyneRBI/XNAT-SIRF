from pathlib import Path
from typing import Any, Tuple

import ismrmrd
import xmlschema


def get_dict_values(dict: dict, key_list: list[Any]) -> Any:
    """Given a dictionary and a list of keys, a new filtered
    dictionary is returned"""
    if key_list:
        result = dict
        for key in key_list:
            result = result[key]
        return result
    else:
        return None


def get_main_parameter_groups(ismrmrd_dict: dict[str, Any]) -> list[list[Any]]:
    """Given a dictionary, pull out the main parameter groups i.e. keys and
    return in a list"""
    xnat_mrd_list = []
    for ckeys in ismrmrd_dict.keys():
        if "@" not in ckeys and "userParameter" not in ckeys:
            xnat_mrd_list.append([ckeys])
    return xnat_mrd_list


def create_list_param_names(
    xnat_mrd_list: list[list[Any]], ismrmrd_dict: dict[str, Any]
) -> list[list[Any]]:
    """Given a dictionary with info from Mrd headers and a list of main parameter groups
    return a list of parameter names nested within main parameter groups"""
    for _ in range(5):
        flag_finished = True
        xnat_mrd_list_new = []
        for ckey_list in xnat_mrd_list:
            cvals = get_dict_values(ismrmrd_dict, ckey_list)
            if isinstance(cvals, dict):
                flag_finished = False
                xnat_mrd_list_new.extend([ckey_list + [ckey] for ckey in cvals.keys()])
            elif isinstance(cvals, list):
                list_had_dicts = False
                for idx, item in enumerate(cvals):
                    if isinstance(item, dict):
                        list_had_dicts = True
                        xnat_mrd_list_new.extend(
                            [ckey_list + [idx, ckey] for ckey in item.keys()]
                        )
                    else:
                        xnat_mrd_list_new.append(ckey_list + [idx])
                if list_had_dicts:
                    flag_finished = False
            else:
                xnat_mrd_list_new.append(ckey_list)

        if flag_finished:
            break
        xnat_mrd_list = xnat_mrd_list_new
    return xnat_mrd_list


def handle_coil_label(
    xnat_mrd_list: list[list[Any]],
    ismrmrd_dict: dict[str, Any],
    xnat_mrd_dict: dict[str, str],
) -> Tuple[list[list[Any]], dict[str, str]]:
    """
    Process and consolidate coil label information from ismrmrd_dict.

    This function extracts coil names from the acquisitionSystemInformation header,
    concatenates them into a single string, and stores it in xnat_mrd_dict.
    It also removes the individual coil label entries from the parameter list to
    avoid duplication.
    """
    coil_idx = [
        idx
        for idx, item in enumerate(xnat_mrd_list)
        if (len(item)) > 3
        and item[0] == "acquisitionSystemInformation"
        and item[1] == "coilLabel"
        and item[3] == "coilName"
    ]

    coil_label_strg = ""
    for idx in coil_idx:
        coil_value = get_dict_values(ismrmrd_dict, xnat_mrd_list[idx])
        coil_label_strg += str(coil_value) + " "

    if len(coil_label_strg) > 255:
        coil_label_strg = coil_label_strg[:243] + " (truncated)"

    xnat_mrd_dict["mrd:mrdScanData/acquisitionSystemInformation/coilLabelList"] = (
        coil_label_strg
    )
    xnat_mrd_list = [
        elem
        for elem in xnat_mrd_list
        if elem[0] != "acquisitionSystemInformation" and elem[1] != "coilLabel"
    ]

    return xnat_mrd_list, xnat_mrd_dict


def handle_waveform_info(
    xnat_mrd_list: list[list[Any]],
    ismrmrd_dict: dict[str, Any],
    xnat_mrd_dict: dict[str, str],
) -> Tuple[list[list[Any]], dict[str, str]]:
    """
    Process and consolidate waveform information from ismrmrd_dict.

    This function extracts waveform types from the waveformInformation header,
    concatenates them into a single string, and stores it in xnat_mrd_dict.
    """
    waveform_idx = [
        idx
        for idx, item in enumerate(xnat_mrd_list)
        if item[0] == "waveformInformation" and item[2] == "waveformType"
    ]

    waveform_strg = ""
    for idx in waveform_idx:
        waveform_value = get_dict_values(ismrmrd_dict, xnat_mrd_list[idx])
        waveform_strg += str(waveform_value) + " "

    if len(waveform_strg) > 255:
        waveform_strg = waveform_strg[:243] + " (truncated)"

    xnat_mrd_dict["mrd:mrdScanData/waveformInformationList"] = waveform_strg
    xnat_mrd_list = [elem for elem in xnat_mrd_list if elem[0] != "waveformInformation"]
    return xnat_mrd_list, xnat_mrd_dict


def handle_encoding(xnat_mrd_list: list[list[Any]]) -> list[list[Any]]:
    """
    Filter out unwanted encoding parameters from xnat_mrd_list.

    This function removes specific encoding-related parameters that should not be
    included in the final XNAT data.
    """
    xnat_mrd_list = [
        elem for elem in xnat_mrd_list if elem[0] != "encoding" or elem[1] == 0
    ]
    xnat_mrd_list = [
        elem
        for elem in xnat_mrd_list
        if elem[:3] != ["encoding", 0, "trajectoryDescription"]
    ]
    xnat_mrd_list = [
        elem
        for elem in xnat_mrd_list
        if elem[:5] != ["encoding", 0, "multiband", "spacing", "dZ"]
    ]
    xnat_mrd_list = [
        elem
        for elem in xnat_mrd_list
        if elem[:6] != ["encoding", 0, "parallelImaging", "multiband", "spacing", "dZ"]
    ]

    return xnat_mrd_list


def handle_sequence_params(xnat_mrd_list: list[list[Any]]) -> list[list[Any]]:
    """
    Filter out unwanted sequence parameters from xnat_mrd_list.

    This function removes diffusion parameters entirely and keeps only the first
    entry (index 0) for specific single-value sequence parameters.
    """
    # Remove diffusion parameters entirely
    xnat_mrd_list = [
        elem
        for elem in xnat_mrd_list
        if elem[:2] != ["sequenceParameters", "diffusion"]
    ]

    # Keep only first entry (index 0) for single-value parameters
    single_entries = ["TR", "TE", "flipAngle_deg", "echo_spacing", "TI"]
    for entry in single_entries:
        xnat_mrd_list = [
            elem
            for elem in xnat_mrd_list
            if elem[:2] != ["sequenceParameters", entry] or elem[2] == 0
        ]

    return xnat_mrd_list


def handle_meas_info(xnat_mrd_list: list[list[Any]]) -> list[list[Any]]:
    """
    Filter out unwanted measurement info from xnat_mrd_list.

    This function removes redundant measurement information entries and keeps only the
    first entry (index 0) for parameters that typically have multiple instances but
    where only the first instance is needed.

    """
    xnat_mrd_list = [
        elem
        for elem in xnat_mrd_list
        if elem[:2] != ["measurementInformation", "measurementDependency"]
        or elem[2] == 0
    ]
    xnat_mrd_list = [
        elem
        for elem in xnat_mrd_list
        if elem[:2]
        != [
            "measurementInformation",
            "referencedImageSequence",
            "referencedSOPInstanceUID",
        ]
        or elem[3] == 0
    ]

    return xnat_mrd_list


def create_final_xnat_mrd_dict(
    xnat_mrd_list: list[list[Any]],
    ismrmrd_dict: dict[str, Any],
    xnat_mrd_dict: dict[str, str],
) -> dict[str, Any]:
    """
    Create final xnat_mrd_dict by building parameter paths and extracting values.

    Converts parameter paths to XNAT-compatible key strings and retrieves corresponding
    values from the ismrmrd_dict. Handles XNAT field length limitations.
    """
    for param_path in xnat_mrd_list:
        # Build XNAT key path
        key_parts = ["mrd:mrdScanData"]
        key_parts.extend(str(part) for part in param_path if isinstance(part, str))
        ckey = "/".join(key_parts)

        # This field seems to be too long for xnat
        if "parallelImaging/accelerationFactor/kspace_encoding_step" in ckey:
            ckey = ckey.replace("kspace_encoding_step", "kspace_enc_step")
        xnat_mrd_dict[ckey] = get_dict_values(ismrmrd_dict, param_path)

    return xnat_mrd_dict


def check_header_valid_convert_to_dict(
    xml_schema_filename: Path, ismrmrd_header: bytes
) -> dict[str, Any]:
    """Use xmlschema package to read in xml_schema_filename as xmlschema object and check
    mrd_header is valid before converting the header to a dictionary and returning"""
    xml_schema = xmlschema.XMLSchema(xml_schema_filename)

    if not xml_schema.is_valid(ismrmrd_header):
        raise Exception("Raw data file is not a valid ismrmrd file")

    return xml_schema.to_dict(ismrmrd_header)  # type: ignore


def mrd_2_xnat(mrd_file_path: Path, xml_schema_filepath: Path) -> dict[str, Any]:
    """
    This takes the ismrmrd_header and converts it to a dictionary compatible with XNAT data types.
    The xml_schema_filename points to a local copy of the official MRD header xml schema (.xsd file):
    https://ismrmrd.readthedocs.io/en/latest/mrd_header.html
    """
    with ismrmrd.Dataset(mrd_file_path, "dataset", create_if_needed=False) as dset:
        ismrmrd_header = dset.read_xml_header()

    ismrmrd_dict = check_header_valid_convert_to_dict(
        xml_schema_filepath, ismrmrd_header
    )

    xnat_mrd_list = get_main_parameter_groups(ismrmrd_dict)

    xnat_mrd_list = create_list_param_names(xnat_mrd_list, ismrmrd_dict)

    # Create dictionary with parameter names and their values
    xnat_mrd_dict = {}
    xnat_mrd_dict["scans"] = "mrd:mrdScanData"

    # First deal with special cases
    xnat_mrd_list, xnat_mrd_dict = handle_coil_label(
        xnat_mrd_list, ismrmrd_dict, xnat_mrd_dict
    )

    xnat_mrd_list, xnat_mrd_dict = handle_waveform_info(
        xnat_mrd_list, ismrmrd_dict, xnat_mrd_dict
    )

    xnat_mrd_list = handle_encoding(xnat_mrd_list)
    xnat_mrd_list = handle_sequence_params(xnat_mrd_list)

    xnat_mrd_list = handle_meas_info(xnat_mrd_list)

    return create_final_xnat_mrd_dict(xnat_mrd_list, ismrmrd_dict, xnat_mrd_dict)
