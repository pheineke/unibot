"""
Help cog - Display available commands
"""
import discord
from discord.ext import commands
import config

class Help(commands.Cog):
    """Help and information commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='help')
    async def help(self, ctx, *, command: str = None):
        """
        Show available commands or help for a specific command
        Usage: !help [command_name]
        """
        if command:
            # Help for a specific command
            cmd = self.bot.get_command(command)
            if cmd is None:
                embed = discord.Embed(
                    title='Command Not Found',
                    description=f'Could not find command: `{command}`',
                    color=config.COLORS['error']
                )
            else:
                embed = discord.Embed(
                    title=f'Help: {cmd.name}',
                    description=cmd.help or 'No description available',
                    color=config.COLORS['info']
                )
            await ctx.send(embed=embed)
        else:
            # General help - list all commands
            embed = discord.Embed(
                title='📚 Available Commands',
                description=f'Use `{config.PREFIX}help <command>` for more info',
                color=config.COLORS['info']
            )
            
            # Group commands by cog
            cogs_dict = {}
            for command in self.bot.commands:
                if command.hidden:
                    continue
                cog_name = command.cog.qualified_name if command.cog else 'Other'
                if cog_name not in cogs_dict:
                    cogs_dict[cog_name] = []
                cogs_dict[cog_name].append(command.name)
            
            for cog_name, commands_list in sorted(cogs_dict.items()):
                embed.add_field(
                    name=cog_name,
                    value=', '.join([f'`{cmd}`' for cmd in sorted(commands_list)]),
                    inline=False
                )
            
            await ctx.send(embed=embed)

async def setup(bot):
    """Required function to load this cog"""
    await bot.add_cog(Help(bot))
