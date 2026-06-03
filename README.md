# B2B Voice Ordering Agent Backend

A robust FastAPI backend designed to power conversational AI voice agents (like Vapi) for wholesale B2B product ordering. This backend seamlessly handles business identification, fuzzy product search, strictly-validated cart building, unit conversions, and order placement.

## Features

- **Conversational Product Discovery:** Built-in recommendations (`/products/recommend`) that supports both top-level category exploration and specific item suggestions.
- **Intelligent Product Resolution:** Fuzzy matching and semantic unit conversion via the `/products/resolve` endpoint.
- **Cart Management:** Endpoints for instantly adding and removing items with built-in enforcement of minimum order quantities safely handled on the backend.
- **Hardened Validation:** Blocks actions without a validated `customer_id` and strictly rejects mathematical impossibilities (like fractional carton ordering).
- **VAPI Optimized:** Carefully engineered system prompt (`vapi_system_prompt.md`) ensuring zero filler words and 100% adherence to API JSON outcomes.

## Project Structure

```text
voice_agent_backend/
├── api/                  # FastAPI router endpoints (products, cart, customer, order)
├── core/                 # Database configuration (PostgreSQL/asyncpg) and Redis links
├── models/               # Pydantic schemas enforcing input/output validation
├── services/             # Core business logic containing the resolver and validation algorithms
├── scripts/              # Utility scripts for database initialization and testing
├── vapi_system_prompt.md # The strictly-tuned persona and instruction set for the Voice LLM
└── main.py               # Application entry point
```

## Setup Instructions

### 1. Prerequisites

- Python 3.10+
- PostgreSQL
- Redis (if session caching is implemented)

### 2. Environment Variables

Create a `.env` file in the root directory (or ensure your environment variables are exported) containing your database credentials:

```env
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=ai_voice_ordering_db
```

### 3. Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### 4. Database Setup

If you need to initialize or recreate the necessary tables (`customers`, `products`, etc.), run the setup script:

```bash
python scripts/recreate_db.py
```

### 5. Running the Development Server

Use the FastAPI CLI to start the development server:

```bash
fastapi dev main.py
```

The server will run on `http://127.0.0.1:8000`. API documentation is available automatically at `http://127.0.0.1:8000/docs`.

---

## API Endpoints Overview

### Customers

- **POST `/customer/identify`**: Validates a spoken business name and returns a `customer_id` for authorization.

### Products

- **GET `/products/recommend`**:
  - *No query arguments*: Returns a generic list of top-level categories.
  - *With `?query=x`*: Fuzzy searches the database and returns specific products matching the query.
- **GET `/products/{product_id}`**: Retrieves specific physical constraints and descriptions of a single item.
- **POST `/products/resolve`**: Deeply translates raw spoken strings (e.g. "half a kilo of green apples") into normalized backend configurations mapped to `product_id`.

### Cart

- **POST `/cart/add`**: Appends products enforcing database integer unit rules.
- **POST `/cart/remove`**: Deletes items from the session cart.
- **GET `/cart/summary`**: Recaps all items pending checkout.

### Orders

- **POST `/order/place`**: Finalizes the session cart and commits the transaction to the database.

---

## Vapi Integration (Voice Setup)

This backend is designed exclusively to be consumed by an LLM via tool-calling.

1. **System Prompt**: Copy the exact contents of `vapi_system_prompt.md` into your agent's system prompt configuration. It includes strict guardrails against over-explanation and filler phrases.
2. **Tools Configuration**: Configure each FastAPI route as a Custom Tool in your Vapi dashboard. Ensure all input/output fields match the exact schemas defined in the Swagger UI (`/docs`). For `/products/recommend`, explicitly ensure the `query` variable argument is set to **optional**.
