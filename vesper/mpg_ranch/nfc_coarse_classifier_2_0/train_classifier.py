# The following commented code was an attempt (along with setting the
# PYTHONHASHSEED environment variable to 0 in the PyDev run configuration
# for this script) to make classifier training reproducible, but it didn't
# work.
# 
# import random
# random.seed(1)
#  
# import numpy as np
# np.random.seed(1)
#  
# import tensorflow as tf
# tf.set_random_seed(1)

from pathlib import Path
import os
import sys
import time

from keras.models import Sequential
from keras.layers import Dense
import keras
import matplotlib.pyplot as plt
import numpy as np
import yaml

from vesper.mpg_ranch.nfc_coarse_classifier_2_0.feature_computer import \
    FeatureComputer
from vesper.util.binary_classification_stats import BinaryClassificationStats
from vesper.util.bunch import Bunch
from vesper.util.clips_hdf5_file import ClipsHdf5File
from vesper.util.conditional_printer import ConditionalPrinter
from vesper.util.settings import Settings
import vesper.mpg_ranch.nfc_coarse_classifier_2_0.classifier_utils as \
    classifier_utils
import vesper.util.numpy_utils as numpy_utils


# TODO: Offer reproducible training option.
# TODO: Balance data in training epochs.
# TODO: Try using longer thrush waveforms.
# TODO: Try adding convolutional layers.
# TODO: Try learning a filter bank instead of using a spectrogram.
# TODO: Try lots of random sets of hyperparameter values.
# TODO: Try training several networks and using majority vote of best three.


_CLIPS_FILE_PATH = '/Users/harold/Desktop/2017 {} Clips 22050.h5'

_VERBOSE = True

# Progress notification period for clip reading and spectrogram computation
# when output is verbose, in clips.
_NOTIFICATION_PERIOD = 10000

_SETTINGS = {
     
    'Tseep': Settings(
        
        clip_type='Tseep',
        
        waveform_start_time=.080,
        waveform_duration=.150,
        
        spectrogram_window_size=.005,
        spectrogram_hop_size=.0025,
        spectrogram_start_freq=4000,
        spectrogram_end_freq=10000,
        spectrogram_power_clipping_fraction=.001,
        spectrogram_normalization_enabled=True,
        
        min_recall=.98,
        
        training_set_size=120000,
        validation_set_size=5000,
        test_set_size=5000,
        
        num_epochs=40,
        batch_size=128,
        
        # Sizes in units of the hidden layers of the classification
        # neural network. All of the hidden layers are dense, and all
        # use the RELU activation function. The final layer of the
        # network comprises a single unit with a sigmoid activation
        # function. Setting this to the empty list yields a logistic
        # regression classifier.
        hidden_layer_sizes=[16],
        
        regularization_beta=.002
        
    ),
             
    'Thrush': Settings(
        
        clip_type='Thrush',
        
        waveform_start_time=.150,
        waveform_duration=.175,
        
        spectrogram_window_size=.005,
        spectrogram_hop_size=.0025,
        spectrogram_start_freq=2000,
        spectrogram_end_freq=5000,
        spectrogram_power_clipping_fraction=.001,
        spectrogram_normalization_enabled=True,
        
        min_recall=.97,
        
        training_set_size=None,
        validation_set_size=5000,
        test_set_size=5000,
        
        num_epochs=40,
        batch_size=128,
        
        # Sizes in units of the hidden layers of the classification
        # neural network. All of the hidden layers are dense, and all
        # use the RELU activation function. The final layer of the
        # network comprises a single unit with a sigmoid activation
        # function. Setting this to the empty list yields a logistic
        # regression classifier.
        hidden_layer_sizes=[16],
        
        # Got the following results for training networks of various
        # sizes on 2017-11-15:
        #
        #     [8] 0.07 0.971 0.801
        #     [10] 0.14 0.971 0.865
        #     [12] 0.12 0.970 0.819
        #     [14] 0.08 0.971 0.801
        #     [16] 0.06 0.972 0.805
        #     [18] 0.15 0.970 0.866
        #     [20] 0.09 0.973 0.815
        #     [22] 0.11 0.970 0.849
        #     [24] 0.11 0.972 0.858
        # 
        #     [8] 0.09 0.971 0.833
        #     [10] 0.08 0.972 0.790
        #     [12] 0.11 0.971 0.851
        #     [14] 0.11 0.971 0.841
        #     [16] 0.09 0.972 0.834
        #     [18] 0.16 0.970 0.819
        #     [20] 0.13 0.971 0.852
        #     [22] 0.11 0.971 0.847
        #     [24] 0.12 0.971 0.833
        # 
        #     [8] 0.09 0.970 0.842
        #     [10] 0.09 0.970 0.846
        #     [12] 0.12 0.972 0.838
        #     [14] 0.11 0.971 0.833
        #     [16] 0.10 0.971 0.824
        #     [18] 0.08 0.972 0.837
        #     [20] 0.11 0.970 0.838
        #     [22] 0.08 0.971 0.850
        #     [24] 0.10 0.971 0.823
        
        # hidden_layer_sizes=[
        #    [8], [10], [12], [14], [16], [18], [20], [22], [24]
        # ],
        
        regularization_beta=.002
        
    )
             
             
}


