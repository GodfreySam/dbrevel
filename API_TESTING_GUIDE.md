# API Testing Guide

This comprehensive guide covers testing the DbRevel API, including authentication, multi-project support, and user workflows.

## 🎯 Quick Start

The API supports **automatic demo account fallback** - you can test immediately without any authentication!

### Test Without Authentication (Uses Demo Account)

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Get all users"}'
```

**What happens:**
- No `X-Project-Key` header provided
- API automatically uses demo project (`dbrevel_demo_project_key`)
- Query executes against pre-seeded demo database
- Returns results immediately

## 🔐 Authentication Overview

DbRevel supports two authentication methods depending on your use case:

### 1. JWT Token Authentication (User Dashboard)

Used for authenticated user operations (dashboard, profile management, projects).

```bash
# Login to get JWT token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your_password"
  }'

# Use token for authenticated requests
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <your_jwt_token>"
```

**When to use:**
- User dashboard access
- Profile management
- Project CRUD operations
- Password changes

### 2. X-Project-Key Header (API Integration)

Used for direct API queries with project API keys.

```bash
# Using project API key
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "X-Project-Key: your_project_api_key" \
  -d '{"intent": "Show products with price over 100"}'

# Using demo project API key
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "X-Project-Key: dbrevel_demo_project_key" \
  -d '{"intent": "Get all users"}'
```

**When to use:**
- Production API integration
- SDK usage
- Programmatic access
- CI/CD pipelines

## 📊 Demo Data Structure

The demo account includes pre-seeded sample data for testing:

### PostgreSQL Tables

1. **users**
   - `id` (integer, primary key)
   - `name` (text)
   - `email` (text, unique)
   - `city` (text)
   - `created_at` (timestamp)

2. **products**
   - `id` (integer, primary key)
   - `name` (text)
   - `price` (decimal)
   - `category` (text)
   - `stock` (integer)

3. **orders**
   - `id` (integer, primary key)
   - `user_id` (integer, foreign key → users.id)
   - `status` (text: 'pending', 'completed', 'cancelled')
   - `total_amount` (decimal)
   - `created_at` (timestamp)

4. **order_items**
   - `id` (integer, primary key)
   - `order_id` (integer, foreign key → orders.id)
   - `product_id` (integer, foreign key → products.id)
   - `quantity` (integer)
   - `price` (decimal)

### MongoDB Collections

1. **sessions**
   - `user_id` (integer)
   - `session_token` (string)
   - `expires_at` (datetime)
   - `ip_address` (string)

2. **reviews**
   - `product_id` (integer)
   - `user_id` (integer)
   - `rating` (integer, 1-5)
   - `comment` (string)
   - `created_at` (datetime)

## 🧪 Example Queries

### Simple Queries

```bash
# Get all users
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Get all users"}'

# Get users from Lagos
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Get all users from Lagos"}'

# Show products
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Show all products"}'
```

### Filtered Queries

```bash
# Products with price over 100
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Show products with price over 100"}'

# Orders by status
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Count orders by status"}'

# High-value orders
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Get orders with total amount greater than 500"}'
```

### Aggregations

```bash
# Total revenue by product
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Show total revenue by product category"}'

# User order counts
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Count orders per user"}'

# Average order value
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Calculate average order value"}'
```

### MongoDB Queries

```bash
# Get all reviews
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Get all reviews"}'

# Recent reviews
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Get recent reviews"}'

# High-rated reviews
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Show reviews with rating 5"}'
```

### Dry Run (See Query Without Executing)

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Get all users from Lagos",
    "dry_run": true
  }'
```

**Response includes:**
- Generated SQL/MongoDB query
- Query plan
- No actual data execution

## 👥 User Workflows

### Complete User Registration & Setup Flow

