from django import forms

from .models import ContaBancaria, Transacao, AnexoTransacao

# Shared widget classes — mobile-first with a 48px minimum tap target.
FIELD = (
    'w-full min-h-[48px] rounded-lg border-gray-300 bg-white px-3 py-2 '
    'text-base sm:text-sm shadow-sm transition '
    'focus:border-indigo-500 focus:ring-indigo-500 focus:outline-none'
)
CHECKBOX = 'h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'


class ContaBancariaForm(forms.ModelForm):
    class Meta:
        model = ContaBancaria
        fields = ['nome', 'tipo', 'saldo_inicial', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': FIELD,
                'placeholder': 'Ex: Banco do Brasil - Conta Corrente',
            }),
            'tipo': forms.Select(attrs={'class': FIELD}),
            'saldo_inicial': forms.NumberInput(attrs={
                'class': FIELD,
                'step': '0.01',
                'inputmode': 'decimal',
            }),
            'ativa': forms.CheckboxInput(attrs={'class': CHECKBOX}),
        }


class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = ['data', 'tipo', 'categoria', 'valor', 'conta_origem', 'conta_destino',
                  'pago_pelo_curador', 'favorecido_nome', 'favorecido_cpf_cnpj', 'descricao']
        widgets = {
            'data': forms.DateInput(attrs={
                'type': 'date',
                'class': FIELD,
            }),
            'tipo': forms.Select(attrs={'class': FIELD}),
            'categoria': forms.Select(attrs={'class': FIELD}),
            'valor': forms.NumberInput(attrs={
                'class': FIELD,
                'step': '0.01',
                'inputmode': 'decimal',
            }),
            'conta_origem': forms.Select(attrs={'class': FIELD}),
            'conta_destino': forms.Select(attrs={'class': FIELD}),
            'pago_pelo_curador': forms.CheckboxInput(attrs={'class': CHECKBOX}),
            'favorecido_nome': forms.TextInput(attrs={'class': FIELD}),
            'favorecido_cpf_cnpj': forms.TextInput(attrs={
                'class': FIELD,
                'inputmode': 'numeric',
            }),
            'descricao': forms.Textarea(attrs={
                'class': FIELD + ' min-h-[96px]',
                'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active accounts can receive transactions.
        self.fields['conta_origem'].queryset = ContaBancaria.objects.filter(ativa=True)
        self.fields['conta_destino'].queryset = ContaBancaria.objects.filter(ativa=True)


class ReceiptSignatureForm(forms.Form):
    """Touch-enabled signature receipt form for service providers."""
    data = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': FIELD,
        })
    )
    categoria = forms.ChoiceField(
        choices=Transacao.CATEGORIA_CHOICES,
        widget=forms.Select(attrs={'class': FIELD}),
    )
    favorecido_nome = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': FIELD,
            'placeholder': 'Nome do prestador de serviço',
        }),
    )
    favorecido_cpf_cnpj = forms.CharField(
        max_length=18,
        widget=forms.TextInput(attrs={
            'class': FIELD,
            'placeholder': '000.000.000-00',
            'inputmode': 'numeric',
        }),
    )
    descricao = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': FIELD + ' min-h-[96px]',
            'rows': 3,
            'placeholder': 'Descrição do serviço prestado',
        }),
    )
    valor = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': FIELD,
            'step': '0.01',
            'inputmode': 'decimal',
            'placeholder': '0,00',
        }),
    )
    conta_origem = forms.ModelChoiceField(
        queryset=ContaBancaria.objects.filter(tipo='BANCO', ativa=True),
        widget=forms.Select(attrs={'class': FIELD}),
    )
    comprovante_pix = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-base sm:text-sm text-slate-600 file:mr-3 file:min-h-[48px] file:rounded-lg file:border-0 file:bg-indigo-50 file:px-4 file:font-medium file:text-indigo-700 hover:file:bg-indigo-100',
        }),
    )


class ExpenseDeliveryForm(forms.Form):
    """Expense & delivery entry with mandatory double-attachment for market/delivery."""
    data = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': FIELD,
        })
    )
    categoria = forms.ChoiceField(
        choices=Transacao.CATEGORIA_CHOICES,
        widget=forms.Select(attrs={'class': FIELD}),
    )
    favorecido_nome = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': FIELD,
            'placeholder': 'Ex: iFood, Keeta, Farmácia São Paulo',
        }),
    )
    descricao = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': FIELD + ' min-h-[80px]',
            'rows': 2,
            'placeholder': 'Itens ou detalhes do pedido',
        }),
    )
    valor = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': FIELD,
            'step': '0.01',
            'inputmode': 'decimal',
            'placeholder': '0,00',
        }),
    )
    fonte_recursos = forms.ChoiceField(
        choices=[
            ('BANCO', 'Conta Bancária do Curatelado'),
            ('CURADOR', 'Recursos Próprios do Curador (Fora do Caixa)'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'h-5 w-5 border-gray-300 text-indigo-600 focus:ring-indigo-500',
        }),
    )
    conta_origem = forms.ModelChoiceField(
        queryset=ContaBancaria.objects.filter(tipo='BANCO', ativa=True),
        required=False,
        widget=forms.Select(attrs={'class': FIELD}),
    )
    comprovante_pagamento = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-base sm:text-sm text-slate-600 file:mr-3 file:min-h-[48px] file:rounded-lg file:border-0 file:bg-indigo-50 file:px-4 file:font-medium file:text-indigo-700 hover:file:bg-indigo-100',
        }),
    )
    cupom_itemizado = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-base sm:text-sm text-slate-600 file:mr-3 file:min-h-[48px] file:rounded-lg file:border-0 file:bg-amber-50 file:px-4 file:font-medium file:text-amber-700 hover:file:bg-amber-100',
        }),
    )


class AnexoTransacaoForm(forms.ModelForm):
    class Meta:
        model = AnexoTransacao
        fields = ['tipo_documento', 'arquivo', 'descricao']
        widgets = {
            'tipo_documento': forms.Select(attrs={'class': FIELD}),
            'arquivo': forms.FileInput(attrs={
                'class': 'block w-full text-base sm:text-sm text-slate-600 file:mr-3 file:min-h-[48px] file:rounded-lg file:border-0 file:bg-indigo-50 file:px-4 file:font-medium file:text-indigo-700 hover:file:bg-indigo-100',
            }),
            'descricao': forms.TextInput(attrs={'class': FIELD}),
        }
