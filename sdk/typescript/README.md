# DbRevel TypeScript SDK

TypeScript client SDK for DbRevel - AI-powered database SDK that converts natural language into secure, optimized queries for any database.

## Installation

```bash
npm install @dbrevel/sdk
```

## Quick Start

```typescript
import { DbRevelClient } from '@dbrevel/sdk';

const client = new DbRevelClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-project-api-key',
});

// Execute a natural language query
const result = await client.query("Get all users from Lagos");
console.log(result.data); // Array of results
console.log(result.metadata.execution_time_ms); // Execution time
```

## Features

- Natural language to database queries
- Type-safe responses with TypeScript generics
- Comprehensive error handling
- Schema introspection
- Health checks
- Request cancellation support
- Response validation
- Request/response interceptors
- Automatic retry with exponential backoff
- Logging interceptors
- Schema utilities and helper class

## API Reference

### `DbRevelClient`

Main client class for interacting with the DbRevel API.

#### Constructor

```typescript
new DbRevelClient(config: DbRevelConfig)
```

**Config:**
- `baseUrl` (string, required): API base URL
- `apiKey` (string, required): Project API key (sent as `X-Project-Key` header)
- `timeout` (number, optional): Request timeout in milliseconds (default: 30000)
- `retry` (RetryConfig, optional): Retry configuration for automatic retries

#### Methods

##### `query<T>(intent: string, options?: QueryOptions): Promise<QueryResult<T>>`

Execute a natural language database query.

```typescript
const result = await client.query<User>("Get all users");
```

**Options:**
- `dryRun` (boolean): Validate query without executing
- `context` (object): Additional context for query generation
- `signal` (AbortSignal): Cancel request signal

##### `getSchemas(): Promise<SchemasResponse>`

Get schemas for all connected databases.

```typescript
const schemas = await client.getSchemas();
console.log(schemas.databases.postgres.tables);
```

##### `getSchema(databaseName: string): Promise<DatabaseSchema>`

Get schema for a specific database.

```typescript
const schema = await client.getSchema("postgres");
```

##### `health(): Promise<HealthResponse>`

Check API and database connectivity.

```typescript
const health = await client.health();
console.log(health.status); // "healthy"
```

## Error Handling

The SDK provides specific error types for better error handling:

```typescript
import {
  DbRevelError,
  DbRevelTimeoutError,
  DbRevelAPIError,
  DbRevelValidationError,
  DbRevelNetworkError,
} from '@dbrevel/sdk';

try {
  await client.query("Get users");
} catch (error) {
  if (error instanceof DbRevelTimeoutError) {
    console.log('Request timed out');
  } else if (error instanceof DbRevelAPIError) {
    console.log(`API error: ${error.statusCode} - ${error.message}`);
  } else if (error instanceof DbRevelNetworkError) {
    console.log('Network error:', error.message);
  }
}
```

## TypeScript Types

All types are exported for use in your code:

```typescript
import type {
  QueryResult,
  QueryMetadata,
  QueryPlan,
  DatabaseSchema,
  SchemasResponse,
  HealthResponse,
} from '@dbrevel/sdk';
```

## Examples

### Basic Query

```typescript
const result = await client.query("Get all users from Lagos");
console.log(result.data);
```

### Dry Run (Validate Only)

```typescript
const result = await client.query("Get users", { dryRun: true });
console.log(result.metadata.query_plan);
```

### With Context

```typescript
const result = await client.query("Get user orders", {
  context: { userId: 123 }
});
```

### Request Cancellation

```typescript
const controller = new AbortController();
setTimeout(() => controller.abort(), 5000); // Cancel after 5s

try {
  await client.query("Get users", { signal: controller.signal });
} catch (error) {
  if (error instanceof DbRevelTimeoutError) {
    console.log('Request cancelled');
  }
}
```

### Schema Introspection

```typescript
// Get all schemas
const schemas = await client.getSchemas();

// Get specific database schema
const postgresSchema = await client.getSchema("postgres");
console.log(postgresSchema.tables);
```

### Health Check

```typescript
const health = await client.health();
if (health.status === 'healthy') {
  console.log('All databases connected:', Object.keys(health.databases));
}
```

### Schema Utilities

The SDK provides powerful utilities for working with database schemas:

