"""Module containing class `Annotator`."""


import vesper.django.app.model_utils as model_utils


class Annotator:
    
    """Superclass of annotators, for example including classifiers."""
    
    
    def __init__(
            self, annotation_info, creating_user=None, creating_job=None,
            creating_processor=None):
        
        self._annotation_info = annotation_info
        self._creating_user = creating_user
        self._creating_job = creating_job
        self._creating_processor = creating_processor
        
        
    def _annotate(self, clip, annotation_value):
        
        model_utils.annotate_clip(
            clip, self._annotation_info, annotation_value,
            creating_user=self._creating_user,
            creating_job=self._creating_job,
            creating_processor=self._creating_processor)
    