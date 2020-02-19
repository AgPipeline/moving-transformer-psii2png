"""Transforms PSII camera output to PNG file format"""

import datetime
import logging
import os
import numpy as np
from PIL import Image
from matplotlib import pyplot as plt

from terrautils.formats import create_geotiff, create_image
from terrautils.spatial import geojson_to_tuples

import configuration
import transformer_class


class __internal__:
    """Class for internal functions
    """
    def __init__(self):
        """Initializes class instance
        """

    @staticmethod
    def get_image_dimensions(metadata: dict) -> tuple:
        """Returns the image width and height as a tuple
        Arguments:
            metadata: the metadata to reference
        Return:
            Returns a tuple consisting of the image width and height: (width, height)
        """
        if 'sensor_fixed_metadata' in metadata:
            dims = metadata['sensor_fixed_metadata']['camera_resolution']
            return dims.split("x")

        # Default based on original fixed metadata
        return 1936, 1216

    @staticmethod
    def load_image_file(file_path: str) -> np.ndarray:
        """Load an image into a numpy array
        Arguments:
            file_path: the path of the image to load
        """
        image_data = Image.open(file_path)
        return np.array(image_data).astype('uint8')

    @staticmethod
    def analyze(frames: dict, hist_path: str, color_img_path: str):
        """Performs analysis on images
        Arguments:
            frames: the files to load
            hist_path: path to save histogram file
            color_img_path: path to save false color image
        """
        fdark = __internal__.load_image_file(frames[0])
        fmin = __internal__.load_image_file(frames[1])

        # Calculate the maximum fluorescence for each frame
        fave = [np.max(fdark)]
        # Calculate the maximum value for frames 2 through 100. Bin file 101 is an XML file that lists the frame times
        for i in range(2, 101):
            img = __internal__.load_image_file(frames[i])
            fave.append(np.max(img))

        # Assign the first image with the most fluorescence as F-max
        fmax = __internal__.load_image_file(frames[np.where(fave == np.max(fave))[0][0]])
        # Calculate F-variable (F-max - F-min)
        fvar = np.subtract(fmax, fmin)
        # Calculate Fv/Fm (F-variable / F-max)
        try:
            fvfm = np.divide(fvar.astype('float'), fmax.astype('float'))
        except Exception:
            logging.debug("Error calculating fvfm, defaulting to zero")
            fvfm = 0
        # Fv/Fm will generate invalid values, such as division by zero
        # Convert invalid values to zero. Valid values will be between 0 and 1
        fvfm[np.where(np.isnan(fvfm))] = 0
        fvfm[np.where(np.isinf(fvfm))] = 0
        fvfm[np.where(fvfm > 1.0)] = 0

        # Plot Fv/Fm (pseudocolored)
        plt.imshow(fvfm, cmap="viridis")
        plt.savefig(color_img_path)
        plt.show()
        plt.close()

        # Calculate histogram of Fv/Fm values from the whole image
        hist, bins = np.histogram(fvfm, bins=20)
        # Plot Fv/Fm histogram
        width = 0.7 * (bins[1] - bins[0])
        center = (bins[:-1] + bins[1:]) / 2
        plt.bar(center, hist, align='center', width=width)
        plt.xlabel("Fv/Fm")
        plt.ylabel("Pixels")
        plt.show()
        plt.savefig(hist_path)
        plt.close()


def check_continue(transformer: transformer_class.Transformer, check_md: dict, transformer_md: list, full_md: list) -> tuple:
    """Checks if conditions are right for continuing processing
    Arguments:
        transformer: instance of transformer class
        check_md: request specific metadata
        transformer_md: metadata associated with previous runs of the transformer
        full_md: the full set of metadata available to the transformer
    Return:
        Returns a tuple containing the return code for continuing or not, and
        an error message if there's an error
    """
    # pylint: disable=unused-argument
    # Make sure we have all the files we need
    file_list = check_md['list_files']()

    # Generate a list of image file names to check
    file_endings = ["{0:0>4}.bin".format(i) for i in range(0, 102)]

    # Build a list of file endings to match
    source_endings = []
    for one_file in file_list:
        source_endings.append(one_file[-8:])

    # Check if the intersection is an empty set
    any_missing = set(file_endings).intersection(set(source_endings))

    if any_missing:
        return -1, "Not all the necessary sensor files were found"

    return tuple([0])


