from typing import Dict, List, Optional
import json
from datetime import datetime, timedelta

class MessageHistory:
    def __init__(self, max_messages: int = 10):
        self.history: Dict[int, List[Dict]] = {}
        self.max_messages = max_messages
        self.last_cleared: Dict[int, datetime] = {}  # Track when history was last cleared

    def add_message(self, user_id: int, role: str, content: str):
        """Add a message to user's history"""
        if user_id not in self.history:
            self.history[user_id] = []
            
        self.history[user_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trim history if too long
        if len(self.history[user_id]) > self.max_messages:
            self.history[user_id] = self.history[user_id][-self.max_messages:]

    def get_history(self, user_id: int) -> List[Dict]:
        """Get user's message history"""
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.history.get(user_id, [])
        ]

    def clear_history(self, user_id: int):
        """Clear user's message history"""
        self.history[user_id] = []
        self.last_cleared[user_id] = datetime.now()

    def get_history_summary(self, user_id: int) -> dict:
        """Get summary of user's message history"""
        history = self.history.get(user_id, [])
        last_cleared = self.last_cleared.get(user_id)
        
        return {
            "message_count": len(history),
            "last_message": history[-1]["timestamp"] if history else None,
            "last_cleared": last_cleared.isoformat() if last_cleared else None
        }

    def export_history(self, user_id: int) -> str:
        """Export user's message history as JSON"""
        history = self.history.get(user_id, [])
        return json.dumps(history, indent=2, ensure_ascii=False)

    def clear_old_histories(self, days: int = 30):
        """Clear histories older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        for user_id in list(self.history.keys()):
            history = self.history[user_id]
            if not history:
                continue
                
            last_message_time = datetime.fromisoformat(history[-1]["timestamp"])
            if last_message_time < cutoff:
                self.clear_history(user_id)

class AIAssistantService:
    def __init__(self, api_endpoint: Optional[str] = None):
        self.api_endpoint = api_endpoint

    async def process_message(self, message: str) -> str:
        if not self.api_endpoint:
            raise ValueError("AI Assistant API endpoint not configured")
            
        # Implementation of API call to external assistant
        # This is a placeholder - actual implementation would depend on the API
        return "AI Assistant response" 

class GroupSettingsManager:
    def __init__(self):
        self.settings = {}  # chat_id -> settings dict
        
    def get_group_settings(self, chat_id: int) -> dict:
        """Get settings for a specific group"""
        if chat_id not in self.settings:
            self.settings[chat_id] = {
                "response_mode": "mentions",  # mentions, replies, all
                "user_rights": "all",        # all, admins, whitelist
                "whitelist": set(),          # set of user_ids
                "usage_limits": {
                    "messages": 100,         # messages per day
                    "images": 10,            # images per day
                    "voice": 20              # voice messages per day
                },
                "usage_count": {
                    "messages": 0,
                    "images": 0,
                    "voice": 0
                },
                "last_reset": None           # datetime of last usage reset
            }
        return self.settings[chat_id]
    
    def update_setting(self, chat_id: int, setting: str, value: any):
        """Update a specific setting for a group"""
        settings = self.get_group_settings(chat_id)
        if setting in settings:
            settings[setting] = value
            
    def check_user_permission(self, chat_id: int, user_id: int, is_admin: bool) -> bool:
        """Check if user has permission to use bot in group"""
        settings = self.get_group_settings(chat_id)
        
        if settings["user_rights"] == "all":
            return True
        elif settings["user_rights"] == "admins":
            return is_admin
        elif settings["user_rights"] == "whitelist":
            return user_id in settings["whitelist"]
        return False
    
    def check_usage_limit(self, chat_id: int, limit_type: str) -> bool:
        """Check if usage limit is reached"""
        settings = self.get_group_settings(chat_id)
        
        # Reset daily counts if needed
        if settings["last_reset"] is None:
            from datetime import datetime
            settings["last_reset"] = datetime.now()
            settings["usage_count"] = {k: 0 for k in settings["usage_count"]}
        else:
            from datetime import datetime, timedelta
            if datetime.now() - settings["last_reset"] > timedelta(days=1):
                settings["last_reset"] = datetime.now()
                settings["usage_count"] = {k: 0 for k in settings["usage_count"]}
        
        # Check limit
        return settings["usage_count"][limit_type] < settings["usage_limits"][limit_type]
    
    def increment_usage(self, chat_id: int, usage_type: str):
        """Increment usage counter"""
        settings = self.get_group_settings(chat_id)
        settings["usage_count"][usage_type] += 1