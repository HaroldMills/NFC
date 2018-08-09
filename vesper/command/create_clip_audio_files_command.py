"""Module containing class `CreateClipAudioFilesCommand`."""


import logging
import os.path
import time

from vesper.command.command import Command
from vesper.singletons import clip_manager
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.os_utils as os_utils
import vesper.util.text_utils as text_utils


_logger = logging.getLogger()


class CreateClipAudioFilesCommand(Command):
    
    
    extension_name = 'create_clip_audio_files'
    
    
    def __init__(self, args):
        super().__init__(args)
        get = command_utils.get_required_arg
        self._detector_names = get('detectors', args)
        self._sm_pair_ui_names = get('station_mics', args)
        self._classification = get('classification', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        
        
    def execute(self, job_info):
        
        self._job_info = job_info

        self._annotation_name, self._annotation_value = \
            model_utils.get_clip_query_annotation_data(
                'Classification', self._classification)

        self._create_clip_audio_files()
        
        return True
    
    
    def _create_clip_audio_files(self):
        
        start_time = time.time()
        
        value_tuples = self._create_clip_query_values_iterator()
        
        total_num_clips = 0
        total_num_created_files = 0
        
        for detector, station, mic_output, date in value_tuples:
            
            clips = model_utils.get_clips(
                station, mic_output, detector, date, self._annotation_name,
                self._annotation_value, order=False)
            
            num_clips = len(clips)
            num_created_files = 0
            
            for clip in clips:
                if self._create_clip_audio_file_if_needed(clip):
                    num_created_files += 1
                
            # Log file creations for this detector/station/mic_output/date.
            count_text = text_utils.create_count_text(num_clips, 'clip')
            _logger.info((
                'Created audio files for {} of {} for detector "{}", '
                'station "{}", mic output "{}", and date {}.').format(
                    num_created_files, count_text, detector.name,
                    station.name, mic_output.name, date))
                
            total_num_clips += num_clips
            total_num_created_files += num_created_files
            
        # Log total file creations and creation rate.
        count_text = text_utils.create_count_text(total_num_clips, 'clip')
        elapsed_time = time.time() - start_time
        timing_text = command_utils.get_timing_text(
            elapsed_time, total_num_clips, 'clips')
        _logger.info(
            'Processed a total of {}{}.'.format(count_text, timing_text))


    def _create_clip_query_values_iterator(self):
        
        try:
            return model_utils.create_clip_query_values_iterator(
                self._detector_names, self._sm_pair_ui_names,
                self._start_date, self._end_date)
            
        except Exception as e:
            command_utils.log_and_reraise_fatal_exception(
                e, 'Clip query values iterator construction',
                'The archive was not modified.')

    
    def _create_clip_audio_file_if_needed(self, clip):
        
        try:
            
            file_path = clip.wav_file_path
            
            if not os.path.exists(file_path):
                
                contents = clip_manager.instance.get_wave_file_contents(clip)
                
                # Create parent directories as needed.
                dir_path = os.path.dirname(file_path)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                    
                os_utils.write_file(file_path, contents, mode='wb')
                
                return True
            
            else:
                return False               
                    
        except Exception as e:
            command_utils.log_and_reraise_fatal_exception(
                e, 'Creation of audio file for clip "{}"'.format(str(clip)))