```typescript
import { SchemaHelper } from '@dbrevel/sdk';

// Get schemas and create helper
const schemas = await client.getSchemas();
const helper = new SchemaHelper(schemas);

// Get database names
const dbNames = helper.getDatabaseNames();

// Get table names from a database
const tableNames = helper.getTableNames('postgres');

// Get column names from a table
const columnNames = helper.getColumnNames('postgres', 'users');

// Get table schema
const usersTable = helper.getTable('postgres', 'users');

// Get primary key columns
const primaryKeys = helper.getPrimaryKeyColumns('postgres', 'users');

// Get foreign key relationships
const relationships = helper.getTableRelationships('postgres', 'users');

// Find tables containing a specific column
const tablesWithEmail = helper.findTablesByColumn('email');

// Check if table exists
if (helper.hasTable('postgres', 'users')) {
  console.log('Users table exists');
}
```

**SchemaHelper Methods:**
- `getDatabaseNames()` - Get all database names
- `getDatabaseSchema(name)` - Get schema for a database
- `getTableNames(database)` - Get all table names
- `getCollectionNames(database)` - Get all collection names
- `getTable(database, table)` - Get table schema
- `getCollection(database, collection)` - Get collection schema
- `getColumnNames(database, table)` - Get column names
- `getColumn(database, table, column)` - Get column schema
- `hasTable(database, table)` - Check if table exists
- `hasCollection(database, collection)` - Check if collection exists
- `getPrimaryKeyColumns(database, table)` - Get primary key columns
- `getForeignKeyColumns(database, table)` - Get foreign key columns
- `getTableRelationships(database, table)` - Get table relationships
- `findTablesByColumn(columnName)` - Find tables with column
- `findCollectionsByField(fieldName)` - Find collections with field

### Interceptors

Interceptors allow you to modify requests, responses, and handle errors:

```typescript
import { createRequestLogger, createResponseLogger } from '@dbrevel/sdk';

// Add logging interceptors
client.useRequestInterceptor(createRequestLogger());
client.useResponseInterceptor(createResponseLogger());

// Custom request interceptor
client.useRequestInterceptor((config) => {
  // Add custom header
  return {
    ...config,
    headers: {
      ...config.headers,
      'X-Custom-Header': 'value',
    },
  };
});

// Custom error interceptor
client.useErrorInterceptor((error) => {
  console.error('Request failed:', error);
  // Optionally modify or rethrow error
  return error;
});
```

### Retry Logic

Enable automatic retries with exponential backoff:

```typescript
const client = new DbRevelClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-key',
  retry: {
    maxRetries: 3,
    retryDelay: 1000,        // Initial delay: 1s
    maxRetryDelay: 10000,     // Max delay: 10s
    backoffMultiplier: 2,     // Double delay each retry
    retryableStatusCodes: [500, 502, 503, 504],
    retryableErrorCodes: ['NETWORK_ERROR', 'TIMEOUT'],
  },
});

// Requests will automatically retry on network errors or 5xx status codes
const result = await client.query("Get users");
```

**Retry Configuration:**
- `maxRetries` (number, default: 3): Maximum retry attempts
- `retryDelay` (number, default: 1000): Initial delay in milliseconds
- `maxRetryDelay` (number, default: 10000): Maximum delay between retries
- `backoffMultiplier` (number, default: 2): Exponential backoff multiplier
- `retryableStatusCodes` (number[], default: [500, 502, 503, 504]): HTTP status codes that trigger retry
- `retryableErrorCodes` (string[], default: ['NETWORK_ERROR', 'TIMEOUT']): Error codes that trigger retry
- `shouldRetry` (function, optional): Custom function to determine if request should be retried

## Examples

See the [`examples/`](./examples/) directory for complete working examples:

- **Basic Query** - Simple query execution
- **Dry Run** - Validate queries without executing
- **Schema Introspection** - Explore database schemas
- **Error Handling** - Handle different error types
- **Interceptors** - Use request/response interceptors
- **Retry Logic** - Configure automatic retries
- **Typed Queries** - Type-safe query results

Run an example:
```bash
npx ts-node examples/basic-query.ts
```

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Run tests
npm test

# Watch mode
npm run dev
```

## License

MIT
