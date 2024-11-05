# 🤖 GPT Telegram Bot

A powerful Telegram bot that integrates OpenAI's GPT, DALL-E, and voice models for text, image, and voice interactions.

## ✨ Features

### 💬 Text Processing
- OpenAI GPT models with streaming support
- Contextual conversations
- Customizable model parameters
- AI Assistant API integration option

### 🎨 Image Generation & Analysis
- DALL-E image generation
- Image analysis with GPT-4 Vision
- Customizable image parameters (size, quality, style)

### 🎤 Voice Processing
- Speech-to-Text (Whisper)
- Text-to-Speech (OpenAI TTS)
- Multiple voice options and speed control

### 👥 Group Chat Support
- Mention & reply-based interactions
- Admin controls
- Usage limits
- User permissions

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Telegram Bot Token
- OpenAI API Key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gpt-telegram-bot.git
cd gpt-telegram-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```env
TELEGRAM_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
```

4. Run the bot:
```bash
python -m main
```

## 🛠 Configuration

### Text Model Settings
- Base URL
- Model selection (GPT-3.5-Turbo, GPT-4, etc.)
- Temperature (0-1)
- Max tokens
- AI Assistant API endpoint (optional)

### Image Settings
- Model selection
- Size options (1024x1024, 1024x1792, 1792x1024)
- Quality (standard/HD)
- Style (natural/vivid)

### Voice Settings
- TTS/STT models
- Voice types
- Speech speed

## 📝 Usage

### Basic Commands
- `/start` - Start the bot
- `/help` - Show help menu
- `/settings` - Access settings
- `/clear` - Clear message history

### Text Interaction
- Simply send a message
- Supports conversation context
- Configure model parameters in settings

### Image Commands
- `/image` or `!image` + description for generation
- Send image with caption for analysis

### Voice Commands
- Send voice message for transcription
- `/speak` or `!speak` + text for voice synthesis

### Group Chat Commands
- `/groupsettings` - Group-specific settings
- `/grouphelp` - Group usage help

## 📁 Project Structure
```
📁 gpt-telegram-bot/
├── 📁 src/
│   ├── __init__.py
│   ├── bot.py          # Main bot implementation
│   ├── models.py       # OpenAI models integration
│   ├── services.py     # History & services
│   ├── config.py       # Configuration
│   └── 📁 utils/
│       ├── __init__.py
│       └── logger.py   # Logging setup
├── main.py            # Entry point
├── .env              # Environment variables
├── requirements.txt  # Dependencies
└── README.md        # Documentation
```

## 🔧 Development

### Requirements
```
python-telegram-bot==20.8
python-dotenv==1.0.0
openai==1.12.0
aiohttp==3.9.3
async-timeout==4.0.3
```

### Logging
- Console output with color coding
- Separate debug and error logs
- Railway.app compatible logging

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Note
Remember to handle your API keys securely and never commit them to version control.