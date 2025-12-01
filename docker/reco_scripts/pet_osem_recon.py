import os
import sys
import sirf.STIR as pPET
from pathlib import Path
from sirf_util import to_dicom_folder


def pet_osem_recon(fpath_input: Path | str, fpath_output: Path | str) -> int:
    """OSEM PET reconstruction using SIRF.

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

    def get_data_file(glob_pattern: str) -> str:
        list_data_files = sorted(fpath_input.glob(glob_pattern))
        if len(list_data_files) == 0:
            print(f"No raw data found in {fpath_input}")
            raise ValueError(
                f"No data file matching {glob_pattern} found in {fpath_input}"
            )
        elif len(list_data_files) > 1:
            print(
                f"Multiple raw data files found in {fpath_input}, only the first one will be processed: {list_data_files[0]}"
            )
        return list_data_files[0].as_posix()

    # listmode data files
    listmode_file = get_data_file("*.l.hdr")
    print("listmode file: ", listmode_file)

    # normalization files
    norm_file = get_data_file("*norm.n.hdr")
    print("norm file: ", norm_file)

    # attenuation files
    attn_file = get_data_file("*umap.v.hdr")
    print("attn file: ", attn_file)

    # output filename prefixes
    sino_file = "sino"

    # redirect STIR messages to some files
    # you can check these if things go wrong
    _ = pPET.MessageRedirector(
        str(fpath_input / "info.txt"), str(fpath_input / "warnings.txt")
    )

    print("message redirected")

    template_acq_data = pPET.AcquisitionData(
        "Siemens_mMR", span=11, max_ring_diff=15, view_mash_factor=2
    )
    template_acq_data.write(str(fpath_input / "template.hs"))

    # create listmode-to-sinograms converter object
    lm2sino = pPET.ListmodeToSinograms()

    # set input, output and template files
    lm2sino.set_input(listmode_file)
    lm2sino.set_output_prefix(sino_file)
    lm2sino.set_template(str(fpath_input / "template.hs"))

    print("template set")

    # set timing interval (in secs) since start of acquisition
    # (the listmode file provided is for 1 hour).
    # you can vary this to see the effect on noise. Increasing it will mean somewhat longer
    # processing time in the following steps (but not in the reconstruction).
    lm2sino.set_time_interval(0, 600)  # 0 - 600 is the first 10 minutes
    # set up the converter
    lm2sino.set_up()
    # create the prompts sinogram
    lm2sino.process()

    print("sinogram finished")

    # get access to the sinograms
    acq_data = lm2sino.get_output()
    # copy the acquisition data into a Python array
    acq_array = acq_data.as_array()[
        0, :, :, :
    ]  # first index is for ToF, which we don't have here
    # how many counts total?
    print("num prompts: %d" % acq_array.sum())
    # print the data sizes.
    print("acquisition data dimensions: %dx%dx%d" % acq_array.shape)

    # create initial image estimate of dimensions and voxel sizes
    # compatible with the scanner geometry (included in the AcquisitionData
    # object acq_data) and initialize each voxel to 1.0
    nxny = (127, 127)
    initial_image = acq_data.create_uniform_image(1.0, nxny)

    # create it from the supplied file
    asm_norm = pPET.AcquisitionSensitivityModel(norm_file)
    asm_norm.set_up(acq_data)
    det_efficiencies = acq_data.get_uniform_copy(1)
    asm_norm.unnormalise(det_efficiencies)

    # read attenuation image
    attn_image = pPET.ImageData(attn_file)

    attn_acq_model = pPET.AcquisitionModelUsingRayTracingMatrix()
    asm_attn = pPET.AcquisitionSensitivityModel(attn_image, attn_acq_model)
    # converting attenuation into attenuation factors (see previous exercise)
    asm_attn.set_up(acq_data)
    attn_factors = acq_data.get_uniform_copy(1)
    print("applying attenuation (please wait, may take a while)...")
    asm_attn.unnormalise(attn_factors)

    # use these in the final attenuation model
    asm_attn = pPET.AcquisitionSensitivityModel(attn_factors)

    randoms = lm2sino.estimate_randoms()

    #  by ray tracing
    acq_model = pPET.AcquisitionModelUsingRayTracingMatrix()
    acq_model.set_num_tangential_LORs(10)

    # now tell the acquisition model more about the geometry of the data it will need to handle
    acq_model.set_up(acq_data, initial_image)

    # define objective function to be maximized as
    # Poisson logarithmic likelihood (with linear model for mean)
    obj_fun = pPET.make_Poisson_loglikelihood(acq_data)
    obj_fun.set_acquisition_model(acq_model)

    # create the reconstruction object
    recon = pPET.OSMAPOSLReconstructor()
    recon.set_objective_function(obj_fun)

    # Choose a number of subsets.
    # For the mMR, best performance requires to not use a multiple of 9 as there are gaps
    # in the sinograms, resulting in unbalanced subsets (which isn't ideal for OSEM).
    num_subsets = 21
    # Feel free to increase these.
    # (Clinical reconstructions use around 60 subiterations, e.g. 21 subsets, 3 full iterations)
    num_subiterations = 12
    recon.set_num_subsets(num_subsets)
    recon.set_num_subiterations(num_subiterations)

    image = initial_image.clone()
    recon.set_up(image)
    # set the initial image estimate
    recon.set_current_estimate(image)

    # update the objective function
    obj_fun.set_acquisition_model(acq_model)
    recon.set_objective_function(obj_fun)

    # chain attenuation and normalisation
    asm = pPET.AcquisitionSensitivityModel(asm_norm, asm_attn)

    # update the acquisition model etc
    acq_model.set_acquisition_sensitivity(asm)
    acq_model.set_background_term(randoms)
    acq_model.set_up(acq_data, initial_image)
    obj_fun.set_acquisition_model(acq_model)
    recon.set_objective_function(obj_fun)

    recon.set_up(initial_image)
    recon.set_current_estimate(initial_image)
    recon.process()
    # show reconstructed image
    image_array = recon.get_output().as_array()

    to_dicom_folder(
        image_array,
        fpath_output,
        filename_prefix=Path(listmode_file).stem.replace(".l", ""),
    )

    return 0


path_in = Path(sys.argv[1])
path_out = Path(sys.argv[2])

if __name__ == "__main__":
    status = pet_osem_recon(path_in, path_out)
    sys.exit(status)
