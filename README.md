# DbRevel - AI-Powered Universal Database SDK

**DBRevel is an AI-powered database SDK that converts natural language into secure, optimized queries for any database. Designed with scalability in mind, it supports multiple AI models and eliminates 60% of backend boilerplate—so developers can ship faster, startups can move leaner, and databases become accessible to everyone.**

## 🚀 Try It Live

**Experience DbRevel in action at [dbrevel.io](https://dbrevel.io)**

- ✨ Interactive demo with pre-loaded sample data
- 🎯 Test natural language queries in real-time
- 📊 Works with PostgreSQL and MongoDB
- 🔐 No setup required - start querying immediately

## What is DbRevel?

DbRevel is a multi-account SaaS platform and SDK that bridges the gap between natural language and databases:

- **Natural Language Processing** - Convert plain English to optimized SQL/MongoDB queries
- **Multi-Database Support** - PostgreSQL and MongoDB (more coming soon)
- **AI-Powered Intelligence** - Scalable architecture supporting multiple AI models for accurate query generation
- **Security First** - Query validation, RBAC, audit trails, and encryption
- **Multi-Account Architecture** - Isolated databases and API usage per account
- **Developer-Friendly SDKs** - Official TypeScript SDK with Python and Go coming soon

## 🎯 Key Features

-  **Natural Language Queries** - "Get all users from Lagos" → Optimized SQL/MongoDB
-  **Multi-Database Support** - PostgreSQL, MongoDB (MySQL, Redis coming soon)
-  **Security Built-in** - Query validation, RBAC, encryption, audit trails
-  **Multi-Account SaaS Ready** - Per-project databases and AI model usage tracking
-  **Project Management** - Organize dev/staging/prod environments
-  **Admin Dashboard** - Platform management with usage analytics
-  **TypeScript SDK** - Official SDK for seamless integration
-  **REST API** - Works with any programming language

## 📦 SDK & Integration

### TypeScript SDK

```bash
npm install @dbrevel/sdk
```

```typescript
import { DbRevelClient } from "@dbrevel/sdk";

const client = new DbRevelClient({
	apiKey: "your_project_api_key",
	baseURL: "https://api.dbrevel.io",
});

const result = await client.query({
	intent: "Get all users from Lagos",
});
```

### REST API

```bash
curl -X POST https://api.dbrevel.io/v1/query \
  -H "X-Project-Key: your_project_api_key" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Get all active users"}'
```

## Supported Languages

> The DbRevel API can be used from any language that can make HTTP requests. Official SDKs provide added convenience, type safety, and helpers.

| Language                |                                                           Official SDK | API Support          |
| ----------------------- | ---------------------------------------------------------------------: | :------------------- |
| TypeScript / JavaScript | Available — [@dbrevel/sdk](https://www.npmjs.com/package/@dbrevel/sdk) | ✓ Supported via REST |
| Python                  |                                                            Coming Soon | ✓ Supported via REST |
| Go                      |                                                            Coming Soon | ✓ Supported via REST |
| Java                    |                                                            Coming Soon | ✓ Supported via REST |
| C# / .NET               |                                                            Coming Soon | ✓ Supported via REST |
| Ruby                    |                                                            Coming Soon | ✓ Supported via REST |
| PHP                     |                                                            Coming Soon | ✓ Supported via REST |
| Rust                    |                                                            Coming Soon | ✓ Supported via REST |
| Swift                   |                                                            Coming Soon | ✓ Supported via REST |
| Kotlin                  |                                                            Coming Soon | ✓ Supported via REST |

If you'd like to contribute an SDK for a language listed as "Coming Soon", see [sdk/README.md](sdk/README.md) for guidelines.

## 📁 Project Structure

```
dbrevel/
├── backend/          # FastAPI multi-account backend
├── sdk/              # Client SDKs
│   └── typescript/   # TypeScript SDK (available now)
│   └── python/       # Python SDK (coming soon)
│   └── go/           # Go SDK (coming soon)
├── frontend-react/   # React SaaS dashboard
├── examples/         # Sample databases and schemas
└── LICENSE           # MIT License
```

## 📚 Documentation

### Getting Started

- **[API_TESTING_GUIDE.md](API_TESTING_GUIDE.md)** - Complete API guide with authentication and examples
- **[sdk/README.md](sdk/README.md)** - SDK overview and language support
- **[sdk/typescript/README.md](sdk/typescript/README.md)** - TypeScript SDK documentation
- **[sdk/typescript/examples/README.md](sdk/typescript/examples/README.md)** - SDK usage examples

### API Reference

- **Live API Docs**: [https://api.dbrevel.io/docs](https://api.dbrevel.io/docs) (Swagger UI)
- **OpenAPI Schema**: [https://api.dbrevel.io/openapi.json](https://api.dbrevel.io/openapi.json)

### Contributing

Interested in contributing? This is an open-source project under the MIT License. Check out the codebase to understand how it works, submit issues, or contribute improvements!

## 📝 License

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for the full license text.

### What MIT License Means

The MIT License is a permissive open source license.

**Requirements:**

- Include the original copyright notice and license text
- The software is provided "as is" without warranty

This license is ideal for hackathon submissions as it allows judges, organizers, and other participants to freely review, test, and learn from the code without legal barriers.

For more information, visit: https://opensource.org/licenses/MIT
