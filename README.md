# Portal Web para Galeria Escolar (Prisma)

Este é um projeto full-stack para gerenciar uma galeria escolar de fotos com controle de acesso baseado em regras (RBAC). O projeto é dividido em um backend FastAPI (Python) e um frontend Next.js (React/TypeScript), utilizando PostgreSQL como banco de dados.

## Estrutura do Projeto

- `/backend`: API construída com FastAPI, SQLAlchemy e PostgreSQL.
- `/frontend`: Interface do usuário construída com Next.js.
- `docker-compose.yml`: Configuração do banco de dados PostgreSQL.

---

## Pré-requisitos

Antes de iniciar, certifique-se de ter instalado em sua máquina:
- [Docker](https://www.docker.com/) e Docker Compose
- [Python 3.12+](https://www.python.org/)
- [Pipenv](https://pipenv.pypa.io/) (`pip install pipenv`)
- [Node.js](https://nodejs.org/) (versão LTS recomendada)

---

## Como Rodar a Aplicação

### 1. Iniciar o Banco de Dados

O banco de dados PostgreSQL é gerenciado via Docker Compose. Para iniciá-lo, execute na raiz do projeto:

```bash
docker compose up -d
```

Isso subirá um container PostgreSQL na porta `5432` com as credenciais padrão configuradas no `docker-compose.yml`.

---

### 2. Configurar e Iniciar o Backend

Navegue para o diretório do backend:

```bash
cd backend
```

#### Passo A: Configurar Variáveis de Ambiente
Verifique ou crie o arquivo `.env` na pasta `backend/`. Ele deve conter as seguintes configurações:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/prisma
SECRET_KEY=uma-chave-secreta-muito-segura-para-desenvolvimento-local-do-portal-web
```

#### Passo B: Instalar as Dependências
Utilize o Pipenv para instalar as dependências do Python em um ambiente virtual isolado:

```bash
pipenv install
```

#### Passo C: Alimentar o Banco de Dados (Seed)
Para criar as tabelas e popular o banco de dados com dados de teste (usuários de demonstração, turmas, alunos e fotos), execute o script de semente:

```bash
pipenv run python -m app.seed
```

*Nota: Os seguintes usuários serão criados com a senha `mypassword`:*
- *Administrador:* `admin@school.com`
- *Diretor:* `diretor@school.com`
- *Coordenador:* `coordenador@school.com`
- *Marketing:* `marketing@school.com`
- *Professora Marília Sena:* `marilia@school.com`

#### Passo D: Iniciar o Servidor FastAPI
Inicie o servidor de desenvolvimento utilizando o Uvicorn:

```bash
pipenv run uvicorn app.main:app --reload
```

A API estará disponível em [http://localhost:8000](http://localhost:8000).
Você pode acessar a documentação interativa (Swagger UI) em [http://localhost:8000/docs](http://localhost:8000/docs).
A área de administração do SQLAdmin estará disponível em [http://localhost:8000/admin](http://localhost:8000/admin).

---

### 3. Configurar e Iniciar o Frontend

Em um novo terminal, navegue para o diretório do frontend:

```bash
cd frontend
```

#### Passo A: Instalar Dependências
Instale os pacotes do Node.js:

```bash
npm install
```

#### Passo B: Iniciar o Servidor Next.js
Execute o servidor de desenvolvimento:

```bash
npm run dev
```

Abra [http://localhost:3000](http://localhost:3000) no seu navegador para acessar a aplicação.
