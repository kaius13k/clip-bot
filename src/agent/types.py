"""
Shared types and data structures for the AI Agent system
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Any, Optional


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: str
    description: str
    priority: int = 1
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    result: Any = None
    error: str = None
    parent_task_id: str = None
    subtasks: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.subtasks is None:
            self.subtasks = []