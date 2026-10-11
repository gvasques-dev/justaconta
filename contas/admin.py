from django.contrib import admin
from .models import ContaBancaria, Transacao, AnexoTransacao


@admin.register(ContaBancaria)
class ContaBancariaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'saldo_inicial', 'ativa', 'created_at']
    list_filter = ['tipo', 'ativa']
    search_fields = ['nome']


@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    list_display = ['data', 'tipo', 'categoria', 'valor', 'favorecido_nome', 'pago_pelo_curador', 'created_at']
    list_filter = ['tipo', 'categoria', 'pago_pelo_curador', 'data']
    search_fields = ['descricao', 'favorecido_nome', 'favorecido_cpf_cnpj']
    date_hierarchy = 'data'


@admin.register(AnexoTransacao)
class AnexoTransacaoAdmin(admin.ModelAdmin):
    list_display = ['transacao', 'tipo_documento', 'uploaded_at']
    list_filter = ['tipo_documento']
