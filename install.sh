#!/bin/bash
# Toolkit-RAG Installer Script
# Standalone RAG system installer with multiple deployment options
# Version: 1.0.0
# Repository: https://github.com/ersantana361/toolkit-rag

set -e  # Exit on error
set -o pipefail  # Exit on pipe failure

# Script version
readonly SCRIPT_VERSION="1.0.0"

# Constants
readonly REQUIRED_SPACE_KB=204800  # 200MB for Docker images
readonly MIN_BASH_VERSION=4

# Colors for output
if [[ -t 1 ]] && [[ "$(tput colors 2>/dev/null)" -ge 8 ]]; then
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[1;33m'
    readonly RED='\033[0;31m'
    readonly BLUE='\033[0;34m'
    readonly NC='\033[0m' # No Color
else
    readonly GREEN=''
    readonly YELLOW=''
    readonly RED=''
    readonly BLUE=''
    readonly NC=''
fi

# Default settings
RAG_TYPE="local"
AUTO_START=false
FORCE=false
VERBOSE=false
DRY_RUN=false
UNINSTALL=false
UPDATE_SUBMODULES=true

# Deployment configuration
declare -A DEPLOYMENT_CONFIGS
DEPLOYMENT_CONFIGS[local]="docker-compose.yml"
DEPLOYMENT_CONFIGS[tei]="docker/docker-compose.tei.yml"
DEPLOYMENT_CONFIGS[openai]="docker/docker-compose.openai.yml"
DEPLOYMENT_CONFIGS[production]="docker/docker-compose.production.yml"

# Function: show_usage
show_usage() {
    echo "Toolkit-RAG Installer v$SCRIPT_VERSION"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deployment Options:"
    echo "  --type <type>           RAG deployment type: local, tei, openai, production (default: local)"
    echo "  --start                 Auto-start services after installation"
    echo "  --force                 Skip confirmation prompts"
    echo "  --verbose               Show detailed output"
    echo "  --dry-run               Preview changes without making them"
    echo ""
    echo "Management Options:"
    echo "  --uninstall             Stop and remove all RAG services"
    echo "  --update                Update to latest versions"
    echo "  --status                Check system status"
    echo "  --health                Run health checks"
    echo ""
    echo "Advanced Options:"
    echo "  --no-submodules         Skip git submodule updates"
    echo "  --openai-key <key>      Set OpenAI API key for openai deployment"
    echo "  --version               Show version information"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Deployment Types:"
    echo "  local                   PostgreSQL + Ollama (privacy-first, fully local)"
    echo "  tei                     PostgreSQL + Text Embeddings Inference (production-ready)"
    echo "  openai                  PostgreSQL + OpenAI API (cloud-powered quality)"
    echo "  production              PostgreSQL + enterprise configuration"
    echo ""
    echo "Examples:"
    echo "  $0                      # Install with local deployment (Ollama)"
    echo "  $0 --type tei --start   # Install TEI deployment and auto-start"
    echo "  $0 --type openai --openai-key sk-...  # Install with OpenAI"
    echo "  $0 --uninstall          # Remove all RAG services"
    echo "  $0 --status             # Check current status"
}

# Function: log messages
log() {
    echo -e "$1"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1" >&2
}

log_verbose() {
    if [[ "$VERBOSE" = true ]]; then
        log "${BLUE}[VERBOSE]${NC} $1"
    fi
}

# Function: check_prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check bash version
    local bash_major_version="${BASH_VERSION%%.*}"
    if [[ "$bash_major_version" -lt "$MIN_BASH_VERSION" ]]; then
        log_error "Bash version $MIN_BASH_VERSION.0 or higher required (current: $BASH_VERSION)"
        exit 1
    fi
    
    # Check required commands
    local missing_commands=()
    local required_commands=("docker" "git" "curl")
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [[ ${#missing_commands[@]} -gt 0 ]]; then
        log_error "Missing required commands: ${missing_commands[*]}"
        log_error "Please install the missing commands and try again."
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check docker compose
    if ! docker compose version >/dev/null 2>&1; then
        log_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    # Check disk space
    if [[ "$DRY_RUN" != true ]]; then
        local available_space=$(df -k . | awk 'NR==2 {print $4}' 2>/dev/null || echo "0")
        if [[ "$available_space" -lt "$REQUIRED_SPACE_KB" ]]; then
            log_warning "Low disk space. Need at least $((REQUIRED_SPACE_KB / 1024))MB free."
        fi
    fi
    
    log_success "Prerequisites check passed"
}

# Function: update_submodules
update_submodules() {
    if [[ "$UPDATE_SUBMODULES" = true ]]; then
        log_info "Updating git submodules..."
        if [[ "$DRY_RUN" = true ]]; then
            log_verbose "Would run: git submodule update --init --recursive"
        else
            if git submodule update --init --recursive; then
                log_success "Submodules updated successfully"
            else
                log_warning "Submodule update failed, continuing anyway"
            fi
        fi
    fi
}

# Function: setup_deployment
setup_deployment() {
    local deployment_type="$1"
    local compose_file="${DEPLOYMENT_CONFIGS[$deployment_type]}"
    
    if [[ -z "$compose_file" ]]; then
        log_error "Unknown deployment type: $deployment_type"
        exit 1
    fi
    
    if [[ ! -f "$compose_file" ]]; then
        log_error "Compose file not found: $compose_file"
        exit 1
    fi
    
    log_info "Setting up $deployment_type deployment..."
    log_verbose "Using compose file: $compose_file"
    
    # Handle OpenAI API key
    if [[ "$deployment_type" = "openai" ]]; then
        if [[ -z "$OPENAI_API_KEY" ]]; then
            log_error "OpenAI API key required for openai deployment"
            log_error "Set it with: --openai-key <key> or export OPENAI_API_KEY=<key>"
            exit 1
        fi
        export OPENAI_API_KEY
    fi
    
    # Start services
    if [[ "$DRY_RUN" = true ]]; then
        log_verbose "Would run: docker compose -f $compose_file up -d"
        return 0
    fi
    
    log_info "Starting Docker services..."
    if docker compose -f "$compose_file" up -d; then
        log_success "Services started successfully"
        
        # Wait for services to be ready
        log_info "Waiting for services to be ready..."
        local max_retries=12
        local retry_count=0
        
        while [[ $retry_count -lt $max_retries ]]; do
            if curl -f http://localhost:8000/health >/dev/null 2>&1; then
                log_success "RAG API is ready!"
                break
            fi
            
            retry_count=$((retry_count + 1))
            log_verbose "Waiting... (attempt $retry_count/$max_retries)"
            sleep 10
        done
        
        if [[ $retry_count -eq $max_retries ]]; then
            log_warning "Services may still be starting. Check status with: $0 --status"
        fi
        
        # Show service endpoints
        show_service_info "$deployment_type"
        
    else
        log_error "Failed to start services"
        exit 1
    fi
}

# Function: show_service_info
show_service_info() {
    local deployment_type="$1"
    
    echo ""
    log_success "Toolkit-RAG $deployment_type deployment ready!"
    echo ""
    echo "Services running:"
    echo "  🗄️  PostgreSQL: localhost:5432"
    echo "  🔗 RAG API: http://localhost:8000"
    
    case "$deployment_type" in
        "local")
            echo "  🧠 Ollama: http://localhost:11434"
            ;;
        "tei")
            echo "  🤗 TEI Embeddings: http://localhost:8080"
            ;;
        "openai")
            echo "  ☁️  OpenAI API: (external)"
            ;;
    esac
    
    echo ""
    echo "Quick start:"
    echo "  curl http://localhost:8000/health                    # Check health"
    echo "  curl http://localhost:8000/projects/myproject/stats  # Get stats"
    echo ""
    echo "Management:"
    echo "  $0 --status      # Check status"
    echo "  $0 --uninstall   # Remove services"
}

