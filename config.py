"""
Configuration settings for the Discord bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Bot settings
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '!'
INTENTS_FLAGS = {
    'message_content': True,
    'members': True,
    'guilds': True,
    'guild_messages': True,
}

# Colors for embeds
COLORS = {
    'success': 0x2ecc71,
    'error': 0xe74c3c,
    'info': 0x3498db,
    'warning': 0xf39c12,
}
