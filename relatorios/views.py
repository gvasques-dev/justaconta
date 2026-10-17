from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, date
from decimal import Decimal
import calendar

from contas.models import Transacao, ContaBancaria
from contas.services import get_saldos, get_credito_curador


def get_month_bounds(year, month):
    """Get first and last day of month."""
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return first_day, last_day


@login_required
def relatorio_mensal(request):
    """Monthly judicial report with filters and preview table."""
    # Get month/year from query params or default to current month
    today = timezone.localdate()
    year = int(request.GET.get('ano', today.year))
    month = int(request.GET.get('mes', today.month))

    first_day, last_day = get_month_bounds(year, month)

    # Get transactions for the month
    transacoes = Transacao.objects.filter(
        data__gte=first_day,
        data__lte=last_day
    ).order_by('data', 'created_at')

    # Calculate totals
    entradas = transacoes.filter(tipo__in=['ENTRADA', 'DEPOSITO']).aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0')

    saidas = transacoes.filter(tipo__in=['SAIDA', 'SAQUE', 'REEMBOLSO_CURADOR']).aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0')

    # Get current balances
    saldos = get_saldos()
    credito_curador = get_credito_curador()

    # Get all transactions with their attachments (for dossier preview)
    transacoes_with_anexos = []
    anexo_counter = 0
    for t in transacoes:
        anexos = list(t.anexos.all())
        anexos_indexed = []
        for anexo in anexos:
            anexo_counter += 1
            anexos_indexed.append({
                'anexo': anexo,
                'indice': anexo_counter,
                'label': f'Anexo #{anexo_counter:02d}'
            })
        transacoes_with_anexos.append({
            'transacao': t,
            'anexos': anexos_indexed,
        })

    # Build month options for filter (last 24 months)
    month_options = []
    for i in range(24):
        d = today.replace(day=1)
        # subtract i months
        m = d.month - i
        y = d.year
        while m <= 0:
            m += 12
            y -= 1
        month_options.append((y, m, calendar.month_abbr[m]))

    context = {
        'year': year,
        'month': month,
        'first_day': first_day,
        'last_day': last_day,
        'transacoes': transacoes_with_anexos,
        'entradas': entradas,
        'saidas': saidas,
        'saldo_consolidado': saldos['saldo_consolidado'],
        'saldo_caixa': saldos['saldo_caixa'],
        'credito_curador': credito_curador,
        'month_options': month_options,
        'month_name': calendar.month_abbr[month],
        'today': today,
    }
    return render(request, 'relatorios/mensal.html', context)


