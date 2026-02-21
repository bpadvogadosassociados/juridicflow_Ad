# JuridicFlow ERP ⚖️

Sistema ERP jurídico modular para escritórios de advocacia.

------------------------------------------------------------------------

## 📦 Stack Tecnológica

### Backend

-   Python 3.12
-   Django 5+
-   Django REST Framework
-   SQLite
-   JWT (SimpleJWT)
-   Django Signals

### Frontend

-   Django Templates
-   Bootstrap (AdminLTE / Jazzmin)
-   Vanilla JavaScript modular
-   FullCalendar
-   Chart.js

------------------------------------------------------------------------

## 🗂 Estrutura do Projeto

    juridicflow/
    │
    ├── apps/
    │   ├── accounts/
    │   ├── organizations/
    │   ├── offices/
    │   ├── memberships/
    │   ├── customers/
    │   ├── processes/
    │   ├── deadlines/
    │   ├── finance/
    │   ├── documents/
    │   ├── portal/
    │   ├── publications/
    │   ├── shared/
    │   └── core/
    │
    ├── config/
    ├── templates/
    ├── static/
    ├── manage.py
    └── requirements.txt

------------------------------------------------------------------------

## ⚙️ Instalação (Ambiente Local)

### 1️⃣ Clone o repositório

``` bash
git clone <url-do-repositorio>
cd juridicflow
```

### 2️⃣ Instale o Python 3.12

``` bash
python3 --version
```

### 3️⃣ Crie ambiente virtual

``` bash
python3 -m venv ambiente
```

Ative:

Linux / Mac:

``` bash
source ambiente/bin/activate
```

Windows:

``` bash
ambiente\Scripts\activate
```

### 4️⃣ Instale dependências

``` bash
pip install -r requirements.txt
```

### 5️⃣ Configure variáveis

``` bash
cp .env.example .env
```

### 6️⃣ Rode migrações

``` bash
python manage.py makemigrations
python manage.py migrate
```

### 7️⃣ Crie superusuário

``` bash
python manage.py createsuperuser
```

### 8️⃣ Inicie o servidor

``` bash
python manage.py runserver
```

Acesse:

    http://127.0.0.1:8000

------------------------------------------------------------------------

## 🔐 Primeira Configuração

1.  Criar Organização\
2.  Criar Office\
3.  Criar Membership vinculando usuário ↔ organização ↔ office ↔ role

Sem Membership o usuário não consegue acessar o portal.

------------------------------------------------------------------------

## 📊 Módulos

### 🧾 Processos

Gestão completa de processos jurídicos.

### 📇 CRM / Pipeline

Gestão de leads e clientes.

### 💰 Financeiro

Contratos, faturas e despesas.

### ⏰ Prazos

Controle e calendário de prazos.

### 💬 Chat

Comunicação interna.

### 🔔 Notificações

Disparadas automaticamente via Signals.

### 📈 Relatórios

Dashboard analítico com gráficos.

------------------------------------------------------------------------

## 📌 Banco de Dados

SQLite (uso local para testes).

------------------------------------------------------------------------

## 🚧 Status

Projeto em fase de testes internos.
