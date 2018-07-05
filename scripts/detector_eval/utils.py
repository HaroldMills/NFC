"""
Utility constants and functions for detector evaluation.

Edit the RECORDINGS_DIR_PATH, ANNOTATIONS_DIR_PATH, and WORKING_DIR_PATH
constants below to set the input and output directories for the
run_detectors and evaluate_detectors scripts.

Edit NUM_DETECTION_THRESHOLDS to adjust the number of detection
thresholds for which the detectors are run. Reducing the number of
thresholds speeds up detector runs considerably during testing.
"""


from pathlib import Path

import numpy as np


RECORDINGS_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/BirdVox/BirdVox-full-night/Other/'
    'Recording Wave Files')

ANNOTATIONS_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/BirdVox/BirdVox-full-night/Dataset')

WORKING_DIR_PATH = Path('/Users/harold/Desktop')

RECORDING_FILE_NAME_FORMAT = 'BirdVox-full-night_wav-audio_unit{:02}.wav'

ANNOTATIONS_FILE_NAME_FORMAT = \
    'BirdVox-full-night_csv-annotations_unit{:02}.csv'

CLIPS_FILE_NAME = 'Clips.csv'

PRECISION_VS_RECALL_PLOT_FILE_NAME = \
    'Detector Precision vs. Recall.pdf'

UNIT_NUMS = (1, 2, 3, 5, 7, 10)

# Constants determining the thresholds for which detectors are run.
# The Old Bird Tseep and Thrush thresholds (2 and 1.3, respectively)
# are added to those generated from these constants.
MIN_DETECTION_THRESHOLD = 1.2
MAX_DETECTION_THRESHOLD = 20
DETECTION_THRESHOLDS_POWER = 3
NUM_DETECTION_THRESHOLDS = 10

# Center frequency threshold separating tseep and thrush calls, in hertz.
FREQ_THRESHOLD = 5000

# Recording sample rate, in hertz.
SAMPLE_RATE = 24000


def seconds_to_samples(x):
    return int(round(x * SAMPLE_RATE))


def get_recording_file_path(unit_num):
    file_name = RECORDING_FILE_NAME_FORMAT.format(unit_num)
    return RECORDINGS_DIR_PATH / file_name


def get_annotations_file_path(unit_num):
    file_name = ANNOTATIONS_FILE_NAME_FORMAT.format(unit_num)
    return ANNOTATIONS_DIR_PATH / file_name


def get_clips_file_path():
    return WORKING_DIR_PATH / CLIPS_FILE_NAME


def get_precision_vs_recall_plot_file_path():
    return WORKING_DIR_PATH / PRECISION_VS_RECALL_PLOT_FILE_NAME


def get_detection_thresholds():

    min_t = MIN_DETECTION_THRESHOLD
    max_t = MAX_DETECTION_THRESHOLD
    n = NUM_DETECTION_THRESHOLDS
    y = (np.arange(n) / (n - 1)) ** DETECTION_THRESHOLDS_POWER
    t = min_t + (max_t - min_t) * y
    t = list(t)
    
    # Always include Old Bird Tseep and Thrush thresholds.
    t.append(1.3)   # Thrush
    t.append(2)     # Tseep
    
    t.sort()
    
    return t
