from django import forms
from .models import Process, validate_cnj


class ProcessForm(forms.ModelForm):

    class Meta:
        model = Process
        fields = [
            'number', 'court', 'subject', 'phase', 'status', 'area',
            'description', 'cause_value', 'filing_date', 'distribution_date',
            'first_hearing_date', 'sentence_date', 'court_unit', 'judge_name',
            'risk', 'success_probability', 'tags', 'internal_notes',
            'next_action', 'last_movement', 'last_movement_date', 'responsible',
        ]
        widgets = {
            'number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0000000-00.0000.0.00.0000',
            }),
            'court': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: TJSP, TRT-2, STJ'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Breve descrição'}),
            'phase': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'area': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'cause_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0,00'}),
            'filing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'distribution_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'first_hearing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sentence_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'court_unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 3ª Vara Cível'}),
            'judge_name': forms.TextInput(attrs={'class': 'form-control'}),
            'risk': forms.Select(attrs={'class': 'form-control'}),
            'success_probability': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'urgente, trabalhista, vip'}),
            'internal_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'next_action': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Próxima movimentação esperada'}),
            'last_movement': forms.TextInput(attrs={'class': 'form-control'}),
            'last_movement_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'responsible': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_number(self):
        number = self.cleaned_data.get('number', '').strip()
        if number:
            validate_cnj(number)
        return number

    def clean_success_probability(self):
        val = self.cleaned_data.get('success_probability')
        if val is not None and (val < 0 or val > 100):
            raise forms.ValidationError("Deve ser entre 0 e 100.")
        return val
