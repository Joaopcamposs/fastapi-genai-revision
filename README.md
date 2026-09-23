# fastapi-genai-revision

Projeto de estudo e revisão de **FastAPI**, design de **REST API**, **SQLAlchemy 2.0 (async)** e **DDD**. Nasceu do exemplo `Hero` da documentação oficial do FastAPI e foi migrado para um domínio próprio (`Product`/`Order`), com autenticação e arquitetura separada por contexto.

## Objetivo

Servir como base de revisão prática para:

- FastAPI (rotas, dependências, injeção de dependência, OAuth2)
- ORM assíncrono com SQLAlchemy 2.0 (`Mapped`/`mapped_column`)
- Design de API REST
- Conceitos de DDD aplicados de forma simples: agregados, invariantes de domínio, separação entre modelo de domínio e modelo de persistência
- Separação de responsabilidades entre leitura e escrita (CQRS-lite)
- Multi-tenancy simples: cada usuário é seu próprio tenant

## Stack

- **FastAPI** (100% async)
- **SQLAlchemy 2.0** async ORM + **aiosqlite** (SQLite)
- **Pydantic v2** para schemas/DTOs
- **JWT** (`python-jose`) + **OAuth2 Password Flow** para autenticação
- **bcrypt** para hash de senha
- **LangChain** (`create_agent`) + **Gemini** (`langchain-google-genai`) para o agente de IA
- **MCP** (`mcp[cli]`) para expor as mesmas ferramentas como servidor MCP
- **slowapi** para rate limiting (endpoints públicos, sem auth)
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

### Multi-tenancy

Cada usuário é o dono do seu próprio tenant — o `id` do usuário autenticado (via JWT) é o `tenant_id` usado para isolar dados entre contas. Não existe uma tabela `tenants` separada; o tenant **é** o `User`.

- `Order` é escopado por `user_id`: cada usuário só lista/vê seus próprios pedidos.
- Não existe listagem de usuários (vazaria outros tenants). `GET /users/me` retorna só o próprio usuário autenticado; `GET /users/{email}` também é restrito ao próprio usuário.
- `Product` é a exceção: **é público**, visível a qualquer usuário autenticado, e qualquer usuário pode incluir qualquer produto num pedido. `Product.user_id` só registra quem criou o produto — não é usado para filtrar leitura nem escrita.
- O agente de IA (`agent/tools.py`) e o servidor MCP (`agent/mcp_server.py`) seguem a mesma regra: `list_products` é global; `list_orders` é escopado ao tenant do usuário autenticado (agente) ou do email informado (MCP).

## Funcionalidades

### Autenticação (`/auth`)

- `POST /auth/token` — login via OAuth2 Password Flow (usuário/senha), retorna um JWT Bearer token

### Usuários (`/users`)

- `POST /users/` — cria usuário (email único, senha com hash bcrypt)
- `GET /users/me` — retorna o próprio usuário autenticado (a partir do JWT)
- `GET /users/{email}` — busca usuário por email (autenticado, só o próprio usuário)

### Produtos (`/products`)

- `POST /products/` — cria produto (autenticado); registra `user_id` de quem criou, mas o produto é público
- `GET /products/` — lista **todos** os produtos, de qualquer usuário; **não exige autenticação**, limitado a 30 req/min por IP (`slowapi`)

### Pedidos (`/orders`)

- `POST /orders/` — cria pedido com um ou mais itens, vinculado ao usuário autenticado; os produtos referenciados podem ser de qualquer usuário (produtos são públicos)
- `GET /orders/` — lista pedidos do usuário autenticado
- `GET /orders/{order_id}` — busca um pedido específico do usuário autenticado

