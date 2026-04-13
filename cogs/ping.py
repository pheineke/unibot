"""
Ping cog - Basic bot responsiveness check
"""
import discord
from discord.ext import commands
import time

class Ping(commands.Cog):
    """Ping commands for checking bot status"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='ping')
    async def ping(self, ctx):
        """
        Check bot latency
        Usage: !ping
        """
        start = time.time()
        message = await ctx.send('🏓 Pong!')
        end = time.time()
        
        latency_ms = round(self.bot.latency * 1000)
        response_time_ms = round((end - start) * 1000)
        
        await message.edit(content=f'🏓 Pong!\n'
                          f'Bot latency: {latency_ms}ms\n'
                          f'Response time: {response_time_ms}ms')

async def setup(bot):
    """Required function to load this cog"""
    await bot.add_cog(Ping(bot))