def _main():
    
    _work_around_openmp_issue()

    clip_type = sys.argv[1]
    
    settings = _SETTINGS[clip_type]
    
    clips_file_path = Path(_CLIPS_FILE_PATH.format(clip_type))
    clips = _get_clips(clips_file_path, settings)
    
    if not _VERBOSE:
        print('Computing features...')
    features = _compute_features(clips, settings)
    
    print('Getting targets from classifications...')
    targets = _get_targets(clips)
    
    print('Creating training, validation, and test data sets...')
    train_set, val_set, _ = _create_data_sets(features, targets, settings)
        
#     print('Training classifiers...')
#     _train_classifiers(train_set, val_set, settings)
    
    print('Training classifier...')
    model = _train_classifier(train_set, settings)
    
    print('Testing classifier...')
    train_stats = _test_classifier(model, train_set)
    val_stats = _test_classifier(model, val_set)
    _show_stats(clip_type, train_stats, val_stats)

    print('Saving classifier...')
    _save_classifier(model, settings, val_stats)
       
    print()
        

def _work_around_openmp_issue():

    # Added this 2018-11-26 to work around a problem on macOS involving
    # potential confusion among multiple copies of the OpenMP runtime.
    # The problem only appears to arise when I install TensorFlow using
    # Conda rather than pip. I'm not sure where the multiple copies are
    # coming from. Perhaps Conda and Xcode? See
    # https://github.com/openai/spinningup/issues/16 for an example of
    # another person encountering this issue.
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'


def _get_clips(file_path, settings):
    
    file_ = ClipsHdf5File(file_path)
    
    num_file_clips = file_.get_num_clips()
    
    num_clips = _get_num_read_clips(num_file_clips, settings)
    
    if num_clips != num_file_clips:
        s = '{} of {}'.format(num_clips, num_file_clips)
    else:
        s = '{}'.format(num_clips)
    print('Reading {} clips from file "{}"...'.format(s, file_path))
    
    if _VERBOSE:
        start_time = time.time()
    
    listener = (lambda n: print('    {}'.format(n))) if _VERBOSE else None
    clips = file_.read_clips(num_clips, _NOTIFICATION_PERIOD, listener)
        
    if _VERBOSE:
        
        elapsed_time = time.time() - start_time
        elapsed_time = int(round(10 * elapsed_time)) / 10
        
        if elapsed_time != 0:
            rate = num_clips / elapsed_time
            s = ', an average of {:.1f} clips per second'.format(rate)
        else:
            s = ''
        
        print('Read {} clips in {:.1f} seconds{}.'.format(
            len(clips), elapsed_time, s))
    
        num_calls = len(
            [c for c in clips if c.classification.startswith('Call')])
        num_noises = num_clips - num_calls
        print('Clips include {} calls and {} noises.'.format(
            num_calls, num_noises))
    
    settings.waveform_sample_rate = file_.get_sample_rate()
    
    return clips
        
        
def _get_num_read_clips(num_file_clips, settings):
    
    train_size = settings.training_set_size
    val_size = settings.validation_set_size
    test_size = settings.test_set_size
    
    if train_size is None:
    
        if num_file_clips <= val_size + test_size:
            
            raise ValueError((
                'File contains {} clips, fewer than required '
                'with the specified validation and test set sizes '
                'of {} and {} clips, respectively.').format(
                    num_file_clips, val_size, test_size))
            
        return num_file_clips
            
    else:
        
        num_clips = train_size + val_size + test_size
        
        if num_clips > num_file_clips:
            
            raise ValueError((
                'File contains {} clips, too few for the '
                'specified training, validation, and test set '
                'sizes of {}, {}, and {} clips, respectively.').format(
                    num_file_clips, train_size, val_size, test_size))
            
        return num_clips
    
        
