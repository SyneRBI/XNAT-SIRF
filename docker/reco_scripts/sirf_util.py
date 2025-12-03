import numpy as np
from pathlib import Path
import pydicom
from pydicom.pixels import set_pixel_data
import datetime


def to_dicom_folder(
    data: np.ndarray,
    foldername: str | Path,
    filename_prefix: str = "sirf",
    series_uid: str | None = None,
    series_description: str | None = None,
    resolution: float = 1.0,
) -> None:
    """Write image data to DICOM files in a folder.

    The data is always saved in a multi-frame DICOM files.

    Parameters
    ----------
    foldername
        Path to folder for DICOM files.
    filename_prefix
        Prefix for DICOM filenames.
    series_uid
        Series Instance UID to be used in the DICOM files. If None, a new UID will be generated.
    series_description
        String to be saved as the series description in the DICOM files.
    resolution
        Spacing between slices in mm.
    """
    print(
        f"Writing dicome files with prefix {filename_prefix} into folder {foldername} "
    )
    if not isinstance(foldername, Path):
        foldername = Path(foldername)
    foldername.mkdir(parents=True, exist_ok=True)

    acquisition_type = "2D"
    frame_dimension = next(
        (i for i in range(-3, -len(data.shape) - 1, -1) if data.shape[i] > 1), -3
    )
    number_of_frames = data.shape[frame_dimension]
    dcm_idata = data.swapaxes(frame_dimension, -3)

    # Metadata
    file_meta = pydicom.dataset.FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.MRImageStorage
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian

    # Dataset
    dataset = pydicom.Dataset()
    dataset.file_meta = file_meta

    dataset.PatientName = "Unknown"
    dataset.PatientID = "Unknown"
    dataset.PatientSex = "O"

    timestamp = datetime.datetime.now(datetime.timezone.utc)
    dataset.SeriesDate = timestamp.strftime("%Y%m%d")
    dataset.SeriesTime = timestamp.strftime("%H%M%S.%f")
    if series_description:
        dataset.SeriesDescription = series_description
        dataset.ProtocolName = series_description
    dataset.SeriesInstanceUID = series_uid if series_uid else pydicom.uid.generate_uid()

    dataset.PatientPosition = "HFS"

    for file_index, other in enumerate(np.ndindex(dcm_idata.shape[:-3])):
        dcm_file_idata = dcm_idata[(*other, slice(None), slice(None), slice(None))]

        dataset.MRAcquisitionType = acquisition_type
        dataset.PerFrameFunctionalGroupsSequence = pydicom.Sequence()

        # (frames, rows, columns) for multi-frame grayscale data
        pixel_data = np.abs(dcm_file_idata)
        pixel_data = pixel_data / pixel_data.max() * (2**16 - 1)
        pixel_data = np.swapaxes(pixel_data, -1, -2)

        for frame in range(number_of_frames):
            image_position_patient = (
                np.asarray([0, 0, 0]) + np.asarray([1, 0, 0]) * resolution * file_index
            )
            dataset.ImagePositionPatient = image_position_patient.tolist()

            # 'MONOCHROME2' means smallest value is black, largest value is white
            set_pixel_data(
                ds=dataset,
                arr=pixel_data[frame, ...].astype(np.uint16),
                photometric_interpretation="MONOCHROME2",
                bits_stored=16,
            )
            dataset.save_as(
                foldername
                / f"{filename_prefix}_{str(np.prod(file_index) * number_of_frames + frame).zfill(4)}.dcm",
                enforce_file_format=True,
            )
