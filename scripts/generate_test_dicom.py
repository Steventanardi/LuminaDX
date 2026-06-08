"""Generate a synthetic liver CT DICOM series for testing."""
import os
import datetime
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid
from pathlib import Path

OUTPUT_DIR = Path(r"D:\Steven Project\Liver Cancer\Datasets\sample_ct\series_arterial")
NUM_SLICES = 30
ROWS, COLS = 512, 512

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

study_uid = generate_uid()
series_uid = generate_uid()
frame_of_ref_uid = generate_uid()

def make_liver_slice(z_idx: int, num_slices: int) -> np.ndarray:
    """Create a fake CT slice with liver-like HU values."""
    arr = np.full((ROWS, COLS), -1000, dtype=np.int16)  # air background

    # Body oval
    cx, cy = COLS // 2, ROWS // 2
    ry, rx = 180, 220
    Y, X = np.ogrid[:ROWS, :COLS]
    body_mask = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 <= 1
    arr[body_mask] = 50  # soft tissue ~50 HU

    # Liver (right lobe, HU 50-70)
    fraction = z_idx / num_slices
    if 0.2 < fraction < 0.85:
        lx, ly = cx + 60, cy - 10
        lrx = int(120 * min(1, (fraction - 0.2) / 0.3 if fraction < 0.5 else (0.85 - fraction) / 0.35))
        lry = int(80 * min(1, (fraction - 0.2) / 0.3 if fraction < 0.5 else (0.85 - fraction) / 0.35))
        if lrx > 5 and lry > 5:
            liver_mask = body_mask & (((X - lx) / lrx) ** 2 + ((Y - ly) / lry) ** 2 <= 1)
            arr[liver_mask] = 60

            # Lesion (hypervascular, +30 HU on arterial)
            if 0.35 < fraction < 0.65:
                tx, ty = lx - 20, ly + 10
                tumor_mask = liver_mask & (((X - tx) / 18) ** 2 + ((Y - ty) / 15) ** 2 <= 1)
                arr[tumor_mask] = 90  # arterial hyperenhancement

    # Spine
    spine_mask = body_mask & (((X - cx) / 18) ** 2 + ((Y - (cy + 60)) / 22) ** 2 <= 1)
    arr[spine_mask] = 700

    return arr


for i in range(NUM_SLICES):
    ds = FileDataset(None, {}, is_implicit_VR=False, is_little_endian=True)

    ds.file_meta = Dataset()
    ds.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT Image Storage
    ds.file_meta.MediaStorageSOPInstanceUID = generate_uid()
    ds.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    ds.is_implicit_VR = False
    ds.is_little_endian = True

    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid
    ds.FrameOfReferenceUID = frame_of_ref_uid

    ds.PatientName = "ANON_TEST"
    ds.PatientID = "TEST001"
    ds.PatientBirthDate = "19700101"
    ds.PatientSex = "M"

    ds.Modality = "CT"
    ds.SeriesDescription = "Arterial Phase"
    ds.StudyDescription = "Liver CT Triphasic"
    ds.StudyDate = datetime.date.today().strftime("%Y%m%d")
    ds.StudyTime = "120000"
    ds.SeriesNumber = 1
    ds.InstanceNumber = i + 1
    ds.AcquisitionNumber = 1

    ds.Rows = ROWS
    ds.Columns = COLS
    ds.PixelSpacing = [0.7, 0.7]
    ds.SliceThickness = 3.0
    ds.ImagePositionPatient = [0.0, 0.0, float(i * 3)]
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.SliceLocation = float(i * 3)
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1  # signed
    ds.RescaleIntercept = -1024.0
    ds.RescaleSlope = 1.0
    ds.WindowCenter = 50
    ds.WindowWidth = 400
    ds.KVP = 120
    ds.XRayTubeCurrent = 200

    pixel_array = make_liver_slice(i, NUM_SLICES)
    ds.PixelData = pixel_array.tobytes()

    out_path = OUTPUT_DIR / f"CT_{i+1:04d}.dcm"
    pydicom.dcmwrite(str(out_path), ds, write_like_original=False)

print(f"Generated {NUM_SLICES} DICOM slices in {OUTPUT_DIR}")
