import os
import sys
from pathlib import Path
import sirf.Gadgetron as pMR
from sirf_util import to_dicom_folder


def mr_direct_recon(fpath_input: Path | str, fpath_output: Path | str) -> int:
    """Direct (non-iterative) MR reconstruction using SIRF.

    Parameters
    ----------
        fpath_input
            Folder with raw data files
        fpath_output
            Output folder where reconstructed dicom images will be saved

    Returns
    ----------
        0 if everything went fine, 1 otherwise
    """
    fpath_input = fpath_input if isinstance(fpath_input, Path) else Path(fpath_input)
    fpath_output = (
        fpath_output if isinstance(fpath_output, Path) else Path(fpath_output)
    )

    print(f"Reading from {fpath_input}, writing into {fpath_output}")
    assert os.access(fpath_input, os.R_OK), (
        f"You don't have read permission in {fpath_input}"
    )
    assert os.access(fpath_output, os.W_OK), (
        f"You don't have write permission in {fpath_output}"
    )

    list_rawdata = sorted(fpath_input.glob("*.h5"))
    if len(list_rawdata) == 0:
        print(f"No raw data found in {fpath_input}")
        return 1
    elif len(list_rawdata) > 1:
        print(
            f"Multiple raw data files found in {fpath_input}, only the first one will be processed: {list_rawdata[0]}"
        )

    # Load in the data and preprocess (remove readout oversampling, noise prewhitening...)
    acq_data = pMR.AcquisitionData(str(list_rawdata[0]))
    preprocessed_data = pMR.preprocess_acquisition_data(acq_data)

    # Calculate coil sensitivity maps
    csm = pMR.CoilSensitivityData()
    csm.smoothness = 100
    csm.calculate(preprocessed_data)

    # Create acquisition model
    E = pMR.AcquisitionModel(acqs=preprocessed_data, imgs=csm)
    E.set_coil_sensitivity_maps(csm)
    image_data = E.inverse(preprocessed_data)

    to_dicom_folder(
        image_data.as_array(), fpath_output, filename_prefix=list_rawdata[0].stem
    )

    return 0


path_in = Path(sys.argv[1])
path_out = Path(sys.argv[2])

if __name__ == "__main__":
    status = mr_direct_recon(path_in, path_out)
    sys.exit(status)
