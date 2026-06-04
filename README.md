# B2B Voice Ordering Agent Backend

A robust FastAPI backend designed to power conversational AI voice agents (like Vapi) for wholesale B2B product ordering. This backend seamlessly handles business identification, fuzzy product search, strictly-validated cart building, unit conversions, and order placement. It operates on a lightweight, fast local SQLite database.

## Features

- **Conversational Product Discovery:** Built-in recommendations (`/products/recommend`) that supports both top-level category exploration and specific item suggestions.
- **Intelligent Product Resolution:** Fuzzy matching and semantic unit conversion via the `/products/resolve` endpoint, complete with quantity validation limits and inline LLM clarification notes.
- **Cart Management:** Endpoints for instantly adding and removing items with built-in enforcement of minimum order quantities safely handled on the backend.
- **Hardened Validation:** Blocks actions without a validated `customer_id` and strictly rejects mathematical impossibilities (like fractional carton ordering).
- **VAPI Optimized:** Carefully engineered system prompt (`vapi_system_prompt.md`) ensuring zero filler words and 100% adherence to API JSON outcomes.

## Project Structure

```text
voice_agent_backend/
├── api/                  # FastAPI router endpoints (products, cart, customer, order)
├── core/                 # Database configuration (aiosqlite) and Redis links
├── data/                 # SQLite database file and JSON seed payloads
├── frontend/             # Frontend client assets
├── logs/                 # Runtime logs for the server and installation
├── models/               # Pydantic schemas enforcing input/output validation
├── scripts/              # Utility scripts for database initialization and local data sync
├── services/             # Core business logic containing the resolver and validation algorithms
├── tests/                # Testing scripts
├── vapi_system_prompt.md # The strictly-tuned persona and instruction set for the Voice LLM
└── main.py               # Application entry point
```

## Setup Instructions

### 1. Prerequisites

- Python 3.10+
- Redis (runs in the background for session caching and active carts)

### 2. Environment Variables

Create a `.env` file in the root directory (or ensure your environment variables are exported):

```env
DATABASE_PATH=./data/voice_agent.db

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

### 3. Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### 4. Database Setup

To initialize the necessary tables (`customers`, `products`, etc.) using SQLite, run the schema recreation script:

```bash
python scripts/recreate_db.py
```

Then, populate the database with product and customer records from the local JSON files:

```bash
python scripts/sync_local.py
```

### 5. Running the API Server

Use the FastAPI CLI (which now runs under standard Uvicorn commands) to start the server:

```bash
fastapi run main.py --host 0.0.0.0
```

*(For local development with reloading, use `fastapi dev main.py`)*

The server will be available at `http://localhost:8000`. API documentation is generated automatically at `http://localhost:8000/docs`.

---

## API Endpoints Overview

### Customers

- **POST `/customer/identify`**: Validates a spoken business name and returns a `customer_id` for authorization.

### Products

- **GET `/products/recommend`**: Returns general product categories or specific items based on queries.
- **GET `/products/{product_id}`**: Retrieves specific details for an item.
- **POST `/products/resolve`**: Deeply translates raw spoken strings (e.g., "3.3 kilos of roasted vegetables") into normalized configurations, identifies ambiguities, and enforces `min_order_qty` directly before the cart stage.

### Cart

- **POST `/cart/add`**: Appends products enforcing database integer unit rules.
- **POST `/cart/remove`**: Deletes items from the session cart via Redis.
- **GET `/cart/summary`**: Recaps all items pending checkout.

### Orders

- **POST `/order/place`**: Finalizes the session cart and places the order.

---

## Vapi Integration (Voice Setup)

This backend is designed exclusively to be consumed by an LLM via tool-calling.

1. **System Prompt**: Copy the exact contents of `vapi_system_prompt.md` into your agent's system prompt configuration. It includes strict guardrails handling clarification logic safely.
2. **Tools Configuration**: Configure each FastAPI route as a Custom Tool in your Vapi dashboard. Ensure all input/output fields match the exact schemas defined in the Swagger UI (`/docs`). For `/products/recommend`, explicitly ensure the `query` variable argument is set to **optional**.
