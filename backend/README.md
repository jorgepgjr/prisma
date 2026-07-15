# Backend - Portal Web para Galeria Escolar

Este diretório contém a API backend do portal da galeria escolar, construída utilizando FastAPI, SQLAlchemy e PostgreSQL.

## Pré-requisitos

- Python 3.12+
- Pipenv (`pip install pipenv`)
- Banco de dados PostgreSQL rodando (localmente ou via Docker Compose na raiz do projeto)

---

## Configuração e Inicialização

### 1. Banco de Dados

Certifique-se de que o banco de dados PostgreSQL está ativo. Se estiver usando o Docker Compose do projeto, execute na raiz:

```bash
docker compose up -d
```

### 2. Variáveis de Ambiente

Crie ou configure o arquivo `.env` neste diretório (`backend/.env`):

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/prisma
SECRET_KEY=sua-chave-secreta-de-desenvolvimento
```

### 3. Instalação de Dependências

Instale os pacotes necessários utilizando o Pipenv:

```bash
pipenv install
```

### 4. Alimentar o Banco de Dados (Seed)

Rode o script de seed para criar as tabelas do banco de dados e inserir dados de teste:

```bash
pipenv run python -m app.seed
```

Este comando limpa o banco de dados anterior, cria a estrutura de tabelas e insere:
- Usuários administrativos (`admin@school.com`, `diretor@school.com`, `coordenador@school.com`, `marketing@school.com` com senha `mypassword`).
- Professores (incluindo `marilia@school.com`).
- Turmas, alunos e fotos físicas simuladas vinculadas no banco de dados.

### 5. Executar o Servidor

Inicie a aplicação FastAPI com recarregamento automático (live-reload):

```bash
pipenv run uvicorn app.main:app --reload
```

O servidor iniciará na porta `8000`:
- **API Base:** [http://localhost:8000/](http://localhost:8000/)
- **Documentação Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentação ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Painel Administrativo (SQLAdmin):** [http://localhost:8000/admin](http://localhost:8000/admin)
