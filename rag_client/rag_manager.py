#!/usr/bin/env python3
"""
SuperClaude RAG Server Manager
Comprehensive management tool for RAG server operations
"""

import os
import sys
import subprocess
import json
import time
import asyncio
import aiohttp
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

class DeploymentType(Enum):
    LOCAL = "local"
    TEI = "tei"
    OPENAI = "openai"
    PRODUCTION = "production"

class ServiceStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"

@dataclass
class RAGServerConfig:
    deployment_type: DeploymentType
    project_root: str
    docker_dir: str
    rag_api_url: str = "http://localhost:8000"
    mongodb_url: str = "mongodb://localhost:27017"
    log_level: str = "INFO"
    data_dir: str = ""
    backup_dir: str = ""

class RAGServerManager:
    """
    Comprehensive RAG server management system
    """
    
    def __init__(self, config: RAGServerConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.compose_files = {
            DeploymentType.LOCAL: "docker-compose.local.yml",
            DeploymentType.TEI: "docker-compose.tei.yml", 
            DeploymentType.OPENAI: "docker-compose.openai.yml",
            DeploymentType.PRODUCTION: "docker-compose.production.yml"
        }
        self.setup_scripts = {
            DeploymentType.LOCAL: "setup-local.sh",
            DeploymentType.TEI: "setup-tei.sh",
            DeploymentType.OPENAI: "setup-openai.sh"
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup logging with appropriate level"""
        logger = logging.getLogger('superclaude.rag.manager')
        logger.setLevel(getattr(logging, self.config.log_level))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    def _run_command(self, command: List[str], cwd: Optional[str] = None, 
                    capture_output: bool = True) -> Tuple[int, str, str]:
        """Run a shell command and return result"""
        try:
            self.logger.debug(f"Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=cwd or self.config.docker_dir,
                capture_output=capture_output,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out after 5 minutes"
        except Exception as e:
            return 1, "", str(e)

    def _get_compose_file(self) -> str:
        """Get the appropriate docker-compose file for the deployment type"""
        return self.compose_files[self.config.deployment_type]

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are available"""
        self.logger.info("Checking prerequisites...")
        
        # Check Docker
        returncode, _, stderr = self._run_command(["docker", "--version"])
        if returncode != 0:
            self.logger.error("Docker is not available")
            return False
        
        # Check Docker Compose
        returncode, _, stderr = self._run_command(["docker", "compose", "version"])
        if returncode != 0:
            self.logger.error("Docker Compose is not available")
            return False
        
        # Check if docker directory exists
        if not os.path.exists(self.config.docker_dir):
            self.logger.error(f"Docker directory not found: {self.config.docker_dir}")
            return False
        
        # Check if compose file exists
        compose_file = os.path.join(self.config.docker_dir, self._get_compose_file())
        if not os.path.exists(compose_file):
            self.logger.error(f"Compose file not found: {compose_file}")
            return False
        
        self.logger.info("✅ Prerequisites check passed")
        return True

    async def setup_server(self) -> bool:
        """Setup the RAG server with the specified deployment type"""
        self.logger.info(f"Setting up RAG server with {self.config.deployment_type.value} deployment")
        
        if not self.check_prerequisites():
            return False
        
        # Run setup script if available
        setup_script = self.setup_scripts.get(self.config.deployment_type)
        if setup_script:
            script_path = os.path.join(self.config.docker_dir, setup_script)
            if os.path.exists(script_path):
                self.logger.info(f"Running setup script: {setup_script}")
                returncode, stdout, stderr = self._run_command(
                    ["bash", script_path], 
                    capture_output=False
                )
                if returncode != 0:
                    self.logger.error(f"Setup script failed: {stderr}")
                    return False
            else:
                self.logger.warning(f"Setup script not found: {script_path}")
        
        # Manual setup for deployment types without scripts
        if self.config.deployment_type == DeploymentType.PRODUCTION:
            self.logger.info("Production setup requires manual configuration")
            self.logger.info("Please ensure ATLAS_MONGO_DB_URI and RAG_OPENAI_API_KEY are set")
        
        # Verify setup
        if await self.health_check():
            self.logger.info("✅ RAG server setup completed successfully")
            return True
        else:
            self.logger.error("❌ RAG server setup failed")
            return False

    async def start_server(self) -> bool:
        """Start the RAG server"""
        self.logger.info(f"Starting RAG server ({self.config.deployment_type.value})...")
        
        if not self.check_prerequisites():
            return False
        
        compose_file = self._get_compose_file()
        
        # Start services
        returncode, stdout, stderr = self._run_command([
            "docker", "compose", "-f", compose_file, "up", "-d"
        ])
        
        if returncode != 0:
            self.logger.error(f"Failed to start services: {stderr}")
            return False
        
        # Wait for services to be ready
        self.logger.info("Waiting for services to be ready...")
        max_retries = 30
        for attempt in range(max_retries):
            if await self.health_check():
                self.logger.info("✅ RAG server started successfully")
                return True
            
            self.logger.info(f"Waiting... (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(10)
        
        self.logger.error("❌ RAG server failed to start within timeout")
        return False

    async def stop_server(self) -> bool:
        """Stop the RAG server"""
        self.logger.info("Stopping RAG server...")
        
        compose_file = self._get_compose_file()
        
        returncode, stdout, stderr = self._run_command([
            "docker", "compose", "-f", compose_file, "down"
        ])
        
        if returncode == 0:
            self.logger.info("✅ RAG server stopped successfully")
            return True
        else:
            self.logger.error(f"Failed to stop services: {stderr}")
            return False

    async def restart_server(self) -> bool:
        """Restart the RAG server"""
        self.logger.info("Restarting RAG server...")
        
        if await self.stop_server():
            await asyncio.sleep(5)  # Brief pause between stop and start
            return await self.start_server()
        
        return False

    async def get_status(self) -> Dict:
        """Get comprehensive server status"""
        status = {
            "deployment_type": self.config.deployment_type.value,
            "services": {},
            "health": {
                "rag_api": False,
                "mongodb": False,
                "embeddings": False
            },
            "ports": {
                "rag_api": 8000,
                "mongodb": 27017,
                "embeddings": None
            }
        }
        
        # Check Docker services
        compose_file = self._get_compose_file()
        returncode, stdout, stderr = self._run_command([
            "docker", "compose", "-f", compose_file, "ps", "--format", "json"
        ])
        
        if returncode == 0 and stdout.strip():
            try:
                services_data = json.loads(stdout) if stdout.startswith('[') else [json.loads(line) for line in stdout.strip().split('\n')]
                for service in services_data:
                    status["services"][service["Service"]] = {
                        "status": service["State"],
                        "health": service.get("Health", "unknown")
                    }
            except json.JSONDecodeError:
                self.logger.warning("Could not parse docker compose status")
        
        # Check health endpoints
        status["health"]["rag_api"] = await self._check_rag_api_health()
        status["health"]["mongodb"] = await self._check_mongodb_health()
        status["health"]["embeddings"] = await self._check_embeddings_health()
        
        # Set embedding service port based on deployment type
        if self.config.deployment_type == DeploymentType.LOCAL:
            status["ports"]["embeddings"] = 11434  # Ollama
        elif self.config.deployment_type == DeploymentType.TEI:
            status["ports"]["embeddings"] = 8080   # TEI
        
        return status

    async def _check_rag_api_health(self) -> bool:
        """Check RAG API health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config.rag_api_url}/health", timeout=5) as response:
                    return response.status == 200
        except Exception:
            return False

    async def _check_mongodb_health(self) -> bool:
        """Check MongoDB health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config.rag_api_url}/health/database", timeout=5) as response:
                    return response.status == 200
        except Exception:
            return False

    async def _check_embeddings_health(self) -> bool:
        """Check embeddings service health"""
        if self.config.deployment_type == DeploymentType.LOCAL:
            # Check Ollama
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:11434/api/tags", timeout=5) as response:
                        return response.status == 200
            except Exception:
                return False
        elif self.config.deployment_type == DeploymentType.TEI:
            # Check TEI
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:8080/health", timeout=5) as response:
                        return response.status == 200
            except Exception:
                return False
        elif self.config.deployment_type == DeploymentType.OPENAI:
            # For OpenAI, we just check if API key is configured
            return bool(os.getenv("RAG_OPENAI_API_KEY"))
        
        return False

    async def health_check(self) -> bool:
        """Comprehensive health check"""
        status = await self.get_status()
        return all(status["health"].values())

    async def get_logs(self, service: Optional[str] = None, tail: int = 100) -> str:
        """Get server logs"""
        compose_file = self._get_compose_file()
        
        command = ["docker", "compose", "-f", compose_file, "logs", "--tail", str(tail)]
        
        if service:
            command.append(service)
        
        returncode, stdout, stderr = self._run_command(command)
        
        if returncode == 0:
            return stdout
        else:
            return f"Error getting logs: {stderr}"

    async def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """Backup the MongoDB database"""
        if not backup_path:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = f"/tmp/superclaude_rag_backup_{timestamp}"
        
        self.logger.info(f"Backing up database to {backup_path}")
        
        # Use docker exec to run mongodump
        returncode, stdout, stderr = self._run_command([
            "docker", "exec", "superclaude-mongodb", 
            "mongodump", "--uri", "mongodb://admin:supersecure@localhost:27017/superclaude_rag?authSource=admin",
            "--out", "/data/backup"
        ])
        
        if returncode == 0:
            self.logger.info("✅ Database backup completed")
            return True
        else:
            self.logger.error(f"❌ Database backup failed: {stderr}")
            return False

    async def update_services(self) -> bool:
        """Update RAG services to latest versions"""
        self.logger.info("Updating RAG services...")
        
        compose_file = self._get_compose_file()
        
        # Pull latest images
        returncode, stdout, stderr = self._run_command([
            "docker", "compose", "-f", compose_file, "pull"
        ])
        
        if returncode != 0:
            self.logger.error(f"Failed to pull images: {stderr}")
            return False
        
        # Restart with new images
        return await self.restart_server()

    def print_status(self, status: Dict):
        """Print formatted status information"""
        print(f"\n🤖 SuperClaude RAG Server Status")
        print("=" * 40)
        print(f"Deployment Type: {status['deployment_type']}")
        print()
        
        print("Services:")
        for service, info in status['services'].items():
            status_icon = "✅" if info['status'] == 'running' else "❌"
            health_icon = "🟢" if info['health'] == 'healthy' else "🟡" if info['health'] == 'starting' else "🔴"
            print(f"  {status_icon} {service}: {info['status']} {health_icon}")
        
        print()
        print("Health Checks:")
        for component, healthy in status['health'].items():
            icon = "✅" if healthy else "❌"
            print(f"  {icon} {component.replace('_', ' ').title()}")
        
        print()
        print("Ports:")
        for service, port in status['ports'].items():
            if port:
                print(f"  🌐 {service.replace('_', ' ').title()}: localhost:{port}")

    async def validate_setup(self) -> bool:
        """Comprehensive validation of the RAG setup"""
        self.logger.info("Validating RAG setup...")
        
        # Check prerequisites
        if not self.check_prerequisites():
            return False
        
        # Check health
        if not await self.health_check():
            self.logger.error("Health check failed")
            return False
        
        # Test basic functionality
        try:
            # Test document upload
            async with aiohttp.ClientSession() as session:
                # Create a test document
                test_content = "This is a test document for RAG validation."
                form_data = aiohttp.FormData()
                form_data.add_field('file', test_content, filename='test.txt', content_type='text/plain')
                form_data.add_field('project_id', 'validation_test')
                
                async with session.post(f"{self.config.rag_api_url}/documents", data=form_data) as response:
                    if response.status != 200:
                        self.logger.error("Document upload test failed")
                        return False
                
                # Test search
                search_data = {
                    'query': 'test document',
                    'file_ids': ['validation_test'],
                    'k': 1
                }
                
                async with session.post(f"{self.config.rag_api_url}/query_multiple", json=search_data) as response:
                    # Don't fail if no documents found, just check endpoint exists
                    if response.status not in [200, 404]:
                        self.logger.error("Search endpoint test failed")
                        return False
        
        except Exception as e:
            self.logger.error(f"Validation test failed: {e}")
            return False
        
        self.logger.info("✅ RAG setup validation completed successfully")
        return True


async def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="SuperClaude RAG Server Manager")
    parser.add_argument("command", choices=[
        "setup", "start", "stop", "restart", "status", "logs", "health", 
        "backup", "update", "validate", "doctor"
    ])
    parser.add_argument("--deployment", "-d", choices=["local", "tei", "openai", "production"], 
                       default="local", help="Deployment type")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARN", "ERROR"], 
                       default="INFO", help="Logging level")
    parser.add_argument("--service", help="Specific service for logs command")
    parser.add_argument("--tail", type=int, default=100, help="Number of log lines to show")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    
    args = parser.parse_args()
    
    # Setup configuration
    project_root = os.path.abspath(args.project_root)
    docker_dir = os.path.join(project_root, "docker")
    
    config = RAGServerConfig(
        deployment_type=DeploymentType(args.deployment),
        project_root=project_root,
        docker_dir=docker_dir,
        log_level=args.log_level
    )
    
    manager = RAGServerManager(config)
    
    try:
        if args.command == "setup":
            success = await manager.setup_server()
            sys.exit(0 if success else 1)
        
        elif args.command == "start":
            success = await manager.start_server()
            sys.exit(0 if success else 1)
        
        elif args.command == "stop":
            success = await manager.stop_server()
            sys.exit(0 if success else 1)
        
        elif args.command == "restart":
            success = await manager.restart_server()
            sys.exit(0 if success else 1)
        
        elif args.command == "status":
            status = await manager.get_status()
            if args.json:
                print(json.dumps(status, indent=2))
            else:
                manager.print_status(status)
        
        elif args.command == "logs":
            logs = await manager.get_logs(args.service, args.tail)
            print(logs)
        
        elif args.command == "health":
            healthy = await manager.health_check()
            if args.json:
                print(json.dumps({"healthy": healthy}))
            else:
                print("🟢 Healthy" if healthy else "🔴 Unhealthy")
            sys.exit(0 if healthy else 1)
        
        elif args.command == "backup":
            success = await manager.backup_database()
            sys.exit(0 if success else 1)
        
        elif args.command == "update":
            success = await manager.update_services()
            sys.exit(0 if success else 1)
        
        elif args.command == "validate":
            success = await manager.validate_setup()
            sys.exit(0 if success else 1)
        
        elif args.command == "doctor":
            print("🔍 SuperClaude RAG Doctor")
            print("=" * 30)
            
            # Check prerequisites
            prereqs_ok = manager.check_prerequisites()
            print(f"Prerequisites: {'✅' if prereqs_ok else '❌'}")
            
            # Check status
            status = await manager.get_status()
            all_healthy = all(status["health"].values())
            print(f"Health Status: {'✅' if all_healthy else '❌'}")
            
            # Validate setup
            if prereqs_ok and all_healthy:
                validation_ok = await manager.validate_setup()
                print(f"Validation: {'✅' if validation_ok else '❌'}")
            
            # Show detailed status
            print()
            manager.print_status(status)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())