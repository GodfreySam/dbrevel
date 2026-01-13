# DbRevel SDK Examples

This directory contains example code demonstrating various features of the DbRevel SDK.

## Examples

### Basic Query (`basic-query.ts`)

Demonstrates how to execute a simple natural language query and access results.

```bash
npx ts-node examples/basic-query.ts
```

### Dry Run (`dry-run.ts`)

Shows how to validate queries without executing them.

```bash
npx ts-node examples/dry-run.ts
```

### Schema Introspection (`schema-introspection.ts`)

Explores database schemas using the SchemaHelper utility class.

```bash
npx ts-node examples/schema-introspection.ts
```

### Error Handling (`error-handling.ts`)

Demonstrates proper error handling for different error types.

```bash
npx ts-node examples/error-handling.ts
```

### Interceptors (`interceptors.ts`)

Shows how to use request, response, and error interceptors.

```bash
npx ts-node examples/interceptors.ts
```

### Retry Logic (`retry-logic.ts`)

Configures automatic retries with exponential backoff.

```bash
npx ts-node examples/retry-logic.ts
```

### Typed Queries (`typed-queries.ts`)

Uses TypeScript generics for type-safe query results.

```bash
npx ts-node examples/typed-queries.ts
```

## Prerequisites

1. Install dependencies:

```bash
npm install
```

2. Build the SDK:

```bash
npm run build
```

3. Update the examples with your API URL and project API key:

- Replace `http://localhost:8000` with your API base URL
- Replace `your-project-api-key` with your actual project API key

## Running Examples

You can run examples using `ts-node`:

```bash
# Install ts-node if not already installed
npm install -g ts-node

# Run an example
npx ts-node examples/basic-query.ts
```

Or compile and run:

```bash
# Compile TypeScript
npx tsc examples/basic-query.ts --outDir dist/examples --esModuleInterop

# Run compiled JavaScript
node dist/examples/basic-query.js
```

## Notes

- Make sure your DbRevel API is running and accessible
- Update API URLs and API keys in each example file
- Some examples require specific database schemas to work properly
