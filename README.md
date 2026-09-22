# fastapi-genai-revision

Projeto de estudo e revisão de **FastAPI**, design de **REST API**, **SQLAlchemy 2.0 (async)** e **DDD**. Nasceu do exemplo `Hero` da documentação oficial do FastAPI e foi migrado para um domínio próprio (`Product`/`Order`), com autenticação e arquitetura separada por contexto.

## Objetivo

Servir como base de revisão prática para:

- FastAPI (rotas, dependências, injeção de dependência, OAuth2)
- ORM assíncrono com SQLAlchemy 2.0 (`Mapped`/`mapped_column`)
- Design de API REST
- Conceitos de DDD aplicados de forma simples: agregados, invariantes de domínio, separação entre modelo de domínio e modelo de persistência
- Separação de responsabilidades entre leitura e escrita (CQRS-lite)

## Stack

- **FastAPI** (100% async)
- **SQLAlchemy 2.0** async ORM + **aiosqlite** (SQLite)
- **Pydantic v2** para schemas/DTOs
- **JWT** (`python-jose`) + **OAuth2 Password Flow** para autenticação
- **bcrypt** para hash de senha
- **uv** para gerenciamento de dependências
- **ruff** para lint/format

## Arquitetura

O código é separado por contexto/responsabilidade, cada arquivo com um papel único:

```
src/
├── aggregates.py     # modelo de domínio puro (dataclasses), sem SQLAlchemy
├── orm_models.py      # modelos de persistência (SQLAlchemy)
├── domain_repo.py      # repositórios de escrita, traduzem agregado <-> ORM
├── view_repo.py         # repositórios de leitura (somente query)
├── services.py            # camada de aplicação / casos de uso
├── schemas.py               # DTOs (Pydantic) usados nas rotas
└── entry_points.py            # routers FastAPI (HTTP layer)

infra/
├── database.py    # engine, sessão, tipo GUID (UUID <-> CHAR(36) no sqlite)
└── security.py    # hashing de senha e JWT (SecurityServices)
```

### Agregados e consistência

Cada entidade de domínio (`User`, `Product`, `Order`) é um agregado (`src/aggregates.py`) responsável por suas próprias invariantes — validações de negócio acontecem no domínio, não nas rotas ou no ORM. `Order` é o agregado raiz que também gerencia seus `OrderItem`.

### Leitura vs. escrita

Repositórios de domínio (`domain_repo.py`) lidam com escrita e usam uma sessão padrão do `AsyncSession`. Repositórios de view (`view_repo.py`) lidam só com leitura e usam uma sessão com `isolation_level=AUTOCOMMIT`, mantendo a separação de intenção entre os dois lados. Ambos criam sua própria sessão por padrão, mas aceitam receber uma sessão externa (override) quando necessário.

### IDs

Todos os IDs são `UUID` (gerados com `uuid7`), armazenados como `CHAR(36)` no SQLite via o tipo customizado `GUID` (`infra/database.py`), que converte automaticamente `UUID <-> str` na fronteira com o banco.

## Funcionalidades

### Autenticação (`/auth`)

- `POST /auth/token` — login via OAuth2 Password Flow (usuário/senha), retorna um JWT Bearer token

### Usuários (`/users`)

- `POST /users/` — cria usuário (email único, senha com hash bcrypt)
- `GET /users/` — lista usuários (autenticado)
- `GET /users/{email}` — busca usuário por email (autenticado, só o próprio usuário)

### Produtos (`/products`)

- `POST /products/` — cria produto (autenticado)
- `GET /products/` — lista produtos (autenticado)

### Pedidos (`/orders`)

- `POST /orders/` — cria pedido com um ou mais itens, vinculado ao usuário autenticado
- `GET /orders/` — lista pedidos do usuário autenticado
- `GET /orders/{order_id}` — busca um pedido específico do usuário autenticado

> Produtos não são vinculados a usuário; pedidos sempre são vinculados ao usuário autenticado (via JWT).

## Rodando o projeto

```bash
uv sync
cp .env_example .env
uv run fastapi dev
```

A aplicação cria o banco SQLite (`database.db`) e as tabelas automaticamente no startup (`lifespan`).

Docs interativos: `http://localhost:8000/docs`

## Comandos úteis (Makefile)

```bash
make run     # sobe o servidor em modo dev
make ruff    # lint + format com ruff
```
