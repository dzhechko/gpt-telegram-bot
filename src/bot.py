from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    InputMediaPhoto, 
    CallbackQuery,
    Chat,
    ChatMember
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from typing import Dict, Optional, List, Any, Union
from .config import Config, ModelSettings
from .models import OpenAIHandler
from .services import MessageHistory, AIAssistantService
import aiohttp
from io import BytesIO
from .utils.logger import setup_logger, log_async_error
import traceback
import json

class Bot:
    def __init__(self):
        self.logger = setup_logger('telegram_bot')
        self.logger.info("Initializing bot...")
        
        try:
            self.config = Config()
            self.openai_handler = OpenAIHandler(self.config.OPENAI_API_KEY)
            self.message_history = MessageHistory()
            self.ai_assistant = AIAssistantService()
            self.user_settings: Dict[int, Dict[str, ModelSettings]] = {}
            
            self.logger.info("Bot initialized successfully")
        except Exception as e:
            self.logger.critical(f"Failed to initialize bot: {str(e)}", exc_info=True)
            raise

    def get_user_settings(self, user_id: int) -> Dict[str, ModelSettings]:
        if user_id not in self.user_settings:
            self.user_settings[user_id] = {
                "text": self.config.TEXT_MODEL,
                "image": self.config.IMAGE_MODEL,
                "voice": self.config.VOICE_MODEL
            }
        return self.user_settings[user_id]

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        welcome_text = (
            "Привет! Я ваш AI-ассистент. Я могу:\n"
            "• Отвечать на текстовые сообщения\n"
            "• Генерировать изображения\n"
            "• Работать с голосовыми сообщениями\n\n"
            "Используйте /settings для настройки параметров."
        )
        await update.message.reply_text(welcome_text)

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /settings command"""
        keyboard = [
            [InlineKeyboardButton(self.config.MENU_OPTIONS["text_settings"], 
                                callback_data="settings_text")],
            [InlineKeyboardButton(self.config.MENU_OPTIONS["image_settings"], 
                                callback_data="settings_image")],
            [InlineKeyboardButton(self.config.MENU_OPTIONS["voice_settings"], 
                                callback_data="settings_voice")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Выберите настрйки:", reply_markup=reply_markup)

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        user_id = update.effective_user.id
        self.logger.debug(f"Handling text message from user {user_id}: {update.message.text[:100]}...")
        
        try:
            user_settings = self.get_user_settings(user_id)
            text_settings = user_settings["text"]

            # Log settings being used
            self.logger.debug(f"Using settings for user {user_id}: {json.dumps(text_settings.__dict__)}")

            # Add user message to history
            self.message_history.add_message(user_id, "user", update.message.text)
            messages = self.message_history.get_history(user_id)

            # Send initial response
            response_message = await update.message.reply_text("...")
            collected_response = []

            # Handle AI Assistant if configured
            if text_settings.assistant_api_endpoint:
                self.logger.info(f"Using AI Assistant for user {user_id}")
                try:
                    response = await self.ai_assistant.process_message(update.message.text)
                    await response_message.edit_text(response)
                    self.message_history.add_message(user_id, "assistant", response)
                    return
                except Exception as e:
                    error_msg = f"AI Assistant error for user {user_id}: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    await response_message.edit_text(f"Ошибка AI Assistant: {str(e)}")
                    return

            # Handle streaming response
            self.logger.debug(f"Starting streaming response for user {user_id}")
            try:
                async for chunk in self.openai_handler.stream_text_response(messages, text_settings):
                    collected_response.append(chunk)
                    if len(collected_response) % 3 == 0:
                        await response_message.edit_text("".join(collected_response))
            except Exception as e:
                error_msg = f"Streaming error for user {user_id}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                await response_message.edit_text(f"Ошибка при получении ответа: {str(e)}")
                return

            final_response = "".join(collected_response)
            await response_message.edit_text(final_response)
            self.message_history.add_message(user_id, "assistant", final_response)
            
            self.logger.debug(f"Successfully processed message for user {user_id}")
            
        except Exception as e:
            error_msg = f"Unexpected error handling message from user {user_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            await update.message.reply_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")

    async def handle_settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced settings callback handler"""
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data
        
        await query.answer()
        
        if data == "clear_history":
            await self.show_clear_history_confirmation(query)
            return
        
        if data == "back_main":
            await self.show_main_settings(query)
            return
            
        if data.startswith("settings_"):
            model_type = data.split("_")[1]
            await self.show_model_settings(query, model_type)
            return
            
        if data.startswith(("model_", "temp_", "tokens_", "voice_", "size_", "quality_")):
            await self.handle_specific_setting(query, data)
            return

    async def show_main_settings(self, query: CallbackQuery):
        """Show main settings menu"""
        keyboard = [
            [InlineKeyboardButton(self.config.MENU_OPTIONS["text_settings"], 
                                callback_data="settings_text")],
            [InlineKeyboardButton(self.config.MENU_OPTIONS["image_settings"], 
                                callback_data="settings_image")],
            [InlineKeyboardButton(self.config.MENU_OPTIONS["voice_settings"], 
                                callback_data="settings_voice")],
            [InlineKeyboardButton(self.config.MENU_OPTIONS["clear_history"], 
                                callback_data="clear_history")]
        ]
        await query.edit_message_text(
            "Настройки бота:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_model_settings(self, query: CallbackQuery, model_type: str):
        """Show settings for specific model type"""
        user_id = query.from_user.id
        user_settings = self.get_user_settings(user_id)
        current_settings = user_settings[model_type]
        
        if model_type == "text":
            keyboard = [
                [InlineKeyboardButton("Модель", callback_data="model_select_text")],
                [InlineKeyboardButton(
                    f"Температура: {current_settings.temperature}", 
                    callback_data="temp_adjust_text"
                )],
                [InlineKeyboardButton(
                    f"Max tokens: {current_settings.max_tokens}", 
                    callback_data="tokens_adjust_text"
                )],
                [InlineKeyboardButton(
                    "AI Assistant API" if current_settings.assistant_api_endpoint else "GPT API",
                    callback_data="toggle_assistant"
                )],
                [InlineKeyboardButton(self.config.MENU_OPTIONS["back"], callback_data="back_main")]
            ]
            
        elif model_type == "image":
            keyboard = [
                [InlineKeyboardButton("Модель", callback_data="model_select_image")],
                [InlineKeyboardButton(self.config.MENU_OPTIONS["image_size"], 
                                    callback_data="size_select")],
                [InlineKeyboardButton(self.config.MENU_OPTIONS["image_quality"], 
                                    callback_data="quality_select")],
                [InlineKeyboardButton(self.config.MENU_OPTIONS["image_style"], 
                                    callback_data="style_select")],
                [InlineKeyboardButton(self.config.MENU_OPTIONS["back"], callback_data="back_main")]
            ]
            
        else:  # voice
            keyboard = [
                [InlineKeyboardButton("Модель TTS", callback_data="model_select_tts")],
                [InlineKeyboardButton("Модель STT", callback_data="model_select_stt")],
                [InlineKeyboardButton(self.config.MENU_OPTIONS["voice_type"], 
                                    callback_data="voice_type")],
                [InlineKeyboardButton(self.config.MENU_OPTIONS["voice_speed"], 
                                    callback_data="voice_speed")],
                [InlineKeyboardButton(self.config.MENU_OPTIONS["back"], callback_data="back_main")]
            ]
        
        await query.edit_message_text(
            f"Настройки {self.config.MENU_OPTIONS[f'{model_type}_settings'].lower()}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_specific_setting(self, query: CallbackQuery, data: str):
        """Handle specific setting adjustments"""
        user_id = query.from_user.id
        user_settings = self.get_user_settings(user_id)
        
        if data.startswith("model_select_"):
            model_type = data.split("_")[2]
            await self.show_model_selection(query, model_type)
            
        elif data.startswith("temp_adjust_"):
            model_type = data.split("_")[2]
            await self.show_temperature_adjustment(query, model_type)
            
        elif data.startswith("tokens_adjust_"):
            model_type = data.split("_")[2]
            await self.show_tokens_adjustment(query, model_type)
            
        elif data == "toggle_assistant":
            await self.toggle_ai_assistant(query)

    async def show_model_selection(self, query: CallbackQuery, model_type: str):
        """Show model selection menu"""
        if model_type == "text":
            models = self.config.AVAILABLE_TEXT_MODELS
        elif model_type == "tts":
            models = self.config.AVAILABLE_VOICE_MODELS["tts"]
        elif model_type == "stt":
            models = self.config.AVAILABLE_VOICE_MODELS["transcription"]
        else:
            models = []  # For image models
            
        keyboard = [
            [InlineKeyboardButton(model, callback_data=f"set_model_{model_type}_{model}")]
            for model in models
        ]
        keyboard.append([InlineKeyboardButton(
            self.config.MENU_OPTIONS["back"], 
            callback_data=f"settings_{model_type}"
        )])
        
        await query.edit_message_text(
            "Выберите модель:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_temperature_adjustment(self, query: CallbackQuery, model_type: str):
        """Show temperature adjustment menu"""
        user_settings = self.get_user_settings(query.from_user.id)
        current_temp = user_settings[model_type].temperature
        
        keyboard = [
            [
                InlineKeyboardButton("0.2", callback_data=f"set_temp_{model_type}_0.2"),
                InlineKeyboardButton("0.5", callback_data=f"set_temp_{model_type}_0.5"),
                InlineKeyboardButton("0.7", callback_data=f"set_temp_{model_type}_0.7")
            ],
            [
                InlineKeyboardButton("0.8", callback_data=f"set_temp_{model_type}_0.8"),
                InlineKeyboardButton("0.9", callback_data=f"set_temp_{model_type}_0.9"),
                InlineKeyboardButton("1.0", callback_data=f"set_temp_{model_type}_1.0")
            ],
            [InlineKeyboardButton(
                self.config.MENU_OPTIONS["back"], 
                callback_data=f"settings_{model_type}"
            )]
        ]
        
        await query.edit_message_text(
            f"Текущая температура: {current_temp}\nВыберите новое значение:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_tokens_adjustment(self, query: CallbackQuery, model_type: str):
        """Show tokens adjustment menu"""
        user_settings = self.get_user_settings(query.from_user.id)
        current_tokens = user_settings[model_type].max_tokens
        
        keyboard = [
            [
                InlineKeyboardButton("500", callback_data=f"set_tokens_{model_type}_500"),
                InlineKeyboardButton("1000", callback_data=f"set_tokens_{model_type}_1000"),
                InlineKeyboardButton("2000", callback_data=f"set_tokens_{model_type}_2000")
            ],
            [
                InlineKeyboardButton("4000", callback_data=f"set_tokens_{model_type}_4000"),
                InlineKeyboardButton("8000", callback_data=f"set_tokens_{model_type}_8000"),
                InlineKeyboardButton("16000", callback_data=f"set_tokens_{model_type}_16000")
            ],
            [InlineKeyboardButton(
                self.config.MENU_OPTIONS["back"], 
                callback_data=f"settings_{model_type}"
            )]
        ]
        
        await query.edit_message_text(
            f"Текущий лимит токенов: {current_tokens}\nВыберите новое значение:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def toggle_ai_assistant(self, query: CallbackQuery):
        """Toggle between GPT API and AI Assistant"""
        user_id = query.from_user.id
        user_settings = self.get_user_settings(user_id)
        
        keyboard = [
            [InlineKeyboardButton(
                "Использоват GPT API", 
                callback_data="set_assistant_none"
            )],
            [InlineKeyboardButton(
                "Настроить AI Assistant", 
                callback_data="configure_assistant"
            )],
            [InlineKeyboardButton(
                self.config.MENU_OPTIONS["back"], 
                callback_data="settings_text"
            )]
        ]
        
        current_mode = "AI Assistant" if user_settings["text"].assistant_api_endpoint else "GPT API"
        
        await query.edit_message_text(
            f"Текущий режим: {current_mode}\nВыберите режим работы:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_image_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming images"""
        user_id = update.effective_user.id
        user_settings = self.get_user_settings(user_id)
        
        # Get the largest available photo
        photo = update.message.photo[-1]
        
        # Get file path
        file = await context.bot.get_file(photo.file_id)
        
        # Download image
        async with aiohttp.ClientSession() as session:
            async with session.get(file.file_url) as response:
                if response.status != 200:
                    await update.message.reply_text("Ошибка при загрузке изображения")
                    return
                
                image_data = await response.read()
        
        # If there's a caption, use it as a prompt for image analysis
        if update.message.caption:
            try:
                analysis = await self.openai_handler.analyze_image(
                    file.file_url,
                    update.message.caption,
                    user_settings["text"]
                )
                await update.message.reply_text(analysis)
            except Exception as e:
                await update.message.reply_text(f"Ошибка при анализе изображения: {str(e)}")

    async def handle_image_generation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle image generation requests"""
        user_id = update.effective_user.id
        user_settings = self.get_user_settings(user_id)
        
        # Check if the message starts with /image or !image
        if not update.message.text.startswith(('/image', '!image')):
            return
        
        # Extract prompt
        prompt = update.message.text.split(maxsplit=1)[1]
        
        # Send "generating" message
        status_message = await update.message.reply_text("Генерирую изображение...")
        
        try:
            # Generate image
            image_url = await self.openai_handler.generate_image(
                prompt=prompt,
                settings=user_settings["image"]
            )
            
            # Download and send the generated image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        await update.message.reply_photo(
                            photo=BytesIO(image_data),
                            caption=f"Prompt: {prompt}"
                        )
                        await status_message.delete()
                    else:
                        await status_message.edit_text("Ошибка при загрузке сгенерированного изображения")
        except Exception as e:
            await status_message.edit_text(f"Ошибка при генерации изображения: {str(e)}")

    async def image_settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle image settings callbacks"""
        query = update.callback_query
        user_id = query.from_user.id
        user_settings = self.get_user_settings(user_id)
        
        if query.data == "image_size":
            keyboard = [
                [InlineKeyboardButton("1024x1024", callback_data="size_1024")],
                [InlineKeyboardButton("1024x1792", callback_data="size_1024_1792")],
                [InlineKeyboardButton("1792x1024", callback_data="size_1792_1024")],
                [InlineKeyboardButton(self.config.MENU_OPTIONS["back"], callback_data="back_image")]
            ]
            await query.edit_message_text(
                "Выберите размер изображения:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif query.data == "image_quality":
            keyboard = [
                [InlineKeyboardButton("Стандартное", callback_data="quality_standard")],
                [InlineKeyboardButton("HD", callback_data="quality_hd")],
                [InlineKeyboardButton(self.config.MENU_OPTIONS["back"], callback_data="back_image")]
            ]
            await query.edit_message_text(
                "Выберите качество изображения:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming voice messages"""
        user_id = update.effective_user.id
        user_settings = self.get_user_settings(user_id)
        
        # Send "processing" message
        status_message = await update.message.reply_text("Обрабатываю голосовое сообщение...")
        
        try:
            # Get voice file
            voice = update.message.voice
            voice_file = await context.bot.get_file(voice.file_id)
            
            # Download voice file
            async with aiohttp.ClientSession() as session:
                async with session.get(voice_file.file_url) as response:
                    if response.status != 200:
                        await status_message.edit_text("Ошибка при загрузке голосового сообщения")
                        return
                    
                    voice_data = await response.read()
            
            # Transcribe voice to text
            transcription = await self.openai_handler.transcribe_audio(
                voice_data,
                user_settings["voice"]
            )
            
            # Add transcription to message history
            self.message_history.add_message(user_id, "user", transcription)
            
            # Process transcribed text with chat model
            response_message = await update.message.reply_text(f"Транскрипция: {transcription}\n\nГенерирую ответ...")
            collected_response = []
            
            async for chunk in self.openai_handler.stream_text_response(
                self.message_history.get_history(user_id),
                user_settings["text"]
            ):
                collected_response.append(chunk)
                if len(collected_response) % 3 == 0:
                    await response_message.edit_text(f"Транскрипция: {transcription}\n\nОтвет: {''.join(collected_response)}")
            
            final_response = "".join(collected_response)
            await response_message.edit_text(f"Транскрипция: {transcription}\n\nОтвет: {final_response}")
            
            # Generate voice response
            voice_response = await self.openai_handler.text_to_speech(
                final_response,
                user_settings["voice"]
            )
            
            # Send voice response
            await update.message.reply_voice(
                voice=BytesIO(voice_response),
                caption="Голосовой ответ"
            )
            
            # Clean up status message
            await status_message.delete()
            
        except Exception as e:
            await status_message.edit_text(f"Ошибка при обработке голосового сообщения: {str(e)}")

    async def handle_text_to_speech(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text-to-speech requests"""
        user_id = update.effective_user.id
        user_settings = self.get_user_settings(user_id)
        
        # Check if the message starts with /speak or !speak
        if not update.message.text.startswith(('/speak', '!speak')):
            return
        
        # Extract text
        text = update.message.text.split(maxsplit=1)[1]
        
        # Send "processing" message
        status_message = await update.message.reply_text("Генерирую голосовое сообщение...")
        
        try:
            # Generate voice message
            voice_data = await self.openai_handler.text_to_speech(
                text,
                user_settings["voice"]
            )
            
            # Send voice message
            await update.message.reply_voice(
                voice=BytesIO(voice_data),
                caption=f"Текст: {text}"
            )
            await status_message.delete()
            
        except Exception as e:
            await status_message.edit_text(f"Ошибка при генерации голосового сообщения: {str(e)}")

    async def voice_settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice settings callbacks"""
        query = update.callback_query
        user_id = query.from_user.id
        user_settings = self.get_user_settings(user_id)
        
        if query.data == "voice_type":
            keyboard = [
                [InlineKeyboardButton(voice.capitalize(), callback_data=f"voice_{voice}")]
                for voice in self.config.AVAILABLE_VOICES
            ]
            keyboard.append([InlineKeyboardButton(self.config.MENU_OPTIONS["back"], 
                                                callback_data="back_voice")])
            
            await query.edit_message_text(
                "Выберите тип голоса:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif query.data == "voice_speed":
            keyboard = [
                [InlineKeyboardButton("0.75x", callback_data="speed_0.75"),
                 InlineKeyboardButton("1.0x", callback_data="speed_1.0"),
                 InlineKeyboardButton("1.25x", callback_data="speed_1.25")],
                [InlineKeyboardButton(self.config.MENU_OPTIONS["back"], 
                                    callback_data="back_voice")]
            ]
            await query.edit_message_text(
                "Выберите скорость речи:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def update_model_setting(self, user_id: int, model_type: str, model_name: str):
        """Update model setting"""
        settings = self.get_user_settings(user_id)
        settings[model_type].model_name = model_name

    async def update_temperature_setting(self, user_id: int, model_type: str, temperature: float):
        """Update temperature setting"""
        settings = self.get_user_settings(user_id)
        settings[model_type].temperature = temperature

    async def update_tokens_setting(self, user_id: int, model_type: str, max_tokens: int):
        """Update max tokens setting"""
        settings = self.get_user_settings(user_id)
        settings[model_type].max_tokens = max_tokens

    async def update_assistant_endpoint(self, user_id: int, endpoint: Optional[str]):
        """Update AI Assistant endpoint"""
        settings = self.get_user_settings(user_id)
        settings["text"].assistant_api_endpoint = endpoint

    async def handle_group_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle messages in group chats"""
        message = update.message
        
        # Check if bot was mentioned or message is a reply to bot's message
        is_mentioned = any(entity.type == "mention" for entity in message.entities) if message.entities else False
        is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id
        
        # Only process messages that mention the bot or reply to its messages
        if not (is_mentioned or is_reply_to_bot):
            return
        
        # Remove bot username from message if mentioned
        text = message.text
        if is_mentioned:
            bot_username = context.bot.username
            text = text.replace(f"@{bot_username}", "").strip()
        
        # Process message as if it was a direct message
        update.message.text = text
        await self.handle_text_message(update, context)

    async def handle_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle commands in group chats"""
        if not update.effective_chat.type in ["group", "supergroup"]:
            return
            
        command = update.message.text.split()[0].lower()
        
        if command == "/groupsettings":
            await self.show_group_settings(update, context)
        elif command == "/grouphelp":
            await self.show_group_help(update, context)

    async def show_group_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings specific to group chats"""
        # Check if user is admin
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            is_admin = member.status in ["creator", "administrator"]
        except Exception:
            is_admin = False
        
        if not is_admin:
            await update.message.reply_text(
                "Только администраторы группы могут менять настройки бота."
            )
            return
        
        keyboard = [
            [InlineKeyboardButton(
                "Режим отетов", 
                callback_data=f"group_response_mode_{chat_id}"
            )],
            [InlineKeyboardButton(
                "Права пользователей", 
                callback_data=f"group_user_rights_{chat_id}"
            )],
            [InlineKeyboardButton(
                "Ограничения использования", 
                callback_data=f"group_usage_limits_{chat_id}"
            )]
        ]
        
        await update.message.reply_text(
            "Настройк бота для группы:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_group_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message for group chat usage"""
        help_text = (
            "Как использовать бота в группе:\n\n"
            "1. Упомяните бота (@bot_username) или ответьте на его сообщение\n"
            "2. Используйте команды:\n"
            "   • /groupsettings - настройки бота для группы\n"
            "   • /grouphelp - это сообщение\n"
            "   • !image или /image - генерация изображений\n"
            "   • !speak или /speak - преобразование текста в речь\n\n"
            "Администраторы мгут настраивать:\n"
            "• Режим ответов бота\n"
            "• Права пользователей\n"
            "• Ограничения использования"
        )
        await update.message.reply_text(help_text)

    async def handle_group_settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle group settings callbacks"""
        query = update.callback_query
        data = query.data
        chat_id = int(data.split("_")[-1])
        
        # Verify admin rights
        try:
            member = await context.bot.get_chat_member(chat_id, query.from_user.id)
            is_admin = member.status in ["creator", "administrator"]
        except Exception:
            is_admin = False
        
        if not is_admin:
            await query.answer("Только администраторы могут менять настройки", show_alert=True)
            return
        
        await query.answer()
        
        if data.startswith("group_response_mode"):
            await self.show_response_mode_settings(query, chat_id)
        elif data.startswith("group_user_rights"):
            await self.show_user_rights_settings(query, chat_id)
        elif data.startswith("group_usage_limits"):
            await self.show_usage_limits_settings(query, chat_id)

    async def show_response_mode_settings(self, query: CallbackQuery, chat_id: int):
        """Show response mode settings"""
        keyboard = [
            [InlineKeyboardButton(
                "Отвечать на упоминания", 
                callback_data=f"set_response_mentions_{chat_id}"
            )],
            [InlineKeyboardButton(
                "Отвечать на ответы", 
                callback_data=f"set_response_replies_{chat_id}"
            )],
            [InlineKeyboardButton(
                "Отвечать на все сообщения", 
                callback_data=f"set_response_all_{chat_id}"
            )],
            [InlineKeyboardButton(
                self.config.MENU_OPTIONS["back"], 
                callback_data=f"group_settings_{chat_id}"
            )]
        ]
        
        await query.edit_message_text(
            "Выберите режим ответов бота:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_user_rights_settings(self, query: CallbackQuery, chat_id: int):
        """Show user rights settings"""
        keyboard = [
            [InlineKeyboardButton(
                "Все пользователи", 
                callback_data=f"set_rights_all_{chat_id}"
            )],
            [InlineKeyboardButton(
                "Только администраторы", 
                callback_data=f"set_rights_admins_{chat_id}"
            )],
            [InlineKeyboardButton(
                "Белый список", 
                callback_data=f"set_rights_whitelist_{chat_id}"
            )],
            [InlineKeyboardButton(
                self.config.MENU_OPTIONS["back"], 
                callback_data=f"group_settings_{chat_id}"
            )]
        ]
        
        await query.edit_message_text(
            "Выберите права доступа к боту:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_usage_limits_settings(self, query: CallbackQuery, chat_id: int):
        """Show usage limits settings"""
        keyboard = [
            [InlineKeyboardButton(
                "Лимит сообщений в день", 
                callback_data=f"set_limit_messages_{chat_id}"
            )],
            [InlineKeyboardButton(
                "Лимит генераций изображений", 
                callback_data=f"set_limit_images_{chat_id}"
            )],
            [InlineKeyboardButton(
                "Лимит голосовых сообщений", 
                callback_data=f"set_limit_voice_{chat_id}"
            )],
            [InlineKeyboardButton(
                self.config.MENU_OPTIONS["back"], 
                callback_data=f"group_settings_{chat_id}"
            )]
        ]
        
        await query.edit_message_text(
            "Настройте ограничения использования:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def clear_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /clear command"""
        user_id = update.effective_user.id
        
        keyboard = [
            [InlineKeyboardButton("Подтвердить очистку", callback_data="confirm_clear")],
            [InlineKeyboardButton("Отмена", callback_data="cancel_clear")]
        ]
        
        await update.message.reply_text(
            "Вы уверены, что хотите очистить историю сообщений?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_clear_history_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle clear history confirmation"""
        query = update.callback_query
        user_id = query.from_user.id
        
        await query.answer()
        
        if query.data == "confirm_clear":
            # Clear history
            self.message_history.clear_history(user_id)
            await query.edit_message_text("История сообщений очищена.")
        elif query.data == "cancel_clear":
            await query.edit_message_text("Очистка истории отменена.")

    async def show_clear_history_confirmation(self, query: CallbackQuery):
        """Show clear history confirmation dialog"""
        keyboard = [
            [InlineKeyboardButton("Подтвердить очистку", callback_data="confirm_clear")],
            [InlineKeyboardButton("Отмена", callback_data="cancel_clear")]
        ]
        
        await query.edit_message_text(
            "Вы уверены, что хотите очистить историю сообщений?\n"
            "Это действие нельзя отменить.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command"""
        keyboard = [
            [InlineKeyboardButton("Основные команды", callback_data="help_commands")],
            [InlineKeyboardButton("Работа с текстом", callback_data="help_text")],
            [InlineKeyboardButton("Работа с изображениями", callback_data="help_images")],
            [InlineKeyboardButton("Голосовые сообщения", callback_data="help_voice")],
            [InlineKeyboardButton("Настройки", callback_data="help_settings")],
            [InlineKeyboardButton("Групповые чаты", callback_data="help_groups")]
        ]
        
        await update.message.reply_text(
            "Выберите раздел справки:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_help_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle help menu callbacks"""
        query = update.callback_query
        await query.answer()
        
        help_texts = {
            "help_commands": (
                "📋 *Основные команды:*\n\n"
                "/start - Начать работу с ботом\n"
                "/help - Показать это сообщение\n"
                "/settings - Настройки бота\n"
                "/clear - Очистить историю сообщений\n"
                "/groupsettings - Настройки для групп\n"
                "/grouphelp - Помощь по работе в группах"
            ),
            "help_text": (
                "💬 *Работа с текстом:*\n\n"
                "• Отправьте текстовое сообщение для получения ответа\n"
                "• Бот поддерживает контекст разговора\n"
                "• Можно настроить модель, температуру и другие параметры\n"
                "• Доступно использование AI Assistant API\n\n"
                "*Модели:*\n"
                "• GPT-3.5-Turbo\n"
                "• GPT-4\n"
                "• GPT-4-Turbo\n"
                "• GPT-3.5-Turbo-16k"
            ),
            "help_images": (
                "🖼 *Работа с изображениями:*\n\n"
                "*Генерация:*\n"
                "• /image или !image + описание\n"
                "• Настраиваемые параметры: размер, качество, стиль\n\n"
                "*Анализ:*\n"
                "• Отправьте изображение с описанием\n"
                "• Бот проанализирует изображение и ответит на вопросы"
            ),
            "help_voice": (
                "🎤 *Голосовые сообщения:*\n\n"
                "*Распознавание речи:*\n"
                "• Отправьте голосовое сообщение\n"
                "• Бот преобразует его в текст и ответит\n\n"
                "*Синтез речи:*\n"
                "• /speak или !speak + текст\n"
                "• Настраиваемые голоса и скорость речи"
            ),
            "help_settings": (
                "⚙️ *Настройки:*\n\n"
                "*Текстовая модель:*\n"
                "• Выбор модели\n"
                "• Температура (0.0 - 1.0)\n"
                "• Максимальное количество токенов\n"
                "• AI Assistant API\n\n"
                "*Изображения:*\n"
                "• Размер (1024x1024, 1024x1792, 1792x1024)\n"
                "• Качество (стандартное/HD)\n"
                "• Стиль (natural/vivid)\n\n"
                "*Голос:*\n"
                "• Модели TTS и STT\n"
                "• Тип голоса\n"
                "• Скорость речи"
            ),
            "help_groups": (
                "👥 *Работа в группах:*\n\n"
                "*Использование:*\n"
                "• Упомяните бота (@bot_username)\n"
                "• Ответьте на сообщение бота\n\n"
                "*Настройки групп:*\n"
                "• Режим ответов\n"
                "• Права пользователей\n"
                "• Ограничения использования\n\n"
                "*Доступно только администраторам:*\n"
                "• Изменение настроек группы\n"
                "• Управление правами\n"
                "• Установка лимитов"
            )
        }
        
        if query.data in help_texts:
            keyboard = [[InlineKeyboardButton("« Назад", callback_data="help_main")]]
            await query.edit_message_text(
                help_texts[query.data],
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        elif query.data == "help_main":
            await self.help_command(update, context)

    async def run(self):
        """Start the bot"""
        try:
            application = Application.builder().token(self.config.TELEGRAM_TOKEN).build()

            # Add help handlers
            application.add_handler(CommandHandler("help", self.help_command))
            application.add_handler(CallbackQueryHandler(
                self.handle_help_callback,
                pattern="^help_"
            ))
            
            # Add existing handlers
            application.add_handler(CommandHandler("start", self.start_command))
            application.add_handler(CommandHandler("settings", self.settings_command))
            application.add_handler(CallbackQueryHandler(self.handle_settings_callback))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
            
            # Add new image handlers
            application.add_handler(MessageHandler(filters.PHOTO, self.handle_image_message))
            application.add_handler(MessageHandler(
                filters.Regex(r'^[!/]image\s+.+'), 
                self.handle_image_generation
            ))

            # Add voice handlers
            application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))
            application.add_handler(MessageHandler(
                filters.Regex(r'^[!/]speak\s+.+'), 
                self.handle_text_to_speech
            ))

            # Add group chat handlers
            application.add_handler(CommandHandler("groupsettings", self.handle_group_command))
            application.add_handler(CommandHandler("grouphelp", self.handle_group_command))
            application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
                self.handle_group_message
            ))

            # Add clear history handlers
            application.add_handler(CommandHandler("clear", self.clear_history_command))
            application.add_handler(CallbackQueryHandler(
                self.handle_clear_history_callback,
                pattern="^(confirm|cancel)_clear$"
            ))

            # Start the bot
            self.logger.info("Starting bot polling...")
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            
            # Keep the application running
            await application.updater.wait_closed()
            
        except Exception as e:
            self.logger.critical(f"Failed to run bot: {str(e)}")
            self.logger.critical(traceback.format_exc())
            raise
        finally:
            self.logger.info("Bot stopped")

if __name__ == "__main__":
    bot = Bot()
    bot.run() 