"""
Form with fields for specifying a set of clips.

The clips are specified as a set of detectors, a set of station/mic pairs,
a classification, and a range of dates.

This form can be used by a Django view either as is, or with additional
fields specified in a subclass.
"""


from django import forms

import vesper.django.app.form_utils as form_utils
import vesper.django.app.model_utils as model_utils


class ClipSetForm(forms.Form):
    

    detectors = forms.MultipleChoiceField(label='Detectors')
    station_mics = forms.MultipleChoiceField(label='Station/mics')
    classification = forms.ChoiceField(label='Classification')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate detectors field.
        self.fields['detectors'].choices = \
            form_utils.get_processor_choices('Detector')
        
        # Populate station/mics field.
        names = model_utils.get_station_mic_output_pair_ui_names()
        choices = [(name, name) for name in names]
        self.fields['station_mics'].choices = choices
        
        # Populate classification field.
        self.fields['classification'].choices = \
            form_utils.get_string_annotation_value_choices('Classification')