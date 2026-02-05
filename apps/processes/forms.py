from django import forms
from .models import Process, validate_cnj

class ProcessForm(forms.ModelForm):
    number = forms.CharField(
        max_length=40,
        label="Número CNJ",
        help_text="Formato: NNNNNNN-DD.AAAA.J.TR.OOOO (Ex: 0000000-00.2024.8.26.0100)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0000000-00.0000.0.00.0000',
            'pattern': r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}',
        })
    )
    
    court = forms.CharField(
        max_length=255,
        required=False,
        label="Tribunal",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: TJSP, TRT-2, STJ'
        })
    )
    
    subject = forms.CharField(
        max_length=255,
        required=False,
        label="Assunto",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Breve descrição do assunto'
        })
    )
    
    phase = forms.ChoiceField(
        choices=[
            ('initial', 'Inicial'),
            ('instruction', 'Instrução'),
            ('sentence', 'Sentença'),
            ('appeal', 'Recurso'),
            ('execution', 'Execução'),
            ('archived', 'Arquivado'),
        ],
        initial='initial',
        label="Fase",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[
            ('active', 'Ativo'),
            ('suspended', 'Suspenso'),
            ('finished', 'Finalizado'),
        ],
        initial='active',
        label="Status",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Process
        fields = ['number', 'court', 'subject', 'phase', 'status']
    
    def clean_number(self):
        """Valida número CNJ"""
        number = self.cleaned_data.get('number', '').strip()
        
        if number:
            # Chama o validador
            validate_cnj(number)
        
        return number