# Sincronizacao de Dashboards via Google Sheets

Este guia explica como configurar a Service Account no servidor (fora do Git)
para permitir o sync automatico dos dashboards pela planilha.

## 1) Criar Service Account
1. Acesse o Google Cloud Console.
2. Crie ou selecione um projeto.
3. Habilite a API: "Google Sheets API".
4. Va em "IAM & Admin" > "Service Accounts".
5. Crie uma Service Account.
6. Crie uma chave JSON e faca o download.

## 2) Compartilhar a planilha com a Service Account
1. Abra a planilha no Google Sheets.
2. Clique em "Compartilhar".
3. Adicione o e-mail da Service Account (termina com `iam.gserviceaccount.com`).
4. Permissao: "Leitor".

## 3) Subir o JSON no servidor (fora do Git)
1. Copie o JSON para o servidor em:
   `instance/google-service-account.json`
2. Nao commitar este arquivo no Git.

## 4) Configurar variaveis de ambiente no servidor
Defina as variaveis abaixo (ex.: no `.env` do servidor):

```
GOOGLE_SHEETS_CREDENTIALS_PATH=instance/google-service-account.json
GOOGLE_SHEETS_ID=1Gj4ol8tQzFtdIYbYNIexTy2AnfsbXM3A86E3KWqkgCA
GOOGLE_SHEETS_TAB=dashboard_import_template
```

## 5) Dependencias
Instale as dependencias no servidor:

```
pip install -r requirements.txt
```

## 6) Validacao
Depois de configurar, o botao "Sincronizar do Sheets" no admin deve:
- Ler a aba informada.
- Atualizar dashboards por slug.
- Remover dashboards ausentes (se marcado).

Em caso de erro, verificar:
- Permissoes da planilha para a Service Account.
- Caminho do JSON e permissoes de leitura no servidor.
- ID da planilha e nome da aba.
