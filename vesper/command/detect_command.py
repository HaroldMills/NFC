"""Module containing class `DetectCommand`."""


from multiprocessing import Process
import itertools

from vesper.command.command import Command, CommandExecutionError
from vesper.django.app.models import Processor, Recording, Station
import vesper.command.command_utils as command_utils
import vesper.command.detector_runner as detector_runner


class DetectCommand(Command):
    
    
    extension_name = 'detect'
    
    
    def __init__(self, args):
        super().__init__(args)
        get = command_utils.get_required_arg
        self._detector_names = get('detectors', args)
        self._station_names = get('stations', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        
        
    def execute(self, context):
        
        self._context = context
        self._logger = self._context.logger

        detectors = self._get_detectors()
        recordings = self._get_recordings()
                
        for recording in recordings:
            
            recording_files = recording.files.all()
            
            if len(recording_files) == 0:
                self._logger.info(
                    'No file information available for {}.'.format(recording))
                
            else:
                num_channels = recording.num_channels
                for file_ in recording_files:
                    for channel_num in range(num_channels):
                        self._logger.info(
                            'Running detectors on {} channel {}...'.format(
                                file_, channel_num))
                        self._run_detectors(detectors, file_, channel_num)
            
        return True
    
    
    def _get_detectors(self):
        
        try:
            return [self._get_detector(name) for name in self._detector_names]
        
        except Exception as e:
            self._logger.error((
                'Collection of detectors to run on recordings on failed with '
                    'an exception.\n'
                'The exception message was:\n'
                '    {}\n'
                'The archive was not modified.\n'
                'See below for exception traceback.').format(str(e)))
            raise
            
            
    def _get_detector(self, name):
        try:
            return Processor.objects.get(name=name)
        except Processor.DoesNotExist:
            raise CommandExecutionError(
                'Unrecognized detector "{}".'.format(name))
            
            
    def _get_recordings(self):
        
        try:
            return itertools.chain.from_iterable(
                self._get_station_recordings(
                    name, self._start_date, self._end_date)
                for name in self._station_names)
            
        except Exception as e:
            self._logger.error((
                'Collection of recordings to run detectors on failed with '
                    'an exception.\n'
                'The exception message was:\n'
                '    {}\n'
                'The archive was not modified.\n'
                'See below for exception traceback.').format(str(e)))
            raise

            
    def _get_station_recordings(self, station_name, start_date, end_date):

        # TODO: Test behavior for an unrecognized station name.
        # I tried this on 2016-08-23 and got results that did not
        # make sense to me. An exception was raised, but it appeared
        # to be  raised from within code that followed the except clause
        # in the `execute` method above (the code logged the sequence of
        # recordings returned by the `_get_recordings` method) rather
        # than from within that clause, and the error message that I
        # expected to be logged by that clause did not appear in the log.
        
        try:
            station = Station.objects.get(name=station_name)
        except Station.DoesNotExist:
            raise CommandExecutionError(
                'Unrecognized station "{}".'.format(station_name))
        
        time_interval = station.get_night_interval_utc(start_date, end_date)
        
        return Recording.objects.filter(
            station_recorder__station=station,
            start_time__range=time_interval)


    def _run_detectors(self, detectors, recording_file, channel_num):
        
        # Copy file channel to monaural file required by Old Bird detectors.
        self._copy_file_channel(recording_file, channel_num)
        
        # Start detector processes.
        processes = [
            self._start_detector_process(d, recording_file, channel_num)
            for d in detectors]
        
        # Wait for processes to complete.
        for process in processes:
            process.join()
            
            
    def _copy_file_channel(self, recording_file, channel_num):
        pass
    
    
    def _start_detector_process(self, detector, recording_file, channel_num):
        
        process = Process(
            target=detector_runner.run_detector,
            args=(detector.id, recording_file.id, channel_num,
                  self._context.logging_info))
        
        process.start()
        
        return process