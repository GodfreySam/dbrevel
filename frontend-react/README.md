# DbRevel React Frontend

Modern React frontend for DbRevel with proper environment variable support.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd frontend-react
npm install
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env.local

# Edit .env.local with your settings
# VITE_API_URL=http://localhost:8000/api/v1
# VITE_ACCOUNT_KEY=your_account_key
```

### 3. Run Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## 📦 Build for Production

```bash
npm run build
```

The built files will be in `dist/` directory.

## 🔧 Environment Variables

Vite exposes environment variables prefixed with `VITE_` via `import.meta.env`.

### Available Variables

- `VITE_API_URL` - API base URL (default: `http://localhost:8000/api/v1`)
- `VITE_ACCOUNT_KEY` - Account API key for SaaS mode (formerly VITE_TENANT_KEY)
- `VITE_TIMEOUT` - Request timeout in milliseconds (default: 30000)

### Environment Files

- `.env` - Default (committed to git)
- `.env.local` - Local overrides (gitignored)
- `.env.production` - Production overrides
- `.env.development` - Development overrides

## 🎯 Features

- ✅ React 18 with TypeScript
- ✅ Vite for fast development and builds
- ✅ Environment variable support
- ✅ Modern UI with CSS
- ✅ Type-safe API calls
- ✅ Error handling
- ✅ Loading states

## 📁 Project Structure

```
frontend-react/
├── src/
│   ├── App.tsx          # Main app component
│   ├── App.css          # App styles
│   ├── config.ts         # Configuration from env vars
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── .env.example         # Example environment file
├── vite.config.ts       # Vite configuration
└── package.json         # Dependencies
```

## 🚀 Why React?

This React frontend provides:

- ✅ Better developer experience
- ✅ Proper environment variable support
- ✅ Type safety with TypeScript
- ✅ Easier to extend with new features
- ✅ Production-ready build process
- ✅ Modern tooling (Vite, React 18)