# Function: check_status
check_status() {
    log_info "Checking Toolkit-RAG system status..."
    
    # Check if any services are running
    local running_containers=$(docker ps --filter "name=toolkit-rag" --filter "name=superclaude" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null)
    
    if [[ -z "$running_containers" ]]; then
        log_warning "No Toolkit-RAG services are currently running"
        echo ""
        echo "To start services, run:"
        echo "  $0 --type local --start"
        return 1
    fi
    
    echo ""
    echo "🟢 Running Services:"
    echo "$running_containers"
    echo ""
    
    # Health checks
    log_info "Performing health checks..."
    
    local health_status=0
    
    # Check RAG API
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        log_success "✅ RAG API: healthy"
    else
        log_error "❌ RAG API: unhealthy"
        health_status=1
    fi
    
    # Check PostgreSQL
    if docker exec -it $(docker ps -q --filter "name=postgres") pg_isready >/dev/null 2>&1; then
        log_success "✅ PostgreSQL: healthy"
    else
        log_error "❌ PostgreSQL: unhealthy"
        health_status=1
    fi
    
    # Check Ollama (if local deployment)
    if curl -f http://localhost:11434/api/tags >/dev/null 2>&1; then
        log_success "✅ Ollama: healthy"
    elif docker ps --filter "name=ollama" --format "{{.Names}}" | grep -q ollama; then
        log_warning "⚠️  Ollama: starting"
    fi
    
    return $health_status
}

