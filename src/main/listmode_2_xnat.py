from typing import Any
import stir


def listmode_2_xnat(
    listmode_header: stir.ListModeData,
) -> dict[str, Any]:
    """
    This takes the listmode_header and converts it to a dictionary compatible with XNAT data types.
    """
    # Create dictionary with parameter names and their values
    xnat_interfile_dict: dict[str, Any] = {}
    xnat_interfile_dict["scans"] = "interfile:petLmScanData"

    xnat_interfile_dict["interfile:petLmScanData/scannerInformation/name"] = str(
        listmode_header.get_scanner().get_name()
    )

    xnat_interfile_dict[
        "interfile:petLmScanData/radionuclideInformation/radionuclide"
    ] = str(listmode_header.get_exam_info().get_radionuclide().get_name())
    xnat_interfile_dict["interfile:petLmScanData/radionuclideInformation/energy"] = (
        float(listmode_header.get_exam_info().get_radionuclide().get_energy())
    )
    xnat_interfile_dict["interfile:petLmScanData/radionuclideInformation/halfLife"] = (
        float(listmode_header.get_exam_info().get_radionuclide().get_branching_ratio())
    )
    xnat_interfile_dict[
        "interfile:petLmScanData/radionuclideInformation/branchingRatio"
    ] = float(listmode_header.get_exam_info().get_radionuclide().get_branching_ratio())

    xnat_interfile_dict["interfile:petLmScanData/examInformation/lowEnergyThres"] = (
        float(listmode_header.get_exam_info().get_low_energy_thres())
    )
    xnat_interfile_dict["interfile:petLmScanData/examInformation/highEnergyThres"] = (
        float(listmode_header.get_exam_info().get_high_energy_thres())
    )
    pat_pos = str(listmode_header.get_exam_info().patient_position)
    pat_pos = pat_pos.replace("<interfile::PatientPosition::", "").replace(">", "")
    xnat_interfile_dict["interfile:petLmScanData/examInformation/patientPosition"] = (
        pat_pos
    )

    xnat_interfile_dict["interfile:petLmScanData/frameInformation/frameStart"] = float(
        listmode_header.get_exam_info().get_time_frame_definitions().get_start_time()
    )
    xnat_interfile_dict["interfile:petLmScanData/frameInformation/frameEnd"] = float(
        listmode_header.get_exam_info().get_time_frame_definitions().get_end_time()
    )
    frame_dur = float(
        listmode_header.get_exam_info().get_time_frame_definitions().get_end_time()
        - listmode_header.get_exam_info().get_time_frame_definitions().get_start_time()
    )
    xnat_interfile_dict["interfile:petLmScanData/frameInformation/frameDuration"] = (
        frame_dur
    )

    return xnat_interfile_dict
