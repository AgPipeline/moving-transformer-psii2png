import logging
import os
import json
import numpy as np

from terrautils.spatial import scanalyzer_to_utm, geojson_to_tuples
from terrautils.formats import create_geotiff
import configuration
try:
    import transformer_class
except ImportError:
    pass


class calibParam:
    def __init__(self):
        self.calibrated = True
        self.calibrationR = 0.0
        self.calibrationB = 0.0
        self.calibrationF = 0.0
        self.calibrationJ1 = 0.0
        self.calibrationJ0 = 0.0
        self.calibrationa1 = 0.0
        self.calibrationa2 = 0.0
        self.calibrationX = 0.0
        self.calibrationb1 = 0.0
        self.calibrationb2 = 0.0


def get_calibrate_param(metadata):
    calibparameter = calibParam()

    try:
        if 'terraref_cleaned_metadata' in metadata:
            fixedmd = metadata['sensor_fixed_metadata']
            if fixedmd['is_calibrated'] == 'True':
                return calibparameter
            else:
                calibparameter.calibrated = False
                calibparameter.calibrationR = float(fixedmd['calibration_R'])
                calibparameter.calibrationB = float(fixedmd['calibration_B'])
                calibparameter.calibrationF = float(fixedmd['calibration_F'])
                calibparameter.calibrationJ1 = float(fixedmd['calibration_J1'])
                calibparameter.calibrationJ0 = float(fixedmd['calibration_J0'])
                calibparameter.calibrationa1 = float(fixedmd['calibration_alpha1'])
                calibparameter.calibrationa2 = float(fixedmd['calibration_alpha2'])
                calibparameter.calibrationX = float(fixedmd['calibration_X'])
                calibparameter.calibrationb1 = float(fixedmd['calibration_beta1'])
                calibparameter.calibrationb2 = float(fixedmd['calibration_beta2'])
                return calibparameter

    except KeyError as err:
        return calibparameter


# convert flir raw data into temperature C degree, for date after September 15th
def flirRawToTemperature(rawData, calibP):

    R = calibP.calibrationR
    B = calibP.calibrationB
    F = calibP.calibrationF
    J0 = calibP.calibrationJ0
    J1 = calibP.calibrationJ1

    X = calibP.calibrationX
    a1 = calibP.calibrationa1
    b1 = calibP.calibrationb1
    a2 = calibP.calibrationa2
    b2 = calibP.calibrationb2

    H2O_K1 = 1.56
    H2O_K2 = 0.0694
    H2O_K3 = -0.000278
    H2O_K4 = 0.000000685

    H = 0.1
    T = 22.0
    D = 2.5
    E = 0.98

    K0 = 273.15

    im = rawData

    AmbTemp = T + K0
    AtmTemp = T + K0

    H2OInGperM2 = H*math.exp(H2O_K1 + H2O_K2*T + H2O_K3*math.pow(T, 2) + H2O_K4*math.pow(T, 3))
    a1b1sqH2O = (a1+b1*math.sqrt(H2OInGperM2))
    a2b2sqH2O = (a2+b2*math.sqrt(H2OInGperM2))
    exp1 = math.exp(-math.sqrt(D/2)*a1b1sqH2O)
    exp2 = math.exp(-math.sqrt(D/2)*a2b2sqH2O)

    tao = X*exp1 + (1-X)*exp2

    obj_rad = im*E*tao

    theo_atm_rad = (R*J1/(math.exp(B/AtmTemp)-F)) + J0
    atm_rad = repmat((1-tao)*theo_atm_rad, 640, 480)

    theo_amb_refl_rad = (R*J1/(math.exp(B/AmbTemp)-F)) + J0
    amb_refl_rad = repmat((1-E)*tao*theo_amb_refl_rad, 640, 480)

    corr_pxl_val = obj_rad + atm_rad + amb_refl_rad

    pxl_temp = B/np.log(R/(corr_pxl_val-J0)*J1+F)

    return pxl_temp


def rawData_to_temperature(rawData, metadata):
    try:
        calibP = get_calibrate_param(metadata)
        tc = np.zeros((640, 480))

        if calibP.calibrated:
            tc = rawData/10
        else:
            tc = flirRawToTemperature(rawData, calibP)

        return tc
    except Exception as ex:
        fail('raw to temperature fail:' + str(ex))


def flir2tif(input_paths, full_md = None):
    # Determine metadata and BIN file
    bin_file = None
    for f in input_paths:
        if f.endswith(".bin"):
            bin_file = f
        if f.endswith("_cleaned.json") and full_md is None:
            with open(f, 'r') as mdf:
                full_md = json.load(mdf)['content']

    # TODO: Figure out how to pass extractor details to create_geotiff in both types of pipelines
    extractor_info = None

    if full_md:
        if bin_file is not None:
            out_file = bin_file.replace(".bin", ".tif")
            gps_bounds_bin = geojson_to_tuples(full_md['spatial_metadata']['flirIrCamera']['bounding_box'])
            raw_data = np.fromfile(bin_file, np.dtype('<u2')).reshape([480, 640]).astype('float')
            raw_data = np.rot90(raw_data, 3)
            tc = rawData_to_temperature(raw_data, full_md)
            create_geotiff(tc, gps_bounds_bin, out_file, None, False, extractor_info, full_md, compress=True)

    # Return formatted dict for simple extractor
    return {
        "metadata": {
            "files_created": [out_file]
        },
        "outputs": [out_file]
    }


def check_continue(transformer, check_md: dict, transformer_md: dict, full_md: dict, **kwargs) -> dict:
    """Checks if conditions are right for continuing processing
    Arguments:
        transformer: instance of transformer class
    Return:
        Returns a dictionary containining the return code for continuing or not, and
        an error message if there's an error
    """
    print("check_continue(): received arguments: %s" % str(kwargs))
    return (0)


def perform_process(transformer, check_md: dict, transformer_md: dict, full_md: dict) -> dict:
    """Performs the processing of the data
    Arguments:
        transformer: instance of transformer class
    Return:
        Returns a dictionary with the results of processing
    """
    result = {}
    file_md = []

    file_list = os.listdir(check_md['working_folder'])

    try:
        bin_files = []
        for one_file in file_list:
            if one_file.endswith(".bin"):
                bin_files.append(os.path.join(check_md['working_folder'], one_file))
        if len(bin_files) > 0:
            output = flir2tif(bin_files, full_md)
            file_md.append({
                'path': output['output'],
                'key': configuration.TRANSFORMER_SENSOR,
                'metadata': {
                    'data': transformer_md
                }
            })
        result['code'] = 0
        result['file'] = file_md

    except Exception as ex:
        result['code'] = -1
        result['error'] = "Exception caught converting PLY files: %s" % str(ex)

    return result
