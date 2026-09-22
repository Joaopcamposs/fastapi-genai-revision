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
- **LangChain** (`create_agent`) + **Gemini** (`langchain-google-genai`) para o agente de IA
- **MCP** (`mcp[cli]`) para expor as mesmas ferramentas como servidor MCP
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

agent/
├── llm.py        # modelo (Gemini) e criação do agente ReAct (LangChain)
├── tools.py       # tools do agente LangChain (produtos e pedidos), escopadas ao usuário
├── formatting.py    # formatação de produtos/pedidos em texto, compartilhada entre tools.py e mcp_server.py
├── mcp_server.py      # servidor MCP standalone, expõe as mesmas consultas via protocolo MCP
├── routes.py            # router FastAPI (/agent)
├── schemas.py             # DTOs da rota do agente
└── utils.py                 # histórico de conversa por usuário (chat-history/*.json)
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

### Agente de IA (`/agent`)

Agente conversacional (LangGraph + Gemini) que responde perguntas sobre **produtos** e **pedidos** usando os repositórios de leitura já existentes (`ProductViewRepo`, `OrderViewRepo`) como *tools*. Não acessa o banco diretamente nem inventa dados — só responde com base no que as tools retornam.

- `POST /agent/ask` — envia uma pergunta (`{"question": "..."}`) e recebe a resposta completa do agente (autenticado)
- `POST /agent/ask/stream` — mesma coisa, mas via SSE (`text/event-stream`), com o conteúdo chegando token a token conforme o modelo gera
- `GET /agent/history` — histórico de perguntas/respostas do usuário autenticado
- `DELETE /agent/history` — limpa o histórico do usuário autenticado

**Como funciona:**

- `agent/tools.py` — monta as tools por requisição, escopadas ao usuário autenticado (`build_tools(user_id)`). `list_products` lista produtos disponíveis; `list_orders` lista **apenas** os pedidos do usuário logado — o `user_id` vem do JWT, nunca é informado pela LLM, então não há como um usuário perguntar pelos pedidos de outro.
- `agent/llm.py` — define o modelo (`gemini-3.5-flash` via `ChatGoogleGenerativeAI`) e `build_agent(tools)`, que cria um agente ReAct (`langchain.agents.create_agent`) com as tools da requisição.
- `agent/utils.py` — persiste o histórico de conversa por usuário em `chat-history/{email}.json` (as últimas 50 interações; só as últimas 10 entram no contexto enviado à LLM).
- `agent/routes.py` — router FastAPI que junta tudo: recupera histórico, monta o agente, invoca (ou faz stream via `agent.astream_events`), salva a resposta.

Requer `GOOGLE_API_KEY` configurada no `.env` (veja `.env_example`) — sem ela a aplicação falha no startup (`ensure_configured()` em `agent/llm.py`, chamado no `lifespan`). As chamadas ao Gemini têm timeout de 30s e até 2 retries.

### Servidor MCP (`agent/mcp_server.py`)

Expõe `list_products` e `list_orders` como um servidor [MCP](https://modelcontextprotocol.io/) standalone (transporte stdio), para uso em clientes MCP como Claude Desktop — desacoplado do FastAPI/LangChain, e reaproveitando a mesma lógica de leitura (`ProductViewRepo`, `OrderViewRepo`) e formatação (`agent/formatting.py`) usada pelas tools do agente.

```bash
make mcp
# ou: uv run python -m agent.mcp_server
```

Diferença importante em relação a `/agent`: não existe JWT/sessão HTTP no MCP — o cliente chama a tool diretamente. Por isso `list_orders` recebe o email do usuário como parâmetro explícito, em vez de vir de um `current_user` autenticado. Isso é aceitável para uso local/confiável (um dev plugando seu próprio banco no seu próprio cliente MCP), mas **não é multi-tenant-safe**: não exponha esse servidor em rede não confiável sem adicionar autenticação de verdade.

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
make mcp     # sobe o servidor MCP (stdio)
make ruff    # lint + format com ruff
```

## Testes

```bash
uv run pytest -x --tb=short -q
```

Cobertura: auth, users, products, orders (incluindo escopo por usuário), o agente (`agent/llm.py`, `agent/tools.py`, `agent/utils.py`, `agent/routes.py`, com o LLM real mockado — os testes não chamam a API do Gemini) e o servidor MCP (`agent/mcp_server.py`). Cada execução usa um `database.db` e um `chat-history/` isolados em `tests/` (via env vars `DATABASE_URL`/`CHAT_HISTORY_DIR`), nunca os dados reais do projeto.