def _compute_features(clips, settings):
    
    vprint = ConditionalPrinter(_VERBOSE)
    
    vprint('Collecting waveforms...')
    waveforms = _collect_waveforms(clips)
    num_waveforms = len(waveforms)
    
    fc = FeatureComputer(settings)
    
    vprint('Trimming waveforms...')
    waveforms = fc.trim_waveforms(waveforms)
    
    def show_clip_count(n):
        vprint('    {}'.format(n))

    vprint('Computing spectrograms...')
    start_time = time.time()
    spectrograms = fc.compute_spectrograms(
        waveforms, _NOTIFICATION_PERIOD, show_clip_count)
    elapsed_time = time.time() - start_time
    spectrogram_rate = num_waveforms / elapsed_time
    spectrum_rate = spectrogram_rate * spectrograms[0].shape[0]
    vprint((
        'Computed {} spectrograms of shape {} in {:.1f} seconds, an '
        'average of {:.1f} spectrograms and {:.1f} spectra per '
        'second.').format(
            num_waveforms, spectrograms[0].shape, elapsed_time,
            spectrogram_rate, spectrum_rate))
    
    vprint('Trimming spectrogram frequencies...')
    vprint('    input shape {}'.format(spectrograms.shape))
    spectrograms = fc.trim_spectrograms(spectrograms)
    vprint('    output shape {}'.format(spectrograms.shape))
    
    fc.configure_spectrogram_power_clipping(spectrograms)
    if settings.spectrogram_min_power is not None:
        vprint('Clipping spectrogram powers to {}...'.format(
            (settings.spectrogram_min_power, settings.spectrogram_max_power)))
        fc.clip_spectrogram_powers(spectrograms)
            
    
    fc.configure_spectrogram_normalization(spectrograms)
    if settings.spectrogram_mean is not None:
        vprint('Normalizing spectrograms with {}...'.format(
            (settings.spectrogram_mean, settings.spectrogram_standard_dev)))
        fc.normalize_spectrograms(spectrograms)
    
    vprint('Flattening spectrograms...')
    features = fc.flatten_spectrograms(spectrograms)
    
    return features

    
def _collect_waveforms(clips):
    num_clips = len(clips)
    num_samples = len(clips[0].waveform)
    waveforms = np.zeros((num_clips, num_samples))
    for i, clip in enumerate(clips):
        waveforms[i] = clip.waveform
    return waveforms
        
        
def _get_targets(clips):
    targets = np.array([_get_target(c) for c in clips])
    targets.shape = (len(targets), 1)
    return targets


def _get_target(clip):
    return 1 if clip.classification.startswith('Call') else 0


def _create_data_sets(features, targets, settings):
    
    num_examples = len(features)
    
    assert(len(targets) == num_examples)
    
    train_size = settings.training_set_size
    val_size = settings.validation_set_size
    test_size = settings.test_set_size

    assert(val_size + test_size < num_examples)
    
    if train_size is None:
        train_size = num_examples - val_size - test_size
        
    assert(train_size + val_size + test_size <= num_examples)
    
    # Shuffle examples.
    permutation = numpy_utils.reproducible_permutation(num_examples)
    features = features[permutation]
    targets = targets[permutation]
    
    test_start = num_examples - test_size
    val_start = test_start - val_size
    
    train_set = Bunch(
        name='training',
        features=features[:val_start],
        targets=targets[:val_start])
    
    val_set = Bunch(
        name='validation',
        features=features[val_start:test_start],
        targets=targets[val_start:test_start])
    
    test_set = Bunch(
        name='test',
        features=features[test_start:],
        targets=targets[test_start:])
    
    return train_set, val_set, test_set


def _train_classifiers(train_set, val_set, settings):
    
    results = []
    
    input_length = train_set.features.shape[1]
    
    for hidden_layer_sizes in settings.hidden_layer_sizes:
        
        print('Training classifier with hidden layer sizes {}...'.format(
            hidden_layer_sizes))
        
        model = _create_classifier_model(
            input_length, hidden_layer_sizes, settings.regularization_beta)
        
        verbose = 2 if _VERBOSE else 0
    
        model.fit(
            train_set.features,
            train_set.targets,
            epochs=settings.num_epochs,
            batch_size=settings.batch_size,
            verbose=verbose)

        stats = _test_classifier(model, val_set)
        i = _find_classification_threshold_index(stats, settings.min_recall)
        results.append(
            (hidden_layer_sizes, stats.threshold[i], stats.recall[i],
             stats.precision[i]))
        
    print(
        'Classifier (hidden layer sizes, threshold, recall, precision) '
        'tuples:')
    for r in results:
        print('    {} {:.2f} {:.3f} {:.3f}'.format(*r))
        

