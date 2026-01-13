# DbRevel SDKs

Official client SDKs for DbRevel - AI-powered database SDK that converts natural language into secure, optimized queries for any database.

## Available SDKs

### ✅ TypeScript/JavaScript

**Status:** Available
**Package:** [`@dbrevel/sdk`](https://www.npmjs.com/package/@dbrevel/sdk)
**Documentation:** [TypeScript SDK README](typescript/README.md)
**Examples:** [TypeScript SDK Examples](typescript/examples/README.md)

```bash
npm install @dbrevel/sdk
```

## Coming Soon

The following SDKs are planned for future releases:

- **Python** - `sdk/python/` (Coming Soon)
- **Go** - `sdk/go/` (Coming Soon)
- **Java** - `sdk/java/` (Coming Soon)
- **C# / .NET** - `sdk/csharp/` (Coming Soon)
- **Ruby** - `sdk/ruby/` (Coming Soon)
- **PHP** - `sdk/php/` (Coming Soon)
- **Rust** - `sdk/rust/` (Coming Soon)
- **Swift** - `sdk/swift/` (Coming Soon)
- **Kotlin** - `sdk/kotlin/` (Coming Soon)

## Using the REST API Directly

While official SDKs provide type safety, error handling, and convenience methods, you can always use the DbRevel REST API directly with any programming language. The API uses standard HTTP requests and JSON responses.

See the [API Testing Guide](../API_TESTING_GUIDE.md) for examples of using the API directly.

## SDK Structure

Each SDK follows a consistent structure:

```
sdk/
├── typescript/        # TypeScript SDK (available)
│   ├── src/          # Source code
│   ├── examples/     # Usage examples
│   ├── package.json  # NPM package configuration
│   └── README.md     # SDK-specific documentation
├── python/           # Python SDK (coming soon)
├── go/               # Go SDK (coming soon)
└── ...
```

## Contributing

Want to contribute an SDK for your favorite language? Check out our [contributing guidelines](../CONTRIBUTING.md) or open an issue to discuss.

## Support

- **Documentation:** [Main README](../README.md)
- **API Testing:** [API Testing Guide](../API_TESTING_GUIDE.md)
- **Issues:** [GitHub Issues](https://github.com/GodfreySam/dbrevel/issues)
