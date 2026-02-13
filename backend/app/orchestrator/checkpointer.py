from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import json
import sqlite3
import asyncio
from datetime import datetime


class BaseCheckpointer(ABC):
    @abstractmethod
    async def save(self, thread_id: str, state: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    async def load(self, thread_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def delete(self, thread_id: str) -> bool:
        pass


class MemoryCheckpointer(BaseCheckpointer):
    def __init__(self, max_size: int = 1000):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
    
    async def save(self, thread_id: str, state: Dict[str, Any]) -> bool:
        if len(self._store) >= self._max_size:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]
        
        self._store[thread_id] = {
            "state": state,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return True
    
    async def load(self, thread_id: str) -> Optional[Dict[str, Any]]:
        entry = self._store.get(thread_id)
        return entry["state"] if entry else None
    
    async def delete(self, thread_id: str) -> bool:
        if thread_id in self._store:
            del self._store[thread_id]
            return True
        return False


class SQLiteCheckpointer(BaseCheckpointer):
    def __init__(self, db_path: str = "checkpoints.db"):
        self._db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    async def save(self, thread_id: str, state: Dict[str, Any]) -> bool:
        def _save():
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO checkpoints (thread_id, state, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (thread_id, json.dumps(state)))
            conn.commit()
            conn.close()
            return True
        
        return await asyncio.get_event_loop().run_in_executor(None, _save)
    
    async def load(self, thread_id: str) -> Optional[Dict[str, Any]]:
        def _load():
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT state FROM checkpoints WHERE thread_id = ?", (thread_id,))
            row = cursor.fetchone()
            conn.close()
            return json.loads(row[0]) if row else None
        
        return await asyncio.get_event_loop().run_in_executor(None, _load)
    
    async def delete(self, thread_id: str) -> bool:
        def _delete():
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            return deleted
        
        return await asyncio.get_event_loop().run_in_executor(None, _delete)


class PostgresCheckpointer(BaseCheckpointer):
    def __init__(self, database_url: str):
        self._database_url = database_url
    
    async def _get_connection(self):
        try:
            import asyncpg
            return await asyncpg.connect(self._database_url)
        except Exception:
            return None
    
    async def save(self, thread_id: str, state: Dict[str, Any]) -> bool:
        conn = await self._get_connection()
        if not conn:
            return False
        
        try:
            await conn.execute("""
                INSERT INTO checkpoints (thread_id, state, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (thread_id) DO UPDATE SET state = $2, updated_at = NOW()
            """, thread_id, json.dumps(state))
            return True
        except Exception:
            return False
        finally:
            await conn.close()
    
    async def load(self, thread_id: str) -> Optional[Dict[str, Any]]:
        conn = await self._get_connection()
        if not conn:
            return None
        
        try:
            row = await conn.fetchrow(
                "SELECT state FROM checkpoints WHERE thread_id = $1",
                thread_id
            )
            return json.loads(row["state"]) if row else None
        except Exception:
            return None
        finally:
            await conn.close()
    
    async def delete(self, thread_id: str) -> bool:
        conn = await self._get_connection()
        if not conn:
            return False
        
        try:
            result = await conn.execute(
                "DELETE FROM checkpoints WHERE thread_id = $1",
                thread_id
            )
            return "DELETE" in result
        except Exception:
            return False
        finally:
            await conn.close()


def get_checkpointer(backend: str = "sqlite", **kwargs) -> BaseCheckpointer:
    if backend == "sqlite":
        return SQLiteCheckpointer(kwargs.get("db_path", "checkpoints.db"))
    elif backend == "postgres":
        return PostgresCheckpointer(kwargs.get("database_url", ""))
    else:
        return MemoryCheckpointer()


class CheckpointerWithFallback:
    def __init__(self, primary: BaseCheckpointer, fallback: BaseCheckpointer):
        self._primary = primary
        self._fallback = fallback
    
    async def save(self, thread_id: str, state: Dict[str, Any]) -> bool:
        try:
            result = await self._primary.save(thread_id, state)
            if result:
                return True
        except Exception:
            pass
        
        return await self._fallback.save(thread_id, state)
    
    async def load(self, thread_id: str) -> Optional[Dict[str, Any]]:
        try:
            state = await self._primary.load(thread_id)
            if state:
                return state
        except Exception:
            pass
        
        return await self._fallback.load(thread_id)
    
    async def delete(self, thread_id: str) -> bool:
        try:
            await self._primary.delete(thread_id)
        except Exception:
            pass
        
        return await self._fallback.delete(thread_id)
