from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Sum, Q
from django.utils import timezone
import os
from django.conf import settings

from .models import ContaBancaria, Transacao, AnexoTransacao
from .forms import (
    ContaBancariaForm, TransacaoForm, ReceiptSignatureForm,
    ExpenseDeliveryForm, AnexoTransacaoForm
)
from .services import get_saldos, get_credito_curador


class ContaListView(ListView):
    model = ContaBancaria
    template_name = 'contas/lista.html'
    context_object_name = 'contas'


class ContaCreateView(CreateView):
    model = ContaBancaria
    form_class = ContaBancariaForm
    template_name = 'contas/form.html'
    success_url = reverse_lazy('contas:lista')


class ContaUpdateView(UpdateView):
    model = ContaBancaria
    form_class = ContaBancariaForm
    template_name = 'contas/form.html'
    success_url = reverse_lazy('contas:lista')


class ContaDeleteView(DeleteView):
    model = ContaBancaria
    template_name = 'contas/confirmar_exclusao.html'
    success_url = reverse_lazy('contas:lista')


def dashboard(request):
    """Main financial dashboard with metrics and recent transactions."""
    saldos = get_saldos()
    credito_curador = get_credito_curador()

    # Recent transactions (last 20)
    transacoes_recentes = Transacao.objects.all().order_by('-data', '-created_at')[:20]

    context = {
        'saldo_consolidado': saldos['saldo_consolidado'],
        'saldo_caixa': saldos['saldo_caixa'],
        'credito_curador': credito_curador,
        'transacoes_recentes': transacoes_recentes,
        'contas': saldos['contas'],
    }
    return render(request, 'dashboard.html', context)


def recibo_novo(request):
    """Touch-enabled signature receipt form."""
    if request.method == 'POST':
        form = ReceiptSignatureForm(request.POST, request.FILES)
        if form.is_valid():
            # Create transaction
            transacao = Transacao.objects.create(
                data=form.cleaned_data['data'],
                tipo='SAIDA',
                categoria=form.cleaned_data['categoria'],
                valor=form.cleaned_data['valor'],
                conta_origem=form.cleaned_data['conta_origem'],
                favorecido_nome=form.cleaned_data['favorecido_nome'],
                favorecido_cpf_cnpj=form.cleaned_data['favorecido_cpf_cnpj'],
                descricao=form.cleaned_data['descricao'],
                pago_pelo_curador=False,
            )

            # Handle signature (from canvas - base64 data in form)
            signature_data = request.POST.get('signature_data', '')
            if signature_data:
                # Save signature as file (in production: upload to Supabase Storage)
                import base64
                signature_decoded = base64.b64decode(signature_data.split(',')[1])
                signature_filename = f'assinatura_{transacao.id}.png'
                signature_path = os.path.join(settings.MEDIA_ROOT, 'assinaturas', signature_filename)
                os.makedirs(os.path.dirname(signature_path), exist_ok=True)
                with open(signature_path, 'wb') as f:
                    f.write(signature_decoded)

                # Create AnexoTransacao for signature
                AnexoTransacao.objects.create(
                    transacao=transacao,
                    tipo_documento='RECIBO_ASSINADO',
                    arquivo=f'assinaturas/{signature_filename}',
                    descricao='Assinatura digital do prestador'
                )

            # Handle Pix receipt upload
            if 'comprovante_pix' in request.FILES:
                AnexoTransacao.objects.create(
                    transacao=transacao,
                    tipo_documento='COMPROVANTE_PIX',
                    arquivo=request.FILES['comprovante_pix'],
                    descricao='Comprovante Pix'
                )

            messages.success(request, 'Recibo criado com sucesso!')
            return redirect('contas:dashboard')
    else:
        form = ReceiptSignatureForm(initial={'data': timezone.localdate()})

    return render(request, 'recibos/novo.html', {'form': form})