```bash
# 1. Register new user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePass123!",
    "name": "John Doe"
  }'

# 2. Verify email with OTP (check email for code)
curl -X POST "http://localhost:8000/api/v1/auth/verify-email" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "otp": "123456"
  }'

# 3. Login to get JWT token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePass123!"
  }'
# Response includes: access_token and user info

# 4. Get user profile
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <jwt_token>"

# 5. Update account database connections (optional)
curl -X PUT "http://localhost:8000/api/v1/accounts/connections" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "postgres_url": "postgresql://user:pass@host:5432/db",
    "mongodb_url": "mongodb://user:pass@host:27017/db"
  }'
```

### Password Reset Flow

```bash
# 1. Request password reset OTP
curl -X POST "http://localhost:8000/api/v1/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'

# 2. Reset password with OTP
curl -X POST "http://localhost:8000/api/v1/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp": "123456",
    "new_password": "NewSecurePass123!"
  }'
```

### Password Change (Authenticated)

```bash
curl -X POST "http://localhost:8000/api/v1/auth/change-password" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "OldPass123!",
    "new_password": "NewPass123!"
  }'
```

## 🚀 Multi-Project Management

### Project CRUD Operations

```bash
# 1. Create a new project
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production",
    "postgres_url": "postgresql://prod_user:pass@host:5432/prod_db",
    "mongodb_url": "mongodb://prod_user:pass@host:27017/prod_db"
  }'
# Response includes: project_id, api_key

# 2. List all projects
curl -X GET "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer <jwt_token>"

# 3. Get specific project
curl -X GET "http://localhost:8000/api/v1/projects/<project_id>" \
  -H "Authorization: Bearer <jwt_token>"

# 4. Update project
curl -X PATCH "http://localhost:8000/api/v1/projects/<project_id>" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production v2",
    "postgres_url": "postgresql://new_host:5432/db"
  }'

# 5. Rotate project API key
curl -X POST "http://localhost:8000/api/v1/projects/<project_id>/rotate-key" \
  -H "Authorization: Bearer <jwt_token>"
# Returns new API key, old key becomes invalid

# 6. Delete project
curl -X DELETE "http://localhost:8000/api/v1/projects/<project_id>" \
  -H "Authorization: Bearer <jwt_token>"
```

### Using Project API Keys for Queries

```bash
# Query using project-specific API key
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "X-Project-Key: <project_api_key>" \
  -d '{"intent": "Get all users"}'
```

**Benefits of Projects:**

- Separate dev/staging/prod environments
- Independent database connections per project
- Unique API keys for each environment
- Easy key rotation without affecting other projects

## 🌐 Frontend Testing Flow

### 1. Home Page (Public Demo)

**URL:** `http://localhost:5173/`

**Flow:**

1. User visits home page
2. Frontend uses `config.accountKey` (defaults to `dbrevel_demo_project_key`)
3. User enters natural language query
4. Frontend sends request with `X-Project-Key` header
5. Backend processes query against demo database
6. Results displayed to user

### 2. User Dashboard (Authenticated)

**URL:** `http://localhost:5173/dashboard`

**Flow:**

1. User logs in with email/password
2. Frontend receives JWT token and user info
3. Dashboard loads account info and projects
4. User can:
   - View/update database connections
   - Manage projects (create, edit, delete)
   - Change password
   - Execute queries against their databases
5. Queries use project API keys via `X-Project-Key` header

## 📝 Response Format

### Success Response

```json
{
  "data": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "city": "Lagos"
    }
  ],
  "metadata": {
    "query_plan": {
      "databases": ["postgres"],
      "queries": [
        {
          "database": "postgres",
          "query_type": "sql",
          "query": "SELECT * FROM users WHERE city = $1 LIMIT 1000",
          "parameters": ["Lagos"],
          "estimated_rows": 10,
          "collection": null
        }
      ]
    },
    "execution_time_ms": 45.2,
    "rows_returned": 10,
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-01-09T12:11:40.546703"
  }
}
```

### Error Response (401 - Missing Auth)

```json
{
  "detail": "Missing project API key. Provide X-Project-Key header or use demo project key: dbrevel_demo_project_key"
}
```

### Error Response (422 - Validation Error)

```json
{
  "detail": "Failed to parse Gemini response as JSON. Response: ..."
}
```

