"""
Template cog - Copy this to create new command modules
"""
import discord
from discord.ext import commands

class Template(commands.Cog):
    """Template cog description"""
    
    def __init__(self, bot):
        self.bot = bot
    
    # ==================== Commands ====================
    
    @commands.command(name='example')
    async def example(self, ctx):
        """
        Example command
        Usage: !example
        """
        embed = discord.Embed(
            title='Example Command',
            description='This is an example command from the template cog',
            color=0x3498db
        )
        await ctx.send(embed=embed)
    
    # ==================== Events ====================
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Called when a member joins the server"""
        print(f'{member} joined the server')
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Called when a message is sent"""
        if message.author == self.bot.user:
            return
        # Add custom message handling here

async def setup(bot):
    """Required function to load this cog"""
    await bot.add_cog(Template(bot))
