"""
Memory Management System for AI Agent
Handles persistent storage, retrieval, and learning from past experiences
"""

import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import asdict
import chromadb
from chromadb.config import Settings
import logging

from .core import Task, TaskStatus


class MemoryManager:
    """
    Manages agent memory including task history, learned patterns, and contextual information
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_path = config.get('url', 'sqlite:///agent_memory.db').replace('sqlite:///', '')
        self.logger = logging.getLogger('MemoryManager')
        
        # Initialize SQLite database
        self._init_database()
        
        # Initialize ChromaDB for semantic memory
        self.chroma_client = chromadb.Client(Settings(persist_directory="./chroma_db"))
        self.semantic_collection = self._get_or_create_collection("agent_memory")
        
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    priority INTEGER DEFAULT 1,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    result TEXT,
                    error TEXT,
                    parent_task_id TEXT,
                    subtasks TEXT
                )
            ''')
            
            # Execution steps table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS execution_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    step_data TEXT NOT NULL,
                    result TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id)
                )
            ''')
            
            # Learning patterns table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learned_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            ''')
            
            # System metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def _get_or_create_collection(self, name: str):
        """Get or create a ChromaDB collection"""
        try:
            return self.chroma_client.get_collection(name)
        except:
            return self.chroma_client.create_collection(name)
    
    async def store_task(self, task: Task):
        """Store a task in the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO tasks 
                (id, description, priority, status, created_at, started_at, completed_at, 
                 result, error, parent_task_id, subtasks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.id,
                task.description,
                task.priority,
                task.status.value,
                task.created_at,
                task.started_at,
                task.completed_at,
                json.dumps(task.result) if task.result else None,
                task.error,
                task.parent_task_id,
                json.dumps(task.subtasks) if task.subtasks else None
            ))
            conn.commit()
        
        # Store in semantic memory for similarity search
        await self._store_semantic_memory(task)
    
    async def update_task(self, task: Task):
        """Update an existing task"""
        await self.store_task(task)  # Same operation for SQLite
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_task(row)
        return None
    
    async def get_recent_tasks(self, limit: int = 10) -> List[Task]:
        """Get recent tasks"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM tasks 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            return [self._row_to_task(row) for row in cursor.fetchall()]
    
    async def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks by status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tasks WHERE status = ?', (status.value,))
            
            return [self._row_to_task(row) for row in cursor.fetchall()]
    
    async def store_execution_step(self, task_id: str, step_data: Dict[str, Any], result: Any):
        """Store an execution step for a task"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO execution_steps (task_id, step_data, result)
                VALUES (?, ?, ?)
            ''', (
                task_id,
                json.dumps(step_data),
                json.dumps(result) if result else None
            ))
            conn.commit()
    
    async def get_execution_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get execution history for a task"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM execution_steps 
                WHERE task_id = ? 
                ORDER BY timestamp
            ''', (task_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    async def store_learned_pattern(self, pattern_type: str, pattern_data: Dict[str, Any], confidence: float = 0.5):
        """Store a learned pattern for future use"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO learned_patterns (pattern_type, pattern_data, confidence)
                VALUES (?, ?, ?)
            ''', (pattern_type, json.dumps(pattern_data), confidence))
            conn.commit()
    
    async def get_learned_patterns(self, pattern_type: str = None, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """Retrieve learned patterns"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if pattern_type:
                cursor.execute('''
                    SELECT * FROM learned_patterns 
                    WHERE pattern_type = ? AND confidence >= ?
                    ORDER BY confidence DESC, usage_count DESC
                ''', (pattern_type, min_confidence))
            else:
                cursor.execute('''
                    SELECT * FROM learned_patterns 
                    WHERE confidence >= ?
                    ORDER BY confidence DESC, usage_count DESC
                ''', (min_confidence,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    async def find_similar_tasks(self, description: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar tasks using semantic search"""
        try:
            results = self.semantic_collection.query(
                query_texts=[description],
                n_results=limit
            )
            
            similar_tasks = []
            if results['ids'][0]:
                for i, task_id in enumerate(results['ids'][0]):
                    task = await self.get_task(task_id)
                    if task:
                        similar_tasks.append({
                            'task': task,
                            'similarity': 1 - results['distances'][0][i],  # Convert distance to similarity
                            'metadata': results['metadatas'][0][i] if results['metadatas'][0] else {}
                        })
            
            return similar_tasks
        except Exception as e:
            self.logger.warning(f"Error finding similar tasks: {e}")
            return []
    
    async def store_metric(self, metric_name: str, value: float):
        """Store a system metric"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO system_metrics (metric_name, metric_value)
                VALUES (?, ?)
            ''', (metric_name, value))
            conn.commit()
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Count tasks by status
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM tasks 
                GROUP BY status
            ''')
            task_counts = dict(cursor.fetchall())
            
            # Get total execution steps
            cursor.execute('SELECT COUNT(*) FROM execution_steps')
            execution_steps = cursor.fetchone()[0]
            
            # Get learned patterns count
            cursor.execute('SELECT COUNT(*) FROM learned_patterns')
            learned_patterns = cursor.fetchone()[0]
            
            # Get recent metrics
            cursor.execute('''
                SELECT metric_name, AVG(metric_value) as avg_value
                FROM system_metrics 
                WHERE timestamp > datetime('now', '-1 hour')
                GROUP BY metric_name
            ''')
            recent_metrics = dict(cursor.fetchall())
        
        return {
            'task_counts': task_counts,
            'execution_steps': execution_steps,
            'learned_patterns': learned_patterns,
            'recent_metrics': recent_metrics,
            'semantic_memory_count': self.semantic_collection.count()
        }
    
    async def _store_semantic_memory(self, task: Task):
        """Store task in semantic memory for similarity search"""
        try:
            self.semantic_collection.add(
                documents=[task.description],
                metadatas=[{
                    'status': task.status.value,
                    'priority': task.priority,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'completed': task.status == TaskStatus.COMPLETED
                }],
                ids=[task.id]
            )
        except Exception as e:
            self.logger.warning(f"Error storing semantic memory: {e}")
    
    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert database row to Task object"""
        from .core import Task, TaskStatus  # Import here to avoid circular import
        
        return Task(
            id=row['id'],
            description=row['description'],
            priority=row['priority'],
            status=TaskStatus(row['status']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            result=json.loads(row['result']) if row['result'] else None,
            error=row['error'],
            parent_task_id=row['parent_task_id'],
            subtasks=json.loads(row['subtasks']) if row['subtasks'] else []
        )