"""Funções de cálculo financeiro compartilhadas por views e relatórios."""
from decimal import Decimal

from django.db.models import Sum

from .models import ContaBancaria, Transacao


def get_saldos():
    """Saldos consolidados: todas as contas ativas + caixa físico."""
    contas = list(ContaBancaria.objects.filter(ativa=True))
    consolidado = sum((c.saldo_atual for c in contas), Decimal('0'))
    caixa = sum((c.saldo_atual for c in contas if c.tipo == 'CAIXA_FISICO'), Decimal('0'))
    return {
        'contas': contas,
        'saldo_consolidado': consolidado,
        'saldo_caixa': caixa,
        'tem_caixa': any(c.tipo == 'CAIXA_FISICO' for c in contas),
        'tem_banco': any(c.tipo == 'BANCO' for c in contas),
    }


def get_credito_curador():
    """Crédito pendente do curador = despesas com recursos próprios - reembolsos recebidos."""
    gastos = Transacao.objects.filter(pago_pelo_curador=True).aggregate(
        v=Sum('valor')
    )['v'] or Decimal('0')
    reembolsos = Transacao.objects.filter(tipo='REEMBOLSO_CURADOR').aggregate(
        v=Sum('valor')
    )['v'] or Decimal('0')
    return gastos - reembolsos


def get_totais_credito_curador():
    """Detalhamento do crédito do curador (gastos, reembolsos, pendente)."""
    gastos = Transacao.objects.filter(pago_pelo_curador=True).aggregate(
        v=Sum('valor')
    )['v'] or Decimal('0')
    reembolsos = Transacao.objects.filter(tipo='REEMBOLSO_CURADOR').aggregate(
        v=Sum('valor')
    )['v'] or Decimal('0')
    return {
        'gastos': gastos,
        'reembolsos': reembolsos,
        'pendente': gastos - reembolsos,
    }
