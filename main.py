"""
Main Discord Bot - with modular cog system
"""
import discord
from discord.ext import commands
import os
import asyncio
import config

# Setup intents
intents = discord.Intents.default()
intents.message_content = config.INTENTS_FLAGS['message_content']
intents.members = config.INTENTS_FLAGS['members']
intents.guilds = config.INTENTS_FLAGS['guilds']
intents.guild_messages = config.INTENTS_FLAGS['guild_messages']

# Initialize bot
bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)

# ==================== Events ====================

@bot.event
async def on_ready():
    """Called when the bot has successfully connected to Discord"""
    print(f'✓ Bot logged in as {bot.user}')
    print(f'✓ Bot ID: {bot.user.id}')
    print(f'✓ Discord.py version: {discord.__version__}')
    try:
        synced = await bot.tree.sync()
        print(f'✓ Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'✗ Failed to sync commands: {e}')

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler"""
    print(f'Error in {event}:', exc_info=True)

# ==================== Cog Loading ====================

async def load_cogs():
    """Dynamically load all cogs from the cogs folder"""
    cogs_dir = 'cogs'
    
    if not os.path.exists(cogs_dir):
        print(f'✗ Cogs directory not found: {cogs_dir}')
        return
    
    cog_files = [f[:-3] for f in os.listdir(cogs_dir) if f.endswith('.py') and f != '__init__.py']
    
    print(f'\n📦 Loading {len(cog_files)} cog(s)...')
    for cog in cog_files:
        try:
            await bot.load_extension(f'cogs.{cog}')
            print(f'  ✓ Loaded cog: {cog}')
        except Exception as e:
            print(f'  ✗ Failed to load cog {cog}: {e}')

# ==================== Main ====================

async def main():
    """Main function to run the bot"""
    async with bot:
        await load_cogs()
        await bot.start(config.TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
