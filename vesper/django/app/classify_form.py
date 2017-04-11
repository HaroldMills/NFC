from django import forms

import vesper.django.app.model_utils as model_utils


class ClassifyForm(forms.Form):
    

    classifier = forms.ChoiceField(label='Classifier')
    detectors = forms.MultipleChoiceField(label='Detectors')
    station_mics = forms.MultipleChoiceField(label='Station/mics')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate classifiers field.
        classifiers = model_utils.get_processors('Classifier')
        self.fields['classifier'].choices = [(c, c) for c in classifiers]
        
        # Populate detectors field.
        detectors = model_utils.get_processors('Detector')
        self.fields['detectors'].choices = [(d.name, d.name) for d in detectors]
        
        # Populate station/mics field.
        names = model_utils.get_station_mic_output_pair_ui_names()
        choices = [(name, name) for name in names]
        self.fields['station_mics'].choices = choices
