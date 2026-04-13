# Discord Bot Base

A modular Discord bot base built with discord.py using the Cogs system for easy expansion.

## Features

- ✨ Modular cog-based architecture
- 🔧 Easy command registration
- ⚙️ Configurable settings
- 📦 Pre-built example cogs
- 🛡️ Error handling

## Installation

1. **Clone or download this repository**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup environment variables**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_bot_token_here
   ```

## Getting Your Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Go to "Bot" section and click "Add Bot"
4. Under TOKEN, click "Copy" to copy your bot token
5. Paste it in your `.env` file

## Running the Bot

```bash
python main.py
```

## Project Structure

```
unibot/
├── main.py              # Main bot file
├── config.py            # Configuration settings
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── .env                 # Environment variables (create from .env.example)
└── cogs/               # Command modules (cogs)
    ├── __init__.py
    ├── ping.py         # Ping command example
    ├── help.py         # Help command example
    └── template.py     # Template for creating new cogs
```

## Creating New Commands

1. **Create a new file in the `cogs/` folder** (e.g., `cogs/mycommand.py`)

2. **Use the template cog as a reference:**
   ```python
   import discord
   from discord.ext import commands

   class MyCommand(commands.Cog):
       """Description of your cog"""
       
       def __init__(self, bot):
           self.bot = bot
       
       @commands.command(name='mycommand')
       async def my_command(self, ctx):
           """Command description"""
           await ctx.send('Hello!')
   
   async def setup(bot):
       await bot.add_cog(MyCommand(bot))
   ```

3. **Restart the bot** - It will automatically load your new cog!

## Command Examples

- `!ping` - Check bot latency
- `!help` - Show all commands
- `!help <command>` - Show help for a specific command

## Available Cogs

### Ping
- `!ping` - Check bot responsiveness and latency

### Help
- `!help` - Display all available commands
- `!help <command>` - Get help for a specific command

## Configuration

Edit `config.py` to customize:
- `PREFIX` - Command prefix (default: `!`)
- `COLORS` - Embed colors for different message types
- `INTENTS_FLAGS` - Discord intents configuration

## Troubleshooting

**Bot not responding?**
- Check that your token is correct in `.env`
- Make sure the bot has proper permissions in your server
- Check the bot's intent settings in Discord Developer Portal

**Cogs not loading?**
- Ensure cog files are in the `cogs/` folder
- Check that each cog has the `async def setup(bot)` function
- Look at console output for error messages

**Command prefix not working?**
- Change `PREFIX` in `config.py`
- Restart the bot after making changes

## Resources

- [discord.py Documentation](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers/applications)
- [Discord.py GitHub](https://github.com/Rapptz/discord.py)

## License

Feel free to use this template for your own projects!