## 🔍 API Documentation

### Interactive Docs

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation.

**Features:**
- Try it out directly in browser
- See request/response schemas
- Test with demo project key
- View authentication options

### OpenAPI Schema

Access OpenAPI JSON schema at: `http://localhost:8000/openapi.json`

## 🚀 Comprehensive Testing Checklist

### Query API Testing

- [ ] Test query without `X-Project-Key` header (auto-demo)
- [ ] Test query with demo project key explicitly
- [ ] Test query with user's project API key
- [ ] Test dry run mode
- [ ] Test PostgreSQL queries
- [ ] Test MongoDB queries
- [ ] Test error handling (401, 422, 500)
- [ ] Verify demo data is accessible

### User Authentication Testing

- [ ] User registration flow
- [ ] Email verification with OTP
- [ ] User login (email/password)
- [ ] JWT token validation
- [ ] Password reset flow
- [ ] Password change (authenticated)
- [ ] Get user profile (`/auth/me`)

### Multi-Project Testing

- [ ] Create new project
- [ ] List user's projects
- [ ] Get specific project details
- [ ] Update project (name, database URLs)
- [ ] Rotate project API key
- [ ] Delete project
- [ ] Query using project API key
- [ ] Verify project isolation (separate databases)

### Frontend Testing

- [ ] Home page (public demo queries)
- [ ] User registration page
- [ ] Email verification page
- [ ] User login page
- [ ] User dashboard (authenticated)
- [ ] Project management UI
- [ ] Password reset flow
- [ ] Password change UI

## 🐛 Troubleshooting

### Authentication Issues

**"Missing project API key" Error**

- Add `X-Project-Key: dbrevel_demo_project_key` header, or
- Ensure demo account exists (auto-created on startup)

**"Invalid project API key" Error**

- Verify API key is correct
- For demo: `dbrevel_demo_project_key`
- For projects: Check project details in dashboard

**"Unauthorized" (401) Error**

- JWT token expired - login again
- Invalid JWT token - check Authorization header format

**Email OTP Not Received**

- Check email configuration in `.env`
- Verify EMAIL_ENABLED=true
- Check backend logs for OTP (if email disabled)
- Check spam folder

### Query Issues

**No Data Returned**

1. Verify demo data is seeded: `python backend/scripts/seed_demo_data.py`
2. Check database connections in backend logs
3. Verify account/project has correct database URLs
4. Try dry run mode to see generated query

**Query Validation Failed**

- Natural language intent may be unclear
- Try rephrasing the query
- Use dry run to see what query was generated
- Check database schema matches query

### Project Issues

**Project Creation Failed**

- Database URLs must be valid
- Check connection strings format
- Verify database credentials
- Test connection before saving

**Project API Key Not Working**

- Ensure project is active (`is_active: true`)
- Verify API key is correct (case-sensitive)
- Check project hasn't been deleted

### Frontend Issues

**Dashboard Not Loading**

1. Check JWT token in localStorage
2. Verify API URL in `config.ts`
3. Check browser console for errors
4. Verify CORS is configured correctly

## 📚 Next Steps

### For Developers

1. **Register & Setup:**
   - Create account at `/api/v1/auth/register`
   - Verify email with OTP
   - Login to get JWT token
   - Access dashboard

2. **Create Projects:**
   - Organize dev/staging/prod environments
   - Get unique API keys per project
   - Connect project-specific databases
   - Use project keys in SDK/API calls

3. **Integrate SDK:**
   - Install `@dbrevel/sdk` package
   - Configure with your project API key
   - Build your application!

## 🔗 Additional Resources

- **API Documentation:** `http://localhost:8000/docs`
- **OpenAPI Schema:** `http://localhost:8000/openapi.json`
- **SDK Docs:** [sdk/typescript/README.md](sdk/typescript/README.md)
- **Backend Setup:** [backend/README.md](backend/README.md)
- **Frontend Setup:** [frontend-react/README.md](frontend-react/README.md)