def _create_classifier_model(
        input_length, hidden_layer_sizes, regularization_beta):
    
    layer_sizes = hidden_layer_sizes + [1]
    num_layers = len(layer_sizes)
    
    regularizer = keras.regularizers.l2(regularization_beta)
    
    model = Sequential()
    
    for i in range(num_layers):
        
        kwargs = {
            'activation': 'sigmoid' if i == num_layers - 1 else 'relu',
            'kernel_regularizer': regularizer
        }
        
        if i == 0:
            kwargs['input_dim'] = input_length
            
        model.add(Dense(layer_sizes[i], **kwargs))
        
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy'])
    
    return model
        
    
def _test_classifier(model, data_set, num_thresholds=101):
    
    features = data_set.features
    targets = data_set.targets
    
    values = model.predict(features, batch_size=len(features))
    
    thresholds = np.arange(num_thresholds) / float(num_thresholds - 1)

    return BinaryClassificationStats(targets, values, thresholds)


def _find_classification_threshold_index(stats, min_recall):
    
    recall = stats.recall
    
    i = 0
    while recall[i] >= min_recall:
        i += 1
        
    return i - 1


def _train_classifier(train_set, settings):
    
    input_length = train_set.features.shape[1]
    model = _create_classifier_model(
        input_length,
        settings.hidden_layer_sizes,
        settings.regularization_beta)
    
    verbose = 2 if _VERBOSE else 0

    model.fit(
        train_set.features,
        train_set.targets,
        epochs=settings.num_epochs,
        batch_size=settings.batch_size,
        verbose=verbose)
    
    return model
    
       
def _show_stats(clip_type, train_stats, val_stats):
    
    plt.figure(1)
    plt.plot(
        train_stats.false_positive_rate, train_stats.true_positive_rate, 'b',
        val_stats.false_positive_rate, val_stats.true_positive_rate, 'g')
    plt.xlim((0, 1))
    plt.ylim((0, 1))
    plt.title('{} Classifier ROC'.format(clip_type))
    plt.legend(['Training', 'Validation'])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    
    plt.figure(2)
    plt.plot(
        train_stats.precision, train_stats.recall, 'b',
        val_stats.precision, val_stats.recall, 'g')
    plt.xlim((.9, 1))
    plt.ylim((.8, 1))
    plt.title('{} Classifier Precision vs. Recall'.format(clip_type))
    plt.legend(['Training', 'Validation'])
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    
    plt.show()
    
    _print_stats(clip_type, 'training', train_stats)
    print()
    _print_stats(clip_type, 'validation', val_stats)
        
        
def _print_stats(clip_type, name, stats):
    
    print('{} {} (threshold, recall, precision) triples:'.format(
        clip_type, name))
    
    for t, r, p in zip(stats.threshold, stats.recall, stats.precision):
        print('    {:.2f} {:.3f} {:.3f}'.format(t, r, p))
        
        
def _save_classifier(model, settings, stats):
    
    clip_type = settings.clip_type
    
    path = classifier_utils.get_model_file_path(clip_type)
    path.parent.mkdir(exist_ok=True)
    model.save(path)
    
    settings = _create_classifier_settings(settings, stats)
    text = yaml.dump(settings, default_flow_style=False)
    path = classifier_utils.get_settings_file_path(clip_type)
    path.write_text(text)
    
    
def _create_classifier_settings(s, stats):
    
    return dict(
        
        clip_type=s.clip_type,
        
        waveform_sample_rate=float(s.waveform_sample_rate),
        waveform_start_time=s.waveform_start_time,
        waveform_duration=s.waveform_duration,
        
        spectrogram_window_size=s.spectrogram_window_size,
        spectrogram_hop_size=s.spectrogram_hop_size,
        spectrogram_start_freq=s.spectrogram_start_freq,
        spectrogram_end_freq=s.spectrogram_end_freq,
        spectrogram_min_power=float(s.spectrogram_min_power),
        spectrogram_max_power=float(s.spectrogram_max_power),
        spectrogram_mean=float(s.spectrogram_mean),
        spectrogram_standard_dev=float(s.spectrogram_standard_dev),
        
        classification_threshold=_find_classification_threshold(
            stats, s.min_recall)
        
    )
    
    
def _find_classification_threshold(stats, min_recall):
    i = _find_classification_threshold_index(stats, min_recall)
    return float(stats.threshold[i])


if __name__ == '__main__':
    _main()
