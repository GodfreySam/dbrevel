@echo off
REM DbRevel Backend Startup Script for Windows
REM This script sets up a Python virtual environment and starts the FastAPI backend

echo ========================================
echo    DbRevel Backend Startup (Windows)
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found
    echo Please run this script from the backend\ directory
    pause
    exit /b 1
)

REM Check Python installation
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11 or higher from python.org
    pause
    exit /b 1
)
python --version
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [2/6] Creating virtual environment...
    python -m venv venv
    echo Virtual environment created
    echo.
) else (
    echo [2/6] Virtual environment already exists
    echo.
)

REM Activate virtual environment
echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat
echo Virtual environment activated
echo.

REM Upgrade pip
echo [4/6] Upgrading pip...
python -m pip install --upgrade pip -q
echo pip upgraded
echo.

REM Install dependencies
echo [5/6] Installing dependencies (this may take a minute)...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed
echo.

REM Check for .env file
echo [6/6] Checking configuration...
if not exist ".env" (
    echo [WARNING] .env file not found in current directory
    echo.
    echo Please copy .env.example to .env and add your GEMINI_API_KEY
    echo.
    REM Check if .env.example exists in current dir or parent dir
    if exist ".env.example" (
        set ENV_EXAMPLE=.env.example
    ) else if exist "..\\.env.example" (
        set ENV_EXAMPLE=..\\.env.example
    ) else (
        echo [ERROR] .env.example not found
        pause
        exit /b 1
    )
    set /p create_env="Would you like to create .env now? (y/n): "
    if /i "%create_env%"=="y" (
        copy "%ENV_EXAMPLE%" ".env"
        echo .env file created
        echo Please edit .env and add your GEMINI_API_KEY
        pause
        exit /b 0
    )
)

REM Load environment variables from .env file
if exist ".env" (
    echo Configuration file found
    echo Loading environment variables...

    REM Use PowerShell to safely parse .env file and set environment variables
    REM This handles special characters in values like URLs with colons, slashes, etc.
    powershell -NoProfile -Command "Get-Content '.env' | Where-Object { $_ -match '^\s*([^#=]+?)\s*=\s*(.*?)\s*$' } | ForEach-Object { $key = $matches[1].Trim(); $val = $matches[2].Trim() -replace '^[\"''](.*)[\"'']$', '$1'; if ($key) { [Environment]::SetEnvironmentVariable($key, $val, 'Process') } }"

    REM Check required environment variables
    if "%GEMINI_API_KEY%"=="" (
        echo [ERROR] GEMINI_API_KEY not set in .env
        pause
        exit /b 1
    )

    if "%POSTGRES_URL%"=="" (
        echo [WARNING] POSTGRES_URL not set, using default
        set POSTGRES_URL=postgresql://dev:dev@localhost:5432/dbreveldemo
    )

    if "%MONGODB_URL%"=="" (
        echo [WARNING] MONGODB_URL not set, using default
        set MONGODB_URL=mongodb://localhost:27017/dbreveldemo
    )

    echo Configuration loaded
    echo.
)

REM Start databases using Docker Compose
echo [7/7] Starting databases with Docker Compose...

REM Determine docker-compose command (support both standalone and plugin versions)
set DOCKER_COMPOSE_CMD=
docker-compose --version >nul 2>&1
if not errorlevel 1 (
    set DOCKER_COMPOSE_CMD=docker-compose
) else (
    docker compose version >nul 2>&1
    if not errorlevel 1 (
        set DOCKER_COMPOSE_CMD=docker compose
    )
)

if not "%DOCKER_COMPOSE_CMD%"=="" (
    REM Save current directory
    set CURRENT_DIR=%CD%

    REM Navigate to project root (parent directory from backend\)
    cd /d "%~dp0.."

    if exist "docker-compose.yml" (
        echo Found docker-compose.yml, starting services...
        %DOCKER_COMPOSE_CMD% up -d postgres mongodb redis >nul 2>&1
        if not errorlevel 1 (
            echo Docker Compose services started
            echo.
            REM Wait a moment for services to be ready
            timeout /t 2 /nobreak >nul
        ) else (
            echo [WARNING] Docker Compose command failed (services may already be running)
            echo.
        )
    ) else (
        echo [WARNING] docker-compose.yml not found in project root
        echo Skipping Docker Compose startup
        echo.
    )

    REM Return to backend directory
    cd /d "%CURRENT_DIR%"
) else (
    echo [WARNING] Docker Compose not found
    echo Make sure Docker is installed and docker-compose/docker compose is available
    echo Or start databases manually: docker-compose up -d postgres mongodb redis
    echo.
)

REM Database check reminder
echo ========================================
echo  Database Connection Reminders:
echo ========================================
echo - PostgreSQL should be running on localhost:5432
echo - MongoDB should be running on localhost:27017
echo - Redis should be running on localhost:6379
echo - Or use Docker: docker-compose up -d postgres mongodb redis
echo.

REM Start the server
echo ========================================
echo  Starting DbRevel API Server
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.
echo ----------------------------------------
echo  API:   http://localhost:8000
echo  Docs:  http://localhost:8000/docs
echo  ReDoc: http://localhost:8000/redoc
echo ----------------------------------------
echo.

REM Start uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

REM Deactivate on exit
call venv\Scripts\deactivate.bat
