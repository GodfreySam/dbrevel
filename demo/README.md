# DbRevel Demo Examples

This folder contains simple Node.js examples demonstrating how to use DbRevel with both the SDK and direct API calls.

## Setup

1. **Install dependencies:**

   ```bash
   npm install
   ```

2. **Configure your environment:**

   ```bash
   cp .env.example .env
   ```

   Then edit `.env` and set:
   - `DBREVEL_BASE_URL` - Your DbRevel API URL (default: `https://api.dbrevel.io` for production, or `http://localhost:8000` for local development)
   - `DBREVEL_API_KEY` - Your project API key (get from dashboard)

   For quick testing, you can use the demo project key: `dbrevel_demo_project_key`

## Examples

### 1. SDK Example (`sdk-example.js`)

Demonstrates using the `@dbrevel/sdk` package for type-safe, convenient querying.

**Run it:**

```bash
npm run sdk
# or
node sdk-example.js
```

**What it does:**

- Initializes the DbRevel client with your API key
- Executes a natural language query: "Get all users"
- Displays results, execution time, and generated SQL/MongoDB query

### 2. Direct API Fetch Example (`api-fetch-example.js`)

Demonstrates using the DbRevel REST API directly with `fetch()`.

**Run it:**

```bash
npm run api
# or
node api-fetch-example.js
```

**What it does:**

- Makes a direct HTTP POST request to `/api/v1/query`
- Sends the query intent in JSON format
- Uses `X-Project-Key` header for authentication
- Parses and displays the response

### Run Both Examples

```bash
npm run all
```

## Customizing Queries

Edit either file to try different queries:

```javascript
// Try these queries:
"Get customers in Lagos with more than 5 orders";
"Show products with price over 100";
"Count orders by status";
"Get recent reviews";
"List all users sorted by created date";
```

## API Endpoint Details

**Endpoint:** `POST /api/v1/query`

**Headers:**

- `Content-Type: application/json`
- `X-Project-Key: your-project-api-key`

**Request Body:**

```json
{
	"intent": "Get all users",
	"context": null,
	"dry_run": false
}
```

**Response:**

```json
{
  "data": [...],
  "metadata": {
    "rows_returned": 10,
    "execution_time_ms": 234,
    "trace_id": "uuid",
    "query_plan": {
      "queries": [...]
    }
  }
}
```

## Troubleshooting

**Error: "Cannot find module '@dbrevel/sdk'"**

- Make sure you ran `npm install`
- If the SDK isn't published yet, you can use the direct API example instead

**Error: "API Error (401)"**

- Check your `DBREVEL_API_KEY` in `.env`
- Make sure the API key matches your project in the dashboard

**Error: "Connection refused"**

- Make sure your DbRevel backend is running
- Check `DBREVEL_BASE_URL` matches your backend URL

**Error: "No data returned"**

- Make sure your database has data
- Try the demo project key: `dbrevel_demo_project_key`
- Check that your database connections are configured in the dashboard
