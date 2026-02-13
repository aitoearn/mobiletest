from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
import json
import uuid


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    id: str
    role: MessageRole
    content: str
    timestamp: datetime = datetime.utcnow()
    metadata: Dict[str, Any] = {}


class Conversation(BaseModel):
    id: str
    title: str
    device_id: Optional[str] = None
    messages: List[Message] = []
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
    metadata: Dict[str, Any] = {}


class ConversationHistoryService:
    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}
        self._max_conversations = 1000
    
    def create_conversation(self, title: str = "新对话", device_id: Optional[str] = None) -> Conversation:
        conversation_id = str(uuid.uuid4())
        
        conversation = Conversation(
            id=conversation_id,
            title=title,
            device_id=device_id,
            messages=[],
        )
        
        self._conversations[conversation_id] = conversation
        self._cleanup_old_conversations()
        
        return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self._conversations.get(conversation_id)
    
    def list_conversations(
        self,
        device_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        conversations = list(self._conversations.values())
        
        if device_id:
            conversations = [c for c in conversations if c.device_id == device_id]
        
        conversations = sorted(
            conversations,
            key=lambda c: c.updated_at or datetime.min,
            reverse=True
        )
        
        return conversations[offset:offset + limit]
    
    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Message]:
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return None
        
        message_id = str(uuid.uuid4())
        message = Message(
            id=message_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        
        conversation.messages.append(message)
        conversation.updated_at = datetime.utcnow()
        
        if role == MessageRole.USER and len(conversation.messages) == 1:
            conversation.title = content[:50] + ("..." if len(content) > 50 else "")
        
        return message
    
    def update_message(
        self,
        conversation_id: str,
        message_id: str,
        content: str,
    ) -> Optional[Message]:
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return None
        
        for message in conversation.messages:
            if message.id == message_id:
                message.content = content
                conversation.updated_at = datetime.utcnow()
                return message
        
        return None
    
    def delete_message(self, conversation_id: str, message_id: str) -> bool:
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return False
        
        for i, message in enumerate(conversation.messages):
            if message.id == message_id:
                del conversation.messages[i]
                conversation.updated_at = datetime.utcnow()
                return True
        
        return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False
    
    def clear_conversations(self, device_id: Optional[str] = None):
        if device_id:
            self._conversations = {
                k: v for k, v in self._conversations.items()
                if v.device_id != device_id
            }
        else:
            self._conversations = {}
    
    def _cleanup_old_conversations(self):
        if len(self._conversations) > self._max_conversations:
            sorted_conversations = sorted(
                self._conversations.values(),
                key=lambda c: c.updated_at or datetime.min
            )
            
            to_delete = len(self._conversations) - self._max_conversations
            for conversation in sorted_conversations[:to_delete]:
                del self._conversations[conversation.id]
    
    def search_conversations(self, query: str) -> List[Conversation]:
        results = []
        query_lower = query.lower()
        
        for conversation in self._conversations.values():
            if query_lower in conversation.title.lower():
                results.append(conversation)
                continue
            
            for message in conversation.messages:
                if query_lower in message.content.lower():
                    results.append(conversation)
                    break
        
        return sorted(results, key=lambda c: c.updated_at or datetime.min, reverse=True)
    
    def export_conversation(self, conversation_id: str, format: str = "json") -> Optional[str]:
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return None
        
        if format == "json":
            return json.dumps({
                "id": conversation.id,
                "title": conversation.title,
                "device_id": conversation.device_id,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "messages": [
                    {
                        "id": m.id,
                        "role": m.role.value,
                        "content": m.content,
                        "timestamp": m.timestamp.isoformat(),
                        "metadata": m.metadata,
                    }
                    for m in conversation.messages
                ],
                "metadata": conversation.metadata,
            }, ensure_ascii=False, indent=2)
        
        return None


conversation_history_service = ConversationHistoryService()
