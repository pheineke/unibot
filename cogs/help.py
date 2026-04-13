import discord
from discord.ext import commands

class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            'help': 'Shows help about the bot, a command, or a category'
        })

    def get_command_signature(self, command):
        return f'{self.context.clean_prefix}{command.qualified_name} {command.signature}'

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Bot Help", description="List of all available commands grouped by category.", color=discord.Color.blue())
        
        for cog, cmds in mapping.items():
            filtered_commands = await self.filter_commands(cmds, sort=True)
            if not filtered_commands:
                continue
                
            cog_name = getattr(cog, "qualified_name", "No Category")
            command_list = "\n".join([f"`{self.context.clean_prefix}{cmd.name}` - {cmd.short_doc}" for cmd in filtered_commands])
            embed.add_field(name=f"**{cog_name}**", value=command_list, inline=False)
            
        embed.set_footer(text=f"Type {self.context.clean_prefix}help <command> for more info on a command.")
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(title=f"{cog.qualified_name} Help", description=cog.description, color=discord.Color.blue())
        
        filtered_commands = await self.filter_commands(cog.get_commands(), sort=True)
        if filtered_commands:
            command_list = "\n".join([f"`{self.context.clean_prefix}{cmd.name}` - {cmd.short_doc}" for cmd in filtered_commands])
            embed.add_field(name="Commands", value=command_list, inline=False)
            
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=f"Group: {group.qualified_name}", description=group.help or "No description provided.", color=discord.Color.blue())
        embed.add_field(name="Usage", value=f"`{self.get_command_signature(group)}`", inline=False)
        
        filtered_commands = await self.filter_commands(group.commands, sort=True)
        if filtered_commands:
            command_list = "\n".join([f"`{self.context.clean_prefix}{cmd.qualified_name}` - {cmd.short_doc}" for cmd in filtered_commands])
            embed.add_field(name="Subcommands", value=command_list, inline=False)
            
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=f"Command: {command.qualified_name}", description=command.help or "No description provided.", color=discord.Color.blue())
        embed.add_field(name="Usage", value=f"`{self.get_command_signature(command)}`", inline=False)
        
        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(command.aliases), inline=False)
            
        await self.get_destination().send(embed=embed)

class HelpCog(commands.Cog):
    """Help commands and information about the bot"""
    def __init__(self, bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = CustomHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help_command

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
