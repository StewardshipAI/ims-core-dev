@echo off
REM IMS Docker Helper for Windows (PowerShell)

if "%1%"=="" goto help
if "%1%"=="start" goto start
if "%1%"=="stop" goto stop
if "%1%"=="clean" goto clean
if "%1%"=="logs" goto logs
if "%1%"=="test" goto test
if "%1%"=="populate" goto populate
if "%1%"=="ps" goto ps
if "%1%"=="help" goto help

:start
echo [*] Starting IMS containers...
docker-compose up -d
echo [+] Containers started!
echo.
echo Services:
echo   PostgreSQL: localhost:5432
echo   Redis: localhost:6379
echo   API: http://localhost:8000
echo   Swagger: http://localhost:8000/docs
echo.
docker-compose ps
goto end

:stop
echo [*] Stopping IMS containers...
docker-compose down
echo [+] Containers stopped!
goto end

:clean
echo [!] WARNING: This will delete ALL data!
set /p confirm="Are you sure? (y/N): "
if /i "%confirm%"=="y" (
    docker-compose down -v
    echo [+] All data removed!
) else (
    echo [-] Cancelled
)
goto end

:logs
if "%2%"=="" (
    docker-compose logs -f api
) else (
    docker-compose logs -f %2%
)
goto end

:test
echo [*] Running tests...
docker-compose run --rm api pytest tests/ -v
goto end

:populate
echo [*] Registering test models...
REM Extract admin key from .env
for /f "delims==" %%A in ('findstr /R "ADMIN_API_KEY" .env') do set %%A

REM Wait for API
echo [*] Waiting for API...
timeout /t 5

REM Register models using curl
echo [*] Registering: gpt-4-turbo
curl -X POST http://localhost:8000/api/v1/models/register ^
  -H "Content-Type: application/json" ^
  -H "X-Admin-Key: %ADMIN_API_KEY%" ^
  -d "{\"model_id\":\"gpt-4-turbo\",\"vendor_id\":\"OpenAI\",\"capability_tier\":\"Tier_1\",\"context_window\":128000,\"cost_in_per_mil\":10.0,\"cost_out_per_mil\":30.0,\"function_call_support\":true,\"is_active\":true}"

echo [+] Test data loaded!
goto end

:ps
docker-compose ps
goto end

:help
echo IMS Docker Helper for Windows
echo.
echo Usage: docker.cmd [COMMAND]
echo.
echo Commands:
echo   start       Start containers
echo   stop        Stop containers
echo   clean       Remove containers and data
echo   logs        View logs (default: api)
echo   test        Run tests
echo   populate    Load test models
echo   ps          Show container status
echo   help        Show this help
echo.
echo Examples:
echo   docker.cmd start
echo   docker.cmd logs api
echo   docker.cmd populate
goto end

:end
