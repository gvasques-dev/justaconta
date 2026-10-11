# JustaConta — Gestor Financeiro de Curatela

Aplicação web minimalista para gerenciar finanças de curatela legal, automatizar relatórios prontos para o tribunal, capturar assinaturas digitais e controlar créditos do curador pagos do próprio bolso.

Feita para cuidadores em campo: mobile-first, touch-friendly, rápida e barata de hospedar (100% free tier).

## 1. O que o projeto resolve

- Controle de contas bancárias do curatelado + caixa físico (espécie).
- Registro de todas as movimentações: entradas, saídas, transferências internas, saques, depósitos e reembolsos ao curador.
- Crédito do curador: despesas pagas com recursos próprios acumulam saldo pendente de reembolso, sem abater das contas do curatelado.
- Recibos assinados na tela (dedo/stylus) com comprovante Pix anexado.
- Regra de anexo duplo para delivery/mercado/farmácia: comprovante financeiro + cupom itemizado com endereço.
- Dossiê mensal em PDF pronto para juntar no processo judicial.

## 2. Funcionalidades

- **Dashboard (`/`):** Saldo Consolidado, Caixa Físico, Crédito do Curador + transações recentes com status de anexo.
- **Recibo assinado (`/recibos/novo`):** data, prestador, CPF, serviço, valor, conta origem, upload do Pix, canvas `signature_pad` com limpar/salvar.
- **Despesa/delivery (`/despesas/nova`):** categoria, estabelecimento (iFood, Keeta, farmácia), toggle `Conta do Curatelado x Recursos do Curador`, dois slots de upload para categorias delivery.
- **Transações (`/transacoes/`):** lista com filtros, detalhe com anexos, criar/editar/excluir.
- **Contas (`/contas/`):** CRUD de `BANCO` e `CAIXA_FISICO`.
- **Relatórios (`/relatorios/`):** filtro mês/ano, tabela cronológica com `Anexo #01, #02...`, exportação PDF do dossiê + relatório de reembolso.

## 3. Stack

- **Backend:** Python 3.12 + Django 5.x monolítico
- **Banco:** PostgreSQL via Supabase (free tier), `dj-database-url`. Local: SQLite
- **Storage:** Supabase Storage (PDFs, recibos, prints). Local: `media/`
- **Frontend:** Django Templates + Tailwind CSS (CDN) + Alpine.js + `signature_pad.js`
- **PDF:** ReportLab
- **Hospedagem:** Render.com Free Web Service + Gunicorn + Whitenoise

## 4. Modelo de dados

**ContaBancaria**
`id (UUID), nome, tipo [BANCO, CAIXA_FISICO], saldo_inicial, ativa`

**Transacao**
`id (UUID), data, tipo [ENTRADA, SAIDA, TRANSF_INTERNA, SAQUE, DEPOSITO, REEMBOLSO_CURADOR], categoria [SAUDE, ALIMENTACAO, CUIDADORES, APOSENTADORIA, MEDICAMENTOS, EXAMES, TRANSPORTE, HIGIENE, LAZER, IFOOD, FARMACIA, MERCADO, OUTROS], valor, conta_origem (nullable), conta_destino (nullable), pago_pelo_curador (bool), favorecido_nome, favorecido_cpf_cnpj, descricao`

**AnexoTransacao**
`id (UUID), transacao (FK), tipo_documento [COMPROVANTE_PIX, RECIBO_ASSINADO, NOTA_FISCAL, PRINT_DELIVERY, OUTRO], arquivo, descricao`

## 5. Regras de negócio

- `SAQUE`: exige destino `CAIXA_FISICO`. `DEPOSITO`: exige origem `CAIXA_FISICO`.
- `pago_pelo_curador=True` + `SAIDA`: não abate saldo das contas; soma no Crédito do Curador.
- `REEMBOLSO_CURADOR`: sai da conta do curatelado e abate o crédito pendente.
- Categorias `IFOOD, FARMACIA, MERCADO` exigem 2 anexos.
- Equação de conciliação: `Saldo Inicial + Entradas − Saídas = Saldo Final`.