@login_required
def exportar_dossier_pdf(request):
    """Export court-ready PDF dossier for the selected month."""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.units import inch
    from io import BytesIO

    # Get parameters
    today = timezone.localdate()
    year = int(request.GET.get('ano', today.year))
    month = int(request.GET.get('mes', today.month))
    first_day, last_day = get_month_bounds(year, month)

    # Get transactions
    transacoes = Transacao.objects.filter(
        data__gte=first_day,
        data__lte=last_day
    ).order_by('data', 'created_at')

    # Calculate totals
    entradas = transacoes.filter(tipo__in=['ENTRADA', 'DEPOSITO']).aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0')

    saidas = transacoes.filter(tipo__in=['SAIDA', 'SAQUE', 'REEMBOLSO_CURADOR']).aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0')

    saldos = get_saldos()
    credito_curador = get_credito_curador()

    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=72)

    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1,  # Center
    )
    elements.append(Paragraph("RELAÇÃO JUDICIAL DE CONTAS", title_style))
    elements.append(Paragraph(f"Mês: {calendar.month_name[month]}/{year}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Balances summary
    elements.append(Paragraph("<b>SALDOS CONSOLIDADOS</b>", styles['Heading2']))
    saldo_data = [
        ['Saldo Consolidado Total', f'R$ {saldos["saldo_consolidado"]:.2f}'],
        ['Caixa Físico (Espécie)', f'R$ {saldos["saldo_caixa"]:.2f}'],
        ['Crédito Pendente do Curador', f'R$ {credito_curador:.2f}'],
    ]
    saldo_table = Table(saldo_data, colWidths=[4*inch, 2*inch])
    saldo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(saldo_table)
    elements.append(Spacer(1, 30))

    # Summary of movements
    elements.append(Paragraph("<b>RESUMO DOS MOVIMENTOS DO MÊS</b>", styles['Heading2']))
    resumo_data = [
        ['Total Entradas (Receitas)', f'R$ {entradas:.2f}'],
        ['Total Saídas (Despesas)', f'R$ {saidas:.2f}'],
        ['Resultado do Mês', f'R$ {entradas - saidas:.2f}'],
    ]
    resumo_table = Table(resumo_data, colWidths=[4*inch, 2*inch])
    resumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(resumo_table)
    elements.append(Spacer(1, 30))

    # Chronological table
    elements.append(Paragraph("<b>DETALHAMENTO CRONOLÓGICO DAS TRANSAÇÕES</b>", styles['Heading2']))

    # Table header
    table_data = [['Data', 'Tipo', 'Categoria', 'Descrição', 'Valor', 'Anexos']]

    anexo_counter = 0
    for t in transacoes:
        # Format valor with signal
        if t.tipo in ('ENTRADA', 'DEPOSITO'):
            valor_str = f'+ R$ {t.valor:.2f}'
        else:
            valor_str = f'- R$ {t.valor:.2f}'

        # Get anexos labels
        anexos = list(t.anexos.all())
        anexos_labels = []
        for anexo in anexos:
            anexo_counter += 1
            anexos_labels.append(f'#{anexo_counter:02d}')

        table_data.append([
            t.data.strftime('%d/%m/%Y'),
            t.get_tipo_display(),
            t.get_categoria_display(),
            (t.descricao or '')[:40] + ('...' if t.descricao and len(t.descricao) > 40 else ''),
            valor_str,
            ', '.join(anexos_labels)
        ])

    if len(table_data) > 1:
        # Create table
        detail_table = Table(table_data, colWidths=[0.9*inch, 1.2*inch, 1*inch, 2*inch, 1*inch, 0.7*inch])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(detail_table)
    else:
        elements.append(Paragraph("Nenhuma transação registrada neste período.", styles['Normal']))

    # Build PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    # Create response
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f'relacao_judicial_{year}_{month:02d}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


@login_required
def exportar_relatorio_reembolso(request):
    """Export curator reimbursement petition report."""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.units import inch
    from io import BytesIO

    # Get all out-of-pocket expenses (pago_pelo_curador=True)
    transacoes_curador = Transacao.objects.filter(
        pago_pelo_curador=True
    ).order_by('data')

    total_credito = transacoes_curador.aggregate(total=Sum('valor'))['total'] or Decimal('0')

    # Get reimbursements already made
    reembolsos = Transacao.objects.filter(
        tipo='REEMBOLSO_CURADOR'
    ).order_by('data')

    total_reembolsado = reembolsos.aggregate(total=Sum('valor'))['total'] or Decimal('0')

    credito_pendente = total_credito - total_reembolsado

    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=72)

    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1,
    )
    elements.append(Paragraph("REQUERIMENTO DE REEMBOLSO DE DESPESAS DO CURADOR", title_style))
    elements.append(Spacer(1, 20))

    # Summary
    elements.append(Paragraph("<b>RESUMO DO CRÉDITO DO CURADOR</b>", styles['Heading2']))
    resumo_data = [
        ['Total de Despesas com Recursos Próprios', f'R$ {total_credito:.2f}'],
        ['Total Reembolsado', f'R$ {total_reembolsado:.2f}'],
        ['Crédito Pendente', f'R$ {credito_pendente:.2f}'],
    ]
    resumo_table = Table(resumo_data, colWidths=[4*inch, 2*inch])
    resumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(resumo_table)
    elements.append(Spacer(1, 30))

    # List of out-of-pocket expenses
    if transacoes_curador.exists():
        elements.append(Paragraph("<b>DETALHAMENTO DAS DESPESAS COM RECURSOS PRÓPRIOS</b>", styles['Heading2']))

        table_data = [['Data', 'Categoria', 'Favorecido', 'Descrição', 'Valor']]
        for t in transacoes_curador:
            table_data.append([
                t.data.strftime('%d/%m/%Y'),
                t.get_categoria_display(),
                t.favorecido_nome or '-',
                (t.descricao or '')[:30] + ('...' if t.descricao and len(t.descricao) > 30 else ''),
                f'R$ {t.valor:.2f}'
            ])

        detail_table = Table(table_data, colWidths=[0.9*inch, 1*inch, 1.5*inch, 2*inch, 1*inch])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(detail_table)
    else:
        elements.append(Paragraph("Nenhuma despesa com recursos próprios registrada.", styles['Normal']))

    # Build PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    # Create response
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = 'requerimento_reembolso_curador.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response
