from dotenv import load_dotenv
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class ModelSettings:
    base_url: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 1000
    assistant_api_endpoint: Optional[str] = None

class Config:
    load_dotenv()
    
    # API Keys
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Default model settings
    TEXT_MODEL = ModelSettings(
        base_url="https://api.openai.com/v1",
        model_name="gpt-3.5-turbo"
    )
    
    IMAGE_MODEL = ModelSettings(
        base_url="https://api.openai.com/v1",
        model_name="dall-e-3"
    )
    
    VOICE_MODEL = ModelSettings(
        base_url="https://api.openai.com/v1",
        model_name="whisper-1"
    )
    
    # Available models for selection
    AVAILABLE_TEXT_MODELS = [
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4-turbo",
        "gpt-3.5-turbo-16k"
    ]
    
    # Menu options in Russian
    MENU_OPTIONS = {
        "settings": "Настройки",
        "clear_history": "Очистить историю",
        "help": "Помощь",
        "text_settings": "Настройки текстовой модели",
        "image_settings": "Настройки генерации изображений",
        "voice_settings": "Настройки голосовой модели",
        "back": "Назад",
        "save": "Сохранить",
        "image_size": "Размер изображения",
        "image_quality": "Качество изображения",
        "image_style": "Стиль изображения",
        "generate_image": "Сгенерировать изображение",
        "voice_model": "Голосовая модель",
        "voice_type": "Тип голоса",
        "voice_speed": "Скорость речи",
        "transcribe": "Транскрибировать",
        "speak": "Озвучить",
        "group_settings": "Настройки группы",
        "response_mode": "Режим ответов",
        "user_rights": "Права пользователей",
        "usage_limits": "Ограничения использования",
        "clear_confirm": "Подтвердить очистку",
        "clear_cancel": "Отмена",
        "export_history": "Экспорт истории",
        "history_summary": "Статистика сообщений"
    }
    
    # Voice settings
    AVAILABLE_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    AVAILABLE_VOICE_MODELS = {
        "transcription": ["whisper-1"],
        "tts": ["tts-1", "tts-1-hd"]
    }
    
    # Group chat settings
    GROUP_SETTINGS = {
        "response_modes": {
            "mentions": "Отвечать на упоминания",
            "replies": "Отвечать на ответы",
            "all": "Отвечать на все сообщения"
        },
        "user_rights": {
            "all": "Все пользователи",
            "admins": "Только администраторы",
            "whitelist": "Белый список"
        },
        "usage_limits": {
            "messages": "Лимит сообщений",
            "images": "Лимит изображений",
            "voice": "Лимит голосовых"
        }
    }
    
    # History settings
    HISTORY_SETTINGS = {
        "max_messages": 50,        # Maximum messages per user
        "auto_clear_days": 30,     # Auto-clear after 30 days
        "export_format": "json"    # Export format
    }