# Function: uninstall_services
uninstall_services() {
    log_info "Uninstalling Toolkit-RAG services..."
    
    if [[ "$FORCE" != true ]]; then
        echo ""
        log_warning "This will stop and remove all Toolkit-RAG Docker services and volumes."
        echo -n "Are you sure you want to continue? (y/N): "
        read -r confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            log_info "Uninstall cancelled"
            exit 0
        fi
    fi
    
    # Stop all related containers
    for compose_file in "${DEPLOYMENT_CONFIGS[@]}"; do
        if [[ -f "$compose_file" ]]; then
            log_verbose "Stopping services from $compose_file"
            if [[ "$DRY_RUN" = true ]]; then
                log_verbose "Would run: docker compose -f $compose_file down -v"
            else
                docker compose -f "$compose_file" down -v 2>/dev/null || true
            fi
        fi
    done
    
    # Clean up any remaining containers
    if [[ "$DRY_RUN" != true ]]; then
        docker container prune -f >/dev/null 2>&1 || true
        docker volume prune -f >/dev/null 2>&1 || true
    fi
    
    log_success "Toolkit-RAG services uninstalled successfully"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            if [[ -z "$2" ]] || [[ "$2" == --* ]]; then
                log_error "--type requires a deployment type"
                exit 1
            fi
            RAG_TYPE="$2"
            shift 2
            ;;
        --start)
            AUTO_START=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        --update)
            UPDATE_SUBMODULES=true
            shift
            ;;
        --status)
            check_status
            exit $?
            ;;
        --health)
            check_status
            exit $?
            ;;
        --no-submodules)
            UPDATE_SUBMODULES=false
            shift
            ;;
        --openai-key)
            if [[ -z "$2" ]] || [[ "$2" == --* ]]; then
                log_error "--openai-key requires an API key"
                exit 1
            fi
            OPENAI_API_KEY="$2"
            shift 2
            ;;
        --version)
            echo "Toolkit-RAG Installer v$SCRIPT_VERSION"
            exit 0
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate deployment type
if [[ -z "${DEPLOYMENT_CONFIGS[$RAG_TYPE]}" ]]; then
    log_error "Invalid deployment type: $RAG_TYPE"
    log_error "Valid types: ${!DEPLOYMENT_CONFIGS[*]}"
    exit 1
fi

# Main execution
echo ""
echo "🚀 Toolkit-RAG Installer v$SCRIPT_VERSION"
echo "========================================="
echo "Deployment type: $RAG_TYPE"
if [[ "$DRY_RUN" = true ]]; then
    echo "Mode: DRY RUN"
fi
echo ""

# Handle uninstall
if [[ "$UNINSTALL" = true ]]; then
    uninstall_services
    exit 0
fi

# Run installation
check_prerequisites
update_submodules

if [[ "$AUTO_START" = true ]] || [[ "$FORCE" = true ]]; then
    setup_deployment "$RAG_TYPE"
else
    echo ""
    log_info "Ready to install Toolkit-RAG with $RAG_TYPE deployment"
    echo -n "Continue? (y/N): "
    read -r confirm
    if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
        setup_deployment "$RAG_TYPE"
    else
        log_info "Installation cancelled"
        exit 0
    fi
fi

echo ""
log_success "🎉 Toolkit-RAG installation complete!"
echo ""
echo "Next steps:"
echo "  1. Check status: $0 --status"
echo "  2. Test the API: curl http://localhost:8000/health"
echo "  3. Use with your applications or SuperClaude integration"
echo ""
echo "For help: $0 --help"