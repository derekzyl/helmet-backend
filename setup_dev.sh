#!/bin/bash

# Development setup script for 2 vCPU + 4GB RAM server using uv
set -e

echo "🚀 Setting up development environment for 2 vCPU + 4GB RAM server..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed. Please install uv first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

print_success "uv is installed: $(uv --version)"

# Check system resources
print_status "Checking system resources..."
TOTAL_MEMORY=$(free -m | awk 'NR==2{printf "%.1f", $2/1024}')
CPU_CORES=$(nproc)

print_status "System specs: ${CPU_CORES} CPU cores, ${TOTAL_MEMORY}GB RAM"

if (( $(echo "$TOTAL_MEMORY < 3.5" | bc -l) )); then
    print_warning "System has less than 3.5GB RAM. Performance may be limited."
fi

# Create virtual environment
print_status "Creating virtual environment with uv..."
uv venv --python 3.11

# Activate virtual environment
print_status "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
print_status "Installing dependencies with uv..."
uv pip install -e .

# Install development dependencies
print_status "Installing development dependencies..."
uv pip install -e ".[dev]"

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs uploads

# Set proper permissions
chmod 755 logs uploads

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating template..."
    cat > .env << EOF
# Environment Configuration
ENVIRONMENT=development
DEBUG=true

# Database Configuration
DATABASE_URL=postgresql://pharmacy_user:pharmacy_pass@localhost:5432/pharmacy_db
POSTGRES_DB=pharmacy_db
POSTGRES_USER=pharmacy_user
POSTGRES_PASSWORD=pharmacy_pass

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Security
SECRET_KEY=dev-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server Configuration
WORKERS=2
MEMORY_LIMIT=3GB
CPU_LIMIT=2

# Email Configuration (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_TLS=true

# File Upload
MAX_FILE_SIZE=10485760
UPLOAD_DIR=uploads

# Monitoring
ENABLE_MONITORING=true
METRICS_INTERVAL=30
EOF
    print_warning "Please edit .env file with your actual configuration."
fi

# Run database migrations (if database is available)
print_status "Checking database connection..."
if command -v psql &> /dev/null; then
    if psql -h localhost -U pharmacy_user -d pharmacy_db -c "SELECT 1;" &> /dev/null; then
        print_status "Running database migrations..."
        alembic upgrade head
        print_success "Database migrations completed"
    else
        print_warning "Database not available. Please set up PostgreSQL first."
    fi
else
    print_warning "PostgreSQL client not found. Please install PostgreSQL first."
fi

# Run tests
print_status "Running tests..."
if uv run pytest --version &> /dev/null; then
    uv run pytest tests/ -v || print_warning "Some tests failed"
else
    print_warning "Tests not available. Please create test files first."
fi

# Show setup summary
print_success "Development environment setup completed!"
echo ""
echo "📊 Setup Summary:"
echo "  - Python version: $(python --version)"
echo "  - uv version: $(uv --version)"
echo "  - Virtual environment: .venv"
echo "  - Dependencies: Installed with uv"
echo "  - Configuration: .env file created"
echo ""
echo "🔧 Development Commands:"
echo "  - Activate environment: source .venv/bin/activate"
echo "  - Run server: uv run python app/main_optimized.py"
echo "  - Run tests: uv run pytest"
echo "  - Install new package: uv pip install package_name"
echo "  - Update dependencies: uv pip install -e ."
echo ""
echo "📈 Performance Tips:"
echo "  - Monitor memory usage: htop or top"
echo "  - Check logs: tail -f logs/optimized_app.log"
echo "  - Health check: curl http://localhost:8000/health"
echo "  - Metrics: curl http://localhost:8000/metrics"
echo ""
echo "🎉 Your optimized development environment is ready!"