def despesa_nova(request):
    """Expense & delivery entry form with double attachment."""
    if request.method == 'POST':
        form = ExpenseDeliveryForm(request.POST, request.FILES)
        if form.is_valid():
            # Determine transaction type and source
            fonte = form.cleaned_data['fonte_recursos']
            if fonte == 'CURADOR':
                pago_pelo_curador = True
                conta_origem = None
            else:
                pago_pelo_curador = False
                conta_origem = form.cleaned_data['conta_origem']

            transacao = Transacao.objects.create(
                data=form.cleaned_data['data'],
                tipo='SAIDA',
                categoria=form.cleaned_data['categoria'],
                valor=form.cleaned_data['valor'],
                conta_origem=conta_origem,
                favorecido_nome=form.cleaned_data['favorecido_nome'],
                descricao=form.cleaned_data['descricao'],
                pago_pelo_curador=pago_pelo_curador,
            )

            # Double attachment for delivery/market categories
            categoria = form.cleaned_data['categoria']
            if categoria in ['IFOOD', 'FARMACIA', 'MERCADO']:
                if 'comprovante_pagamento' in request.FILES:
                    AnexoTransacao.objects.create(
                        transacao=transacao,
                        tipo_documento='COMPROVANTE_PIX',
                        arquivo=request.FILES['comprovante_pagamento'],
                        descricao='Comprovante financeiro (Pix/Banco)'
                    )
                if 'cupom_itemizado' in request.FILES:
                    AnexoTransacao.objects.create(
                        transacao=transacao,
                        tipo_documento='PRINT_DELIVERY' if categoria == 'IFOOD' else 'NOTA_FISCAL',
                        arquivo=request.FILES['cupom_itemizado'],
                        descricao='Cupom itemizado com endereço de entrega'
                    )
            elif 'comprovante_pagamento' in request.FILES:
                AnexoTransacao.objects.create(
                    transacao=transacao,
                    tipo_documento='COMPROVANTE_PIX',
                    arquivo=request.FILES['comprovante_pagamento'],
                    descricao='Comprovante de pagamento'
                )

            messages.success(request, 'Despesa registrada com sucesso!')
            return redirect('contas:dashboard')
    else:
        form = ExpenseDeliveryForm(initial={'data': timezone.localdate()})

    return render(request, 'despesas/nova.html', {'form': form})


def transacao_lista(request):
    """List all transactions with filters."""
    transacoes = Transacao.objects.all()

    # Filter by type
    tipo_filter = request.GET.get('tipo', '')
    if tipo_filter:
        transacoes = transacoes.filter(tipo=tipo_filter)

    # Filter by date range
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    if data_inicio:
        transacoes = transacoes.filter(data__gte=data_inicio)
    if data_fim:
        transacoes = transacoes.filter(data__lte=data_fim)

    # Filter by category
    categoria = request.GET.get('categoria', '')
    if categoria:
        transacoes = transacoes.filter(categoria=categoria)

    transacoes = transacoes.order_by('-data', '-created_at')

    context = {
        'transacoes': transacoes,
        'tipo_filter': tipo_filter,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'categoria_filter': categoria,
        'tipo_choices': Transacao.TIPO_CHOICES,
        'categoria_choices': Transacao.CATEGORIA_CHOICES,
    }
    return render(request, 'transacoes/lista.html', context)


def transacao_create(request):
    """Generic transaction creation form."""
    if request.method == 'POST':
        form = TransacaoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transação criada com sucesso!')
            return redirect('contas:transacao_lista')
    else:
        form = TransacaoForm(initial={'data': timezone.localdate()})

    return render(request, 'transacoes/form.html', {'form': form})


def transacao_update(request, pk):
    """Update transaction."""
    transacao = get_object_or_404(Transacao, pk=pk)
    if request.method == 'POST':
        form = TransacaoForm(request.POST, instance=transacao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transação atualizada com sucesso!')
            return redirect('contas:transacao_lista')
    else:
        form = TransacaoForm(instance=transacao)

    return render(request, 'transacoes/form.html', {'form': form, 'transacao': transacao})


def transacao_delete(request, pk):
    """Delete transaction."""
    transacao = get_object_or_404(Transacao, pk=pk)
    if request.method == 'POST':
        transacao.delete()
        messages.success(request, 'Transação excluída com sucesso!')
        return redirect('contas:transacao_lista')

    return render(request, 'transacoes/confirmar_exclusao.html', {'transacao': transacao})


def transacao_detail(request, pk):
    """Transaction detail with attachments."""
    transacao = get_object_or_404(Transacao, pk=pk)
    anexos = transacao.anexos.all()

    if request.method == 'POST':
        form = AnexoTransacaoForm(request.POST, request.FILES)
        if form.is_valid():
            anexo = form.save(commit=False)
            anexo.transacao = transacao
            anexo.save()
            messages.success(request, 'Anexo adicionado com sucesso!')
            return redirect('contas:transacao_detail', pk=transacao.pk)
    else:
        form = AnexoTransacaoForm()

    context = {
        'transacao': transacao,
        'anexos': anexos,
        'form': form,
    }
    return render(request, 'transacoes/detalhe.html', context)
