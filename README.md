# Intranet Carmel

Portal interno do grupo Carmel Hotéis para acesso centralizado a dashboards de BI, com autenticação via Google OAuth e controle de acesso por usuário.

## Visão Geral

- Autenticação SSO via **Google OAuth** (ou Zoho)
- Acesso a dashboards **Power BI** embarcados por setor
- Painel administrativo para gerenciar usuários e permissões
- Importação de dashboards via **Google Sheets** ou CSV

## Stack

| Componente | Tecnologia |
|---|---|
| Backend | Python 3.11 + Flask 3 |
| Banco de dados | PostgreSQL (produção) / SQLite (dev) |
| Auth | Authlib + Google OAuth 2.0 |
| Frontend | Bootstrap 5.3 |
| Servidor | Gunicorn |

## Configuração

### 1. Clone e ambiente virtual

```bash
git clone https://github.com/jadsonmorais/intranet.git
cd intranet_carmel
python3 -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### 2. Variáveis de ambiente

Copie o template e preencha:

```bash
cp .env.example .env
```

| Variável | Obrigatório | Descrição |
|---|---|---|
| `SECRET_KEY` | ✅ | Chave Flask — gere com `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | ✅ em prod | URL PostgreSQL. Padrão: SQLite local |
| `GOOGLE_CLIENT_ID` | ✅ | OAuth 2.0 Client ID (Google Cloud Console) |
| `GOOGLE_CLIENT_SECRET` | ✅ | OAuth 2.0 Client Secret |
| `SUPERADMIN_EMAIL` | | E-mail sempre admin/ativo. Padrão: `suporte@carmelhoteis.com.br` |
| `ZOHO_CLIENT_ID` | | OAuth Zoho (opcional) |
| `ZOHO_CLIENT_SECRET` | | OAuth Zoho (opcional) |
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | | Caminho para o JSON da Service Account |
| `GOOGLE_SHEETS_ID` | | ID da planilha Google Sheets |
| `GOOGLE_SHEETS_TAB` | | Nome da aba na planilha |
| `FLASK_DEBUG` | | `1` apenas em desenvolvimento local |

### 3. Google OAuth

1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
3. Tipo: **Web application**
4. Authorized redirect URIs: `https://seudominio.com/auth/authorize`
5. Copie Client ID e Client Secret para o `.env`

### 4. Inicializar banco de dados

```bash
flask shell
>>> from app.extensions import db
>>> db.create_all()
>>> exit()
```

### 5. Rodar em desenvolvimento

```bash
FLASK_DEBUG=1 python run.py
```

### 6. Rodar em produção (Gunicorn)

```bash
gunicorn -w 1 -b 127.0.0.1:8000 run:app
```

O `intranet.service` do systemd já está configurado no servidor.

## Estrutura do Projeto

```
intranet_carmel/
├── app/
│   ├── __init__.py          # App factory, registro de blueprints
│   ├── models.py            # User, Dashboard, UserDashboard
│   ├── extensions.py        # SQLAlchemy, LoginManager, OAuth
│   ├── auth.py              # Rotas de autenticação (Google, Zoho)
│   ├── routes.py            # Rotas principais (área de BI, embed)
│   ├── admin.py             # Painel admin (usuários, dashboards, import)
│   ├── admin_guard.py       # Decorator @admin_required
│   └── templates/           # Templates Jinja2
│       ├── base.html
│       ├── login.html
│       ├── area_bi.html
│       ├── dashboard_embed.html
│       └── admin/
├── instance/
│   └── google-service-account.json  # Credencial Google Sheets (não versionado)
├── config.py                # Configuração centralizada
├── run.py                   # Entry point
├── requirements.txt
├── .env.example             # Template de variáveis
└── DEPLOY_SHEETS_SYNC.md    # Guia de integração Google Sheets
```

## Fluxo de Acesso

```
Usuário acessa /
    ↓
Redireciona para /auth/login
    ↓
Clica "Entrar com Google"
    ↓
Google OAuth valida identidade
    ↓
Sistema verifica:
  1. Domínio do e-mail (lista ALLOWED_EMAIL_DOMAINS)
  2. Usuário existe no banco (cadastrado por admin)
  3. Usuário está ativo
    ↓
Login → /bi/ (dashboards liberados para o usuário)
```

## Gerenciamento de Usuários

Apenas administradores podem cadastrar novos usuários em `/admin/`.

Um novo usuário precisa ser cadastrado **antes** de fazer o primeiro login.

### Permissões

- **Admin**: vê e gerencia todos os dashboards e usuários
- **Usuário comum**: vê apenas os dashboards liberados pelo admin

### Importar usuários via CSV

```bash
python import_users_csv.py usuarios.csv
```

Formato do CSV: `email;setor` (suporta `;`, `,`, `\t` e `|` como delimitador)

## Importação de Dashboards

Acesse `/admin/dashboards/import`. Três modos:

1. **Manual** — cole linhas no formato `setor | nome | slug | url`
2. **Google Sheets** — sincroniza com planilha configurada no `.env`

Modo de importação:
- **Sync** — atualiza existentes, adiciona novos
- **Substituir tudo** — remove tudo e reimporta

Veja [DEPLOY_SHEETS_SYNC.md](DEPLOY_SHEETS_SYNC.md) para configurar Google Sheets.

## Domínios Autorizados

Definidos em `config.py`. Apenas e-mails desses domínios podem se autenticar:

- `carmelhoteis.com.br`
- `carmelcharme.com.br`
- `carmelcumbuco.com.br`
- `carmeltaiba.com.br`
- `magnapraiahotel.com.br`
- `magnaloc.com.br`

## Parte do Ecossistema Carmel

Este projeto faz parte de um ecossistema maior:

| Projeto | Descrição |
|---|---|
| **infraspeak** | ETL Python — coleta dados de manutenção, PDV, NF-e e fiscal |
| **chat-reservas** | Bot WhatsApp para equipe de reservas (análise de voos) |
| **intranet_carmel** | Este projeto — portal de dashboards |
| **cmflex-erp-agent** | Automação de aquecimento do ERP CMFlex |
