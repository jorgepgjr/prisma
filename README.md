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

## Como Rodar a Aplicação Localmente

Você tem duas opções para iniciar a aplicação: **Automática (Recomendado)** ou **Manual**.

### 1. Iniciar o Banco de Dados (PostgreSQL)

O banco de dados é gerenciado via Docker Compose. Certifique-se de que o Docker está rodando e execute na raiz do projeto:

```bash
docker compose up -d
```

### 2. Opção A: Iniciar Automático (Frontend + Backend)

A forma mais rápida e recomendada de subir tudo (API e Interface) em um único terminal é através do nosso script de inicialização.

Certifique-se de ter dado permissão de execução (apenas na primeira vez):
```bash
chmod +x start.sh
```

Execute o script:
```bash
./start.sh
```

O script vai subir a API Python na porta 8000 e o Next.js na porta 3000. Para encerrar ambos os processos, basta pressionar `CTRL+C` uma vez.

---

### 2. Opção B: Iniciar Manualmente

Caso prefira rodar os serviços em terminais separados, siga os passos abaixo.

#### Backend
Em um terminal, acesse a pasta `backend/` e instale as dependências:
```bash
cd backend
pipenv install
```

Configure o arquivo `.env` em `backend/`:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/prisma
SECRET_KEY=uma-chave-secreta-muito-segura-para-desenvolvimento-local-do-portal-web
```

Alimente o Banco de Dados (Seed):
```bash
pipenv run python seed.py
```
*(Nota: O script de seed popula contas de pais, crianças e projetos para o TinhaKids!)*

Inicie o Servidor:
```bash
pipenv run uvicorn app.main:app --reload
```
A API ficará disponível em http://localhost:8000 e o Swagger em http://localhost:8000/docs.

#### Frontend
Em outro terminal, acesse a pasta `frontend/`:
```bash
cd frontend
npm install
npm run dev
```
O portal ficará disponível em http://localhost:3000.