def perform_process(transformer: transformer_class.Transformer, check_md: dict, transformer_md: list, full_md: list) -> dict:
    """Performs the processing of the data
    Arguments:
        transformer: instance of transformer class
    Return:
        Returns a dictionary with the results of processing
    """
    # pylint: disable=unused-argument
    result = {}
    file_md = []
    start_timestamp = datetime.datetime.utcnow()

    file_list = check_md['list_files']()
    files_count = len(file_list)

    # Find the metadata we're interested in for calibration parameters
    terra_md = None
    for one_md in full_md:
        if 'terraref_cleaned_metadata' in one_md:
            terra_md = one_md
            break
    if not terra_md:
        raise RuntimeError("Unable to find TERRA REF specific metadata")

    transformer_md = transformer.generate_transformer_md()

    # Generate a list of approved file name endings
    file_endings = ["{0:0>4}.bin".format(i) for i in range(0, 102)]

    files_processed = 0
    try:
        img_width, img_height = __internal__.get_image_dimensions(terra_md)
        gps_bounds = geojson_to_tuples(terra_md['spatial_metadata']['ps2Top']['bounding_box'])

        png_frames = {}
        for one_file in file_list:
            if one_file[-8:] in file_endings:
                files_processed += 1

                raw_data = np.fromfile(one_file, np.dtype('<u2')).reshape([img_width, img_height]).astype('float')

                png_filename = os.path.join(check_md['working_folder'], os.path.basename(one_file.replace('.bin', '.png')))
                logging.info("Creating: '%s'", png_filename)
                create_image(raw_data, png_filename, transformer.args.scale_values)
                cur_md = {'path': png_filename,
                          'key': configuration.TRANSFORMER_SENSOR,
                          'metadata': {
                              'data': {
                                  'data': transformer_md
                              }
                          }}
                file_md.append(cur_md)
                png_frames[int(one_file[-8:-4])] = png_filename

                tif_filename = os.path.join(check_md['working_folder'], os.path.basename(one_file.replace('.bin', '.tif')))
                logging.info("Creating: '%s'", tif_filename)
                create_geotiff(raw_data, gps_bounds, tif_filename, None, False, transformer_md, terra_md)
                cur_md = {'path': tif_filename,
                          'key': configuration.TRANSFORMER_SENSOR,
                          'metadata': {
                              'data': transformer_md
                          }}
                file_md.append(cur_md)

        logging.info("Generating aggregates")
        hist_path = os.path.join(check_md['working_folder'], 'combined_hist.png')
        false_color_path = os.path.join(check_md['working_folder'], 'combined_pseudocolored.png')
        __internal__.analyze(png_frames, hist_path, false_color_path)
        cur_md = {'path': hist_path,
                  'key': configuration.TRANSFORMER_SENSOR,
                  'metadata': {
                      'data': transformer_md
                  }}
        file_md.append(cur_md)
        cur_md = {'path': false_color_path,
                  'key': configuration.TRANSFORMER_SENSOR,
                  'metadata': {
                      'data': transformer_md
                  }}
        file_md.append(cur_md)

        result['code'] = 0
        result['file'] = file_md
        result[configuration.TRANSFORMER_NAME] = {
            'version': configuration.TRANSFORMER_VERSION,
            'utc_timestamp': datetime.datetime.utcnow().isoformat(),
            'processing_time': str(datetime.datetime.now() - start_timestamp),
            'num_files_received': str(files_count),
            'files_processed': str(files_processed)
        }

    except Exception as ex:
        msg = 'Exception caught converting PSII files'
        logging.exception(msg)
        result['code'] = -1
        result['error'] = msg + ': ' + str(ex)

    return result
