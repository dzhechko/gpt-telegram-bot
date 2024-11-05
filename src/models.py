from openai import AsyncOpenAI
from typing import AsyncGenerator, Optional
from .config import ModelSettings
from .utils.logger import setup_logger, log_async_error

class OpenAIHandler:
    def __init__(self, api_key: str):
        self.logger = setup_logger('openai_handler')
        self.api_key = api_key
        self.clients: dict = {}  # Store clients for different base URLs
        self.logger.info("OpenAI handler initialized")

    def get_client(self, base_url: str) -> AsyncOpenAI:
        if base_url not in self.clients:
            self.logger.debug(f"Creating new OpenAI client for base URL: {base_url}")
            self.clients[base_url] = AsyncOpenAI(
                api_key=self.api_key,
                base_url=base_url
            )
        return self.clients[base_url]

    async def stream_text_response(
        self, 
        messages: list, 
        settings: ModelSettings
    ) -> AsyncGenerator[str, None]:
        self.logger.debug(f"Starting text stream with model {settings.model_name}")
        
        try:
            client = self.get_client(settings.base_url)
            
            self.logger.debug(f"Request params: temperature={settings.temperature}, "
                            f"max_tokens={settings.max_tokens}")
            
            stream = await client.chat.completions.create(
                model=settings.model_name,
                messages=messages,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_msg = f"Error in stream_text_response: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            yield f"Ошибка: {str(e)}"

    async def generate_image(
        self,
        prompt: str,
        settings: ModelSettings,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "natural"
    ) -> str:
        """Generate image using DALL-E"""
        client = self.get_client(settings.base_url)
        
        try:
            response = await client.images.generate(
                model=settings.model_name,
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                n=1
            )
            return response.data[0].url
        except Exception as e:
            raise Exception(f"Ошибка генерации изображения: {str(e)}")

    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        settings: ModelSettings
    ) -> str:
        """Analyze image using GPT-4 Vision"""
        client = self.get_client(settings.base_url)
        
        try:
            response = await client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": image_url}
                        ]
                    }
                ],
                max_tokens=settings.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Ошибка анализа изображения: {str(e)}")

    async def transcribe_audio(
        self,
        audio_file: bytes,
        settings: ModelSettings,
        language: str = None
    ) -> str:
        """Transcribe audio using Whisper"""
        client = self.get_client(settings.base_url)
        
        try:
            response = await client.audio.transcriptions.create(
                model=settings.model_name,
                file=audio_file,
                language=language,
                response_format="text"
            )
            return response
        except Exception as e:
            raise Exception(f"Ошибка транскрибации: {str(e)}")

    async def text_to_speech(
        self,
        text: str,
        settings: ModelSettings,
        voice: str = "alloy",
        speed: float = 1.0
    ) -> bytes:
        """Convert text to speech using OpenAI TTS"""
        client = self.get_client(settings.base_url)
        
        try:
            response = await client.audio.speech.create(
                model=settings.model_name,
                voice=voice,
                input=text,
                speed=speed
            )
            return await response.read()
        except Exception as e:
            raise Exception(f"Ошибка синтеза речи: {str(e)}")