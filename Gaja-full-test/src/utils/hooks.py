"""Hooks dla działań systemu testowego (restart, maintenance)."""

import asyncio
import subprocess
import time
from typing import Dict, Any, Optional

from loguru import logger


class SystemHooks:
    """Hooks dla działań systemowych."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.gaja_base_url = config.get("gaja", {}).get("base_url", "http://localhost:8001")
    
    async def restart_gaja(self) -> Dict[str, Any]:
        """Restartuje serwer GAJA przez Docker."""
        try:
            logger.info("🔄 Restarting GAJA server...")
            
            # Zatrzymaj kontener
            result = subprocess.run(
                ["docker", "restart", "gaja-server"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to restart GAJA: {result.stderr}")
                return {"success": False, "error": result.stderr}
            
            # Poczekaj chwilę na start
            await asyncio.sleep(5)
            
            # Sprawdź health check
            health_ok = await self._wait_for_health()
            
            if health_ok:
                logger.info("✅ GAJA server restarted successfully")
                return {"success": True, "action": "service_restarted"}
            else:
                logger.error("❌ GAJA server failed health check after restart")
                return {"success": False, "error": "Health check failed"}
                
        except subprocess.TimeoutExpired:
            logger.error("Restart command timed out")
            return {"success": False, "error": "Restart timeout"}
        except Exception as e:
            logger.error(f"Restart failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _wait_for_health(self, max_attempts: int = 12, delay: float = 5.0) -> bool:
        """Czeka na pozytywny health check."""
        import httpx
        
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.gaja_base_url}/health", timeout=10.0)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "healthy":
                            return True
                
            except Exception as e:
                logger.debug(f"Health check attempt {attempt + 1} failed: {e}")
            
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)
        
        return False
    
    async def clear_gaja_cache(self) -> Dict[str, Any]:
        """Czyści cache GAJA."""
        try:
            # Sprawdź czy istnieje endpoint do czyszczenia cache
            # Na razie placeholder
            logger.info("🧹 Clearing GAJA cache...")
            
            # Tutaj można dodać wywołanie API endpoint do czyszczenia cache
            # lub bezpośrednie działanie na plikach cache
            
            await asyncio.sleep(1)  # Symulacja
            
            return {"success": True, "action": "cache_cleared"}
            
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def backup_gaja_data(self) -> Dict[str, Any]:
        """Tworzy backup danych GAJA."""
        try:
            logger.info("💾 Backing up GAJA data...")
            
            # Backup bazy danych
            timestamp = int(time.time())
            backup_name = f"gaja_backup_{timestamp}"
            
            # Docker exec do skopiowania bazy
            result = subprocess.run([
                "docker", "exec", "gaja-server",
                "cp", "/app/server_data.db", f"/app/data/{backup_name}.db"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"✅ Data backup created: {backup_name}.db")
                return {"success": True, "action": "data_backed_up", "backup_name": backup_name}
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
                
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Sprawdza zasoby systemowe."""
        try:
            # Sprawdź użycie CPU i RAM kontenera
            result = subprocess.run([
                "docker", "stats", "gaja-server", "--no-stream", "--format",
                "table {{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:  # Skip header
                    stats = lines[1].split(",")
                    if len(stats) >= 3:
                        return {
                            "success": True,
                            "cpu_percent": stats[0].strip(),
                            "memory_usage": stats[1].strip(),
                            "memory_percent": stats[2].strip()
                        }
            
            return {"success": False, "error": "Could not parse stats"}
            
        except Exception as e:
            logger.error(f"Resource check failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_action(self, action: str) -> Dict[str, Any]:
        """Wykonuje akcję systemową."""
        actions_map = {
            "restart_gaja": self.restart_gaja,
            "clear_cache": self.clear_gaja_cache,
            "backup_data": self.backup_gaja_data,
            "check_resources": self.check_system_resources
        }
        
        if action not in actions_map:
            return {"success": False, "error": f"Unknown action: {action}"}
        
        return await actions_map[action]()