> Pedidos e usuários são escopados ao tenant (usuário) autenticado via JWT; produtos são públicos — ver [Multi-tenancy](#multi-tenancy).

### Agente de IA (`/agent`)

Agente conversacional (LangGraph + Gemini) que responde perguntas sobre **produtos** e **pedidos** usando os repositórios de leitura já existentes (`ProductViewRepo`, `OrderViewRepo`) como *tools*. Não acessa o banco diretamente nem inventa dados — só responde com base no que as tools retornam.

- `POST /agent/ask` — envia uma pergunta (`{"question": "..."}`) e recebe a resposta completa do agente (autenticado)
- `POST /agent/ask/stream` — mesma coisa, mas via SSE (`text/event-stream`), com o conteúdo chegando token a token conforme o modelo gera
- `GET /agent/history` — histórico de perguntas/respostas do usuário autenticado
- `DELETE /agent/history` — limpa o histórico do usuário autenticado

**Como funciona:**

- `agent/tools.py` — monta as tools por requisição (`build_tools(user_id)`). `list_products` lista produtos disponíveis (públicos); `list_orders` lista **apenas** os pedidos do usuário logado — o `user_id` vem do JWT, nunca é informado pela LLM, então não há como um usuário perguntar pelos pedidos de outro.
- `agent/llm.py` — define o modelo (`gemini-3.5-flash` via `ChatGoogleGenerativeAI`) e `build_agent(tools)`, que cria um agente ReAct (`langchain.agents.create_agent`) com as tools da requisição.
- `agent/utils.py` — persiste o histórico de conversa por usuário em `chat-history/{email}.json` (as últimas 50 interações; só as últimas 10 entram no contexto enviado à LLM).
- `agent/routes.py` — router FastAPI que junta tudo: recupera histórico, monta o agente, invoca (ou faz stream via `agent.astream_events`), salva a resposta.

Requer `GOOGLE_API_KEY` configurada no `.env` (veja `.env_example`) — sem ela a aplicação falha no startup (`ensure_configured()` em `agent/llm.py`, chamado no `lifespan`). As chamadas ao Gemini têm timeout de 30s e até 2 retries.

### Servidor MCP (`agent/mcp_server.py`)

Expõe `list_products` e `list_orders` como um servidor [MCP](https://modelcontextprotocol.io/) standalone (transporte stdio), para uso em clientes MCP como Claude Desktop — desacoplado do FastAPI/LangChain, e reaproveitando a mesma lógica de leitura (`ProductViewRepo`, `OrderViewRepo`) e formatação (`agent/formatting.py`) usada pelas tools do agente.

Rodar direto via stdio (para um cliente MCP real, como Claude Desktop):

```bash
uv run python -m agent.mcp_server
```

Diferença importante em relação a `/agent`: não existe JWT/sessão HTTP no MCP — o cliente chama a tool diretamente. `list_products` não precisa de usuário (produtos são públicos); `list_orders` recebe o email do usuário como parâmetro explícito, em vez de vir de um `current_user` autenticado. Isso é aceitável para uso local/confiável (um dev plugando seu próprio banco no seu próprio cliente MCP), mas **não é multi-tenant-safe por si só**: não exponha esse servidor em rede não confiável sem adicionar autenticação de verdade.

#### Testando com o MCP Inspector

O pacote `mcp[cli]` traz um inspector web interativo pra chamar as tools na mão, sem precisar de um cliente MCP completo.

1. Suba o Inspector (precisa de `node`/`npx` instalados):
   ```bash
   make mcp
   # ou: uv run mcp dev agent/mcp_server.py:mcp
   ```
   > `mcp dev`/`mcp run` carregam `agent/mcp_server.py` direto via `importlib`, sem adicionar a raiz do projeto no `sys.path` — por isso o próprio arquivo faz `sys.path.insert(0, ...)` no topo, senão `from agent.formatting import ...` falharia com `ModuleNotFoundError: No module named 'agent'`.
   >
   > Se aparecer erro de conexão ao clicar em **Connect** mencionando `uv` (não achou o binário), é porque o Inspector spawna processos filhos sem o `PATH` completo do seu shell — resolvido com `ln -sf ~/.local/bin/uv /opt/homebrew/bin/uv` (ou onde seu `uv` estiver, num diretório que já esteja no `PATH` padrão do sistema).
2. O terminal imprime uma URL tipo `http://127.0.0.1:6274/?MCP_INSPECTOR_API_TOKEN=...` — abre ela no browser (ou deixa abrir sozinho).
3. Clica em **Connect** no canto superior esquerdo; deve aparecer "Connected".
4. Aba **Tools** → **List Tools**: devem aparecer `list_products` e `list_orders`.
5. `list_products` → **Run Tool** (sem parâmetros) — retorna os produtos do `database.db` real (não o de teste).
6. `list_orders` → preenche `user_email` com um usuário existente no `database.db` → **Run Tool** — retorna os pedidos dele, ou `No user found ...` se o email não existir.
7. `Ctrl+C` no terminal encerra o Inspector.

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
make mcp     # sobe o servidor MCP com o Inspector web
make ruff    # lint + format com ruff
```

## Testes

```bash
uv run pytest -x --tb=short -q
```

Cobertura: auth, users, products, orders (incluindo escopo por usuário), o agente (`agent/llm.py`, `agent/tools.py`, `agent/utils.py`, `agent/routes.py`, com o LLM real mockado — os testes não chamam a API do Gemini) e o servidor MCP (`agent/mcp_server.py`). Cada execução usa um `database.db` e um `chat-history/` isolados em `tests/` (via env vars `DATABASE_URL`/`CHAT_HISTORY_DIR`), nunca os dados reais do projeto.
