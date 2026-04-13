"""
Course sync cog - Module for syncing channels and setting links
"""
import discord
from discord.ext import commands, tasks
import json
import os
import datetime

class CourseSync(commands.Cog):
    """Commands for course channels and daily synchronization"""
    
    def __init__(self, bot):
        self.bot = bot
        self.startup_sync_done = False
        self.daily_sync.start()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.startup_sync_done:
            print("Bot is ready. Running startup course sync...")
            await self.perform_sync()
            self.startup_sync_done = True
        
    def cog_unload(self):
        self.daily_sync.cancel()

    def generate_topic(self, description: str, links: list) -> str:
        """Helper to generate the discord channel topic string."""
        topic_parts = []
        if description:
            topic_parts.append(description)
            
        if links:
            links_text = " • ".join([f"{link['name'].upper()}: {link['link']}" for link in links])
            topic_parts.append(links_text)
            
        return "\n\n".join(topic_parts)[:1024] # Discord channel topic limit is 1024 chars

    @commands.group(name='setlink', invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def set_link(self, ctx):
        """
        Set course links.
        Usage: !setlink olat <url> OR !setlink kis <url>
        """
        await ctx.send("Usage: `!setlink olat <url>` or `!setlink kis <url>`")

    @set_link.command(name='olat')
    @commands.has_permissions(manage_channels=True)
    async def _olat(self, ctx, url: str):
        await self._update_link(ctx, "olat", url)

    @set_link.command(name='kis')
    @commands.has_permissions(manage_channels=True)
    async def _kis(self, ctx, url: str):
        await self._update_link(ctx, "office-kis", url)

    async def _update_link(self, ctx, link_name: str, url: str):
        if not os.path.exists('data/structure.json'):
            await ctx.send("❌ `data/structure.json` not found.")
            return
            
        with open('data/structure.json', 'r') as f:
            data = json.load(f)
            
        # Find the current channel in data
        found = False
        for season, content in data.items():
            for course in content.get('courses', []):
                if course.get('id') == ctx.channel.id:
                    # Found the course
                    found = True
                    
                    # Update links
                    links = course.get('links', [])
                    # Remove the old link if it exists
                    links = [l for l in links if l['name'] != link_name]
                    links.append({"name": link_name, "link": url})
                    course['links'] = links
                    
                    description = course.get('description', '')
                    new_topic = self.generate_topic(description, links)
                    
                    try:
                        await ctx.channel.edit(topic=new_topic)
                    except Exception as e:
                        await ctx.send(f"❌ Failed to update channel topic: {e}")
                        return
                    
                    break
            if found:
                break
                
        if not found:
            await ctx.send("❌ This channel is not registered as a course in `data/structure.json`.")
            return
            
        with open('data/structure.json', 'w') as f:
            json.dump(data, f, indent=4)
            
        await ctx.send(f"✅ Updated {link_name} link and channel topic!")

    # Run every day at 6:00 AM UTC (before cycle hook potentially)
    @tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=datetime.timezone.utc))
    async def daily_sync(self):
        """Daily background job to sync Discord edits -> JSON -> Roles"""
        await self.perform_sync()

    async def perform_sync(self):
        """Core sync logic to run on command, startup, or daily"""
        print(f"[{datetime.datetime.now(datetime.timezone.utc)}] Running course sync...")
        if not os.path.exists('data/structure.json'):
            return
            
        with open('data/structure.json', 'r') as f:
            data = json.load(f)
            
        if not self.bot.guilds:
            return
            
        guild = self.bot.guilds[0]
        
        changes_made = False
        
        for season, season_data in data.items():
            for course in season_data.get("courses", []):
                channel_id = course.get("id")
                channel = guild.get_channel(channel_id)
                
                # If channel is found, sync FROM it
                if channel:
                    
                    # 1. Sync Channel Name -> Course Name & Role Name
                    if course.get("name") != channel.name:
                        print(f"Syncing name change: {course.get('name')} -> {channel.name}")
                        course["name"] = channel.name
                        changes_made = True
                        
                        # Apply name to Role if it exists
                        role_info = course.get("role", {})
                        if "id" in role_info:
                            role = guild.get_role(role_info["id"])
                            if role and role.name != channel.name:
                                try:
                                    await role.edit(name=channel.name)
                                    course["role"]["name"] = channel.name
                                except Exception as e:
                                    print(f"Failed to edit role name for {channel.name}: {e}")
                                    
                    # 2. Sync Role Color -> JSON
                    role_info = course.get("role", {})
                    if "id" in role_info:
                        role = guild.get_role(role_info["id"])
                        if role:
                            # Use hex logic e.g., #FFFFFF
                            color_hex = f"#{role.color.value:06x}" if role.color.value else "#000000"
                            if role_info.get("color") != color_hex:
                                print(f"Syncing color change for {channel.name}: {role_info.get('color')} -> {color_hex}")
                                course["role"]["color"] = color_hex
                                changes_made = True
                                
                    # 3. Sync Channel Topic -> JSON Description
                    # Note: We need to strip our generated links from the topic to just save the pure description
                    current_topic = channel.topic or ""
                    links_text = ""
                    links = course.get("links", [])
                    if links:
                        links_text = " • ".join([f"{link['name'].upper()}: {link['link']}" for link in links])
                        
                    # Pure description is whatever came before the links if links exist
                    pure_desc = current_topic
                    if links_text and current_topic.endswith(links_text):
                        # Attempt to split our generated delimiter
                        pure_desc = current_topic[:-(len(links_text) + 2)].strip() # +2 for "\n\n"
                        
                    if course.get("description", "") != pure_desc:
                        print(f"Syncing description change for {channel.name}")
                        course["description"] = pure_desc
                        changes_made = True
                        
                        # Re-apply full topic just to be 100% clean
                        new_topic = self.generate_topic(pure_desc, links)
                        if new_topic != current_topic:
                            try:
                                await channel.edit(topic=new_topic)
                            except Exception as e:
                                print(f"Failed to enforce topic structure for {channel.name}: {e}")

        if changes_made:
            with open('data/structure.json', 'w') as f:
                json.dump(data, f, indent=4)
            print("Daily sync completed and saved to data/structure.json.")
        else:
            print("Daily sync completed. No manual edits found.")

    @daily_sync.before_loop
    async def before_sync(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(CourseSync(bot))