## 6. UI mobile-first

- Mobile (<1024px): topbar fixa + bottom nav com 5 ícones, alvos de toque `min-h-[48px]`, safe-area `env()`.
- Desktop: sidebar fixa.
- Forms em `grid-cols-1 md:grid-cols-2`, `text-base` no mobile (evita zoom do iOS).
- Canvas `h-48 sm:h-64`, com `touch-action: none`, `preventDefault` no toque e persistência da assinatura na rotação.
- Tabelas: cards empilhados no mobile, `overflow-x-auto` com indicador de swipe no desktop.

## 7. Rodar localmente

```bash
git clone <seu-repo> justaconta
cd justaconta
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` local:
```env
SECRET_KEY=troque-por-uma-chave-segura
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
SUPABASE_URL=
SUPABASE_KEY=
```

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
# http://localhost:8000/ | admin: http://localhost:8000/admin/
```

## 8. Publicar grátis (Supabase + Render)

**8.1 Supabase (banco + storage)**
1. Crie conta em supabase.com → New Project (free tier).
2. Em Project Settings → Database, copie a `Connection string` (modo Session, porta 6543).
3. Em Storage, crie o bucket `justaconta-documents` (privado).
4. Guarde: `SUPABASE_URL`, `SUPABASE_KEY` (anon), `DATABASE_URL`.

**8.2 Render (app)**
1. Suba o código para o GitHub.
2. render.com → New → Web Service → selecione o repo.
3. O `render.yaml` na raiz já configura: Build Command, Start Command, `PYTHON_VERSION=3.12.4`, `DEBUG=False`, `SECRET_KEY` auto-gerado. Basta conectar o repo.
4. Coloque no painel (Environment) as variáveis `sync: false`:
   ```env
   DATABASE_URL=<connection-string-supabase>
   SUPABASE_URL=<sua-url>
   SUPABASE_KEY=<sua-anon-key>
   ```
5. Deploy. Teste: `/`, `/admin/`, exportação de PDF.

**8.3 Validação pós-deploy**
- Acesse `https://<seu-app>.onrender.com/` → dashboard carrega.
- `/admin/` → login funciona.
- `/relatorios/` → PDF exporta sem erro.

**8.4 Atenção free tier**
- Render dorme após inatividade (~50s para acordar).
- Disco efêmero: `media/` local é apagado no restart — em produção use Supabase Storage para arquivos permanentes.

## 9. Estrutura

```
justaconta/
├── justaconta/        # settings, urls, wsgi, asgi
├── contas/            # models, forms, views, services, admin
├── relatorios/        # views de relatório + PDFs ReportLab
├── templates/         # base.html + dashboard, recibos, despesas, transacoes, relatorios, contas
├── media/             # uploads (só dev local, efêmero no Render)
├── staticfiles/       # collectstatic (gerado no build)
├── requirements.txt
├── .env.example
├── render.yaml        # configuração Render (build/start/env)
├── build.sh           # script build alternativo
├── Procfile           # gunicorn start (fallback)
├── runtime.txt        # python-3.12.4
├── .gitignore
└── README.md
```

## 10. Segurança

- Nunca commite `.env`. Use `SECRET_KEY` forte e `DEBUG=False` em produção.
- HTTPS automático no Render + `SECURE_SSL_REDIRECT`, HSTS, cookies secure.
- CSRF_TRUSTED_ORIGINS configurado para o domínio Render.
- Valide tipos de arquivo enviados; limite tamanho.
- Trilha de auditoria: nunca edite valores históricos sem registrar — prefira estorno.

## 11. Roadmap (sugestões)

- Integração automática com Supabase Storage via API (hoje os anexos ficam em `media/` local no dev).
- Login por papel (curador / curatelado) além do Django admin.
- Conciliação bancária via OFX/CNAB.
- Assinatura do juiz/revisor no dossiê exportado.
