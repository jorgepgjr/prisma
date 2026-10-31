# Portal Web para Galeria Escolar (Prisma)

Este é um projeto full-stack para gerenciar uma galeria escolar de fotos com controle de acesso baseado em regras (RBAC). O projeto é dividido em um backend FastAPI (Python) e um frontend Next.js (React/TypeScript), utilizando PostgreSQL como banco de dados.

## Gestão de publicações

- **Publicações** (`/publications`): professores visualizam suas turmas e podem criar, editar e excluir apenas publicações de sua autoria. A coordenação administra toda a escola. Marketing não tem acesso.
- Criação e edição acontecem em modal, com legenda, fotos e alunos destinatários. A turma de uma publicação já identificada não pode ser alterada. As mudanças aparecem para as famílias ao atualizar o feed.
- Excluir uma publicação remove seus vínculos, não os arquivos das fotos, suas tags, a identificação dos alunos ou os portfólios.
- As bibliotecas da turma e da coordenação mostram **Em publicação**, contagem de uso e filtros **Todas / Em publicação / Não utilizadas**. O indicador considera apenas publicações existentes.
- A API aplica automaticamente uma migração incremental de turma, autoria e ordem das fotos. Publicações antigas preservam o nome do autor, mas ficam sob gestão da coordenação; não se atribui autoria de conta pelo nome. **Não execute seed para aplicar esta atualização.**
- APIs administrativas: `GET/POST /api/posts/`, `GET/PUT/DELETE /api/posts/{id}`. `class_id` é opcional na listagem; respostas incluem `photo_ids`, `student_ids`, `created_by_user_id`, `class_id` e `can_manage`. Fotos incluem `publication_count`. Os endpoints familiares continuam compatíveis.
- O [guia de testes](GUIA_DE_TESTES_E_FLUXOS.md) descreve os fluxos e os limites do MVP.

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

Recrie e alimente o banco de desenvolvimento (Seed):
```bash
pipenv run python seed.py
```
> Atenção: o seed apaga os dados locais existentes e cria duas escolas para validar o isolamento multi-escola.

Contas principais da Escola Girassol (senha `mypassword`):

- Coordenação: `coordenacao@girassol.com`
- Professor: `professora@girassol.com`
- Marketing: `marketing@girassol.com`

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
