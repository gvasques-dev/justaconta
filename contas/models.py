import uuid

from django.db import models


class ContaBancaria(models.Model):
    TIPO_CHOICES = [
        ('BANCO', 'Conta Bancária'),
        ('CAIXA_FISICO', 'Caixa Físico (Espécie)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=100, verbose_name="Nome da Conta")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo")
    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Saldo Inicial")
    ativa = models.BooleanField(default=True, verbose_name="Ativa")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Conta Bancária"
        verbose_name_plural = "Contas Bancárias"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

    @property
    def saldo_atual(self):
        """Saldo atual = saldo inicial + entradas - saídas (apenas desta conta)."""
        from django.db.models import Sum

        entradas_qs = Transacao.objects.filter(conta_destino=self)
        saidas_qs = Transacao.objects.filter(conta_origem=self)

        if self.tipo == 'CAIXA_FISICO':
            # Saques bancários trazem espécie para o caixa físico.
            entradas_qs = entradas_qs.filter(
                tipo__in=['ENTRADA', 'DEPOSITO', 'TRANSF_INTERNA', 'SAQUE']
            )
        else:
            entradas_qs = entradas_qs.filter(
                tipo__in=['ENTRADA', 'DEPOSITO', 'TRANSF_INTERNA']
            )

        saidas_qs = saidas_qs.filter(
            tipo__in=['SAIDA', 'SAQUE', 'TRANSF_INTERNA', 'DEPOSITO', 'REEMBOLSO_CURADOR']
        ).exclude(pago_pelo_curador=True)

        entradas = entradas_qs.aggregate(total=Sum('valor'))['total'] or 0
        saidas = saidas_qs.aggregate(total=Sum('valor'))['total'] or 0

        return self.saldo_inicial + entradas - saidas


class Transacao(models.Model):
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada (Receita)'),
        ('SAIDA', 'Saída (Despesa)'),
        ('TRANSF_INTERNA', 'Transferência Interna'),
        ('SAQUE', 'Saque (Banco → Caixa)'),
        ('DEPOSITO', 'Depósito (Caixa → Banco)'),
        ('REEMBOLSO_CURADOR', 'Reembolso ao Curador'),
    ]

    CATEGORIA_CHOICES = [
        ('SAUDE', 'Saúde'),
        ('ALIMENTACAO', 'Alimentação'),
        ('CUIDADORES', 'Cuidadores'),
        ('APOSENTADORIA', 'Aposentadoria/Pensão'),
        ('MEDICAMENTOS', 'Medicamentos'),
        ('EXAMES', 'Exames'),
        ('TRANSPORTE', 'Transporte'),
        ('HIGIENE', 'Higiene Pessoal'),
        ('LAZER', 'Lazer/Bem-estar'),
        ('IFOOD', 'iFood/Delivery'),
        ('FARMACIA', 'Farmácia'),
        ('MERCADO', 'Mercado/Supermercado'),
        ('OUTROS', 'Outros'),
    ]

    # Regra de anexo duplo obrigatório (comprovante financeiro + cupom itemizado).
    CATEGORIAS_EXIGEM_DUPLO_ANEXO = ('IFOOD', 'FARMACIA', 'MERCADO')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data = models.DateField(verbose_name="Data")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo")
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, verbose_name="Categoria")
    valor = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor")
    conta_origem = models.ForeignKey(
        ContaBancaria, on_delete=models.PROTECT, related_name='transacoes_origem',
        null=True, blank=True, verbose_name="Conta de Origem",
    )
    conta_destino = models.ForeignKey(
        ContaBancaria, on_delete=models.PROTECT, related_name='transacoes_destino',
        null=True, blank=True, verbose_name="Conta de Destino",
    )
    pago_pelo_curador = models.BooleanField(
        default=False, verbose_name="Pago pelo Curador (Recursos Próprios)"
    )
    favorecido_nome = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Nome do Favorecido"
    )
    favorecido_cpf_cnpj = models.CharField(
        max_length=18, blank=True, null=True, verbose_name="CPF/CNPJ do Favorecido"
    )
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Transação"
        verbose_name_plural = "Transações"
        ordering = ['-data', '-created_at']

    def __str__(self):
        return f"{self.data} - {self.get_tipo_display()} - R$ {self.valor} - {self.categoria}"

    def clean(self):
        from django.core.exceptions import ValidationError

        out_of_pocket = self.pago_pelo_curador and self.tipo == 'SAIDA'

        if self.tipo in ('ENTRADA', 'DEPOSITO') and not self.conta_destino:
            raise ValidationError("Transações de entrada/depósito exigem conta_destino.")

        if self.tipo in ('SAIDA', 'SAQUE', 'REEMBOLSO_CURADOR') and not self.conta_origem:
            if not out_of_pocket:
                raise ValidationError("Transações de saída/saque/reembolso exigem conta_origem.")

        if self.tipo == 'TRANSF_INTERNA' and (not self.conta_origem or not self.conta_destino):
            raise ValidationError("Transferências internas exigem conta_origem e conta_destino.")

        if self.tipo == 'TRANSF_INTERNA' and self.conta_origem_id == self.conta_destino_id:
            raise ValidationError("Origem e destino da transferência devem ser diferentes.")

        if self.tipo == 'SAQUE':
            if not self.conta_destino or self.conta_destino.tipo != 'CAIXA_FISICO':
                raise ValidationError("Saque deve ter como destino uma conta do tipo Caixa Físico.")

        if self.tipo == 'DEPOSITO' and self.conta_origem and self.conta_origem.tipo != 'CAIXA_FISICO':
            raise ValidationError("Depósito deve ter como origem uma conta do tipo Caixa Físico.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def requer_duplo_anexo(self):
        """Delivery/mercado/farmácia exigem comprovante financeiro + cupom itemizado."""
        return self.categoria in self.CATEGORIAS_EXIGEM_DUPLO_ANEXO and self.tipo == 'SAIDA'

    @property
    def valor_sinalizado(self):
        """Valor com sinal para exibição (+ entrada / - saída)."""
        if self.tipo in ('ENTRADA', 'DEPOSITO'):
            return self.valor
        if self.tipo in ('SAIDA', 'SAQUE', 'REEMBOLSO_CURADOR', 'TRANSF_INTERNA'):
            if self.tipo == 'TRANSF_INTERNA':
                return self.valor
            return -self.valor
        return self.valor

    @property
    def eh_entrada(self):
        return self.tipo in ('ENTRADA', 'DEPOSITO')

    @property
    def eh_saida(self):
        return self.tipo in ('SAIDA', 'SAQUE', 'REEMBOLSO_CURADOR')


class AnexoTransacao(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('COMPROVANTE_PIX', 'Comprovante PIX'),
        ('RECIBO_ASSINADO', 'Recibo Assinado'),
        ('NOTA_FISCAL', 'Nota Fiscal'),
        ('PRINT_DELIVERY', 'Print do Delivery (iFood/etc)'),
        ('OUTRO', 'Outro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transacao = models.ForeignKey(
        Transacao, on_delete=models.CASCADE, related_name='anexos', verbose_name="Transação"
    )
    tipo_documento = models.CharField(
        max_length=20, choices=TIPO_DOCUMENTO_CHOICES, verbose_name="Tipo de Documento"
    )
    arquivo = models.FileField(upload_to='anexos/%Y/%m/', verbose_name="Arquivo")
    descricao = models.CharField(max_length=200, blank=True, verbose_name="Descrição")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Anexo de Transação"
        verbose_name_plural = "Anexos de Transações"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.transacao} - {self.get_tipo_documento_display()}"
