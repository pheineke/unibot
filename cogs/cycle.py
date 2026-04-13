"""
Cycle cog - Module for cycling channels between categories
"""
import discord
from discord.ext import commands, tasks
import json
import os
import datetime
import asyncio

class Cycle(commands.Cog):
    """Commands for cycling channel categories"""
    
    def __init__(self, bot):
        self.bot = bot
        self.startup_check_done = False
        self.check_semester_start.start()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.startup_check_done:
            print("Bot is ready. Running startup semester check...")
            await self.perform_check()
            self.startup_check_done = True
        
    def cog_unload(self):
        self.check_semester_start.cancel()

    # Run every Monday at 8:00 AM UTC
    @tasks.loop(time=datetime.time(hour=8, minute=0, tzinfo=datetime.timezone.utc))
    async def check_semester_start(self):
        """Checks if it is Monday and if we have hit a semester start"""
        await self.perform_check()

    async def perform_check(self):
        """Core semester check logic"""
        today = datetime.datetime.now(datetime.timezone.utc).date()
        
        # 0 == Monday
        if today.weekday() != 0:
            return
            
        if not os.path.exists('data/structure.json'):
            return
            
        with open('data/structure.json', 'r') as f:
            data = json.load(f)
            
        guild = self.bot.guilds[0] # Assuming bot is in 1 main guild
        
        # We check both seasons to see if today is the start week
        for season in ["summer", "winter"]:
            if season not in data:
                continue
                
            start_str = data[season].get("start")
            if not start_str:
                continue
                
            try:
                day_str, month_str = start_str.split('-')
                start_day = int(day_str)
                start_month = int(month_str)
            except ValueError:
                continue
                
            # If today is in the start month and the day is within 7 days of the start_date
            # (which means it's the first Monday on or after the start date)
            if today.month == start_month and 0 <= (today.day - start_day) < 7:
                print(f"[{today}] Semester start detected for {season}! Cycling categories...")
                
                active_season = season
                inactive_season = "winter" if season == "summer" else "summer"
                
                # Retrieve the category IDs dynamically from the current season configuration
                # Assuming the active season ALWAYS gets mapped to the category listed in the active season's data.
                current_cat_id = data[active_season].get("category", {}).get("id")
                noncurrent_cat_id = data[inactive_season].get("category", {}).get("id")
                
                # Move active season courses to current_cat_id
                active_courses = data[active_season].get("courses", [])
                active_category = guild.get_channel(current_cat_id)
                if active_category:
                    for course in active_courses:
                        channel = guild.get_channel(course["id"])
                        if channel and channel.category_id != active_category.id:
                            try:
                                await channel.edit(category=active_category)
                                await asyncio.sleep(1)
                            except Exception as e:
                                print(f"Error moving channel {channel.name}: {e}")
                
                # Move inactive season courses to noncurrent_cat_id
                inactive_courses = data[inactive_season].get("courses", [])
                inactive_category = guild.get_channel(noncurrent_cat_id)
                if inactive_category:
                    for course in inactive_courses:
                        channel = guild.get_channel(course["id"])
                        if channel and channel.category_id != inactive_category.id:
                            try:
                                await channel.edit(category=inactive_category)
                                await asyncio.sleep(1)
                            except Exception as e:
                                print(f"Error moving channel {channel.name}: {e}")
                                
                # Since we found a matching season and processed it, we can break
                break

    @check_semester_start.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


    
    @commands.command(name='cycle')
    @commands.has_permissions(manage_channels=True)
    async def cycle_channels(self, ctx, from_season: str, to_season: str):
        """
        Cycle (move) channels from one season's category to another.
        Usage: !cycle summer winter
        """
        if not os.path.exists('data/structure.json'):
            await ctx.send("❌ `data/structure.json` not found.")
            return
            
        with open('data/structure.json', 'r') as f:
            data = json.load(f)
            
        if from_season not in data or to_season not in data:
            await ctx.send(f"❌ Both `{from_season}` and `{to_season}` must exist in data/structure.json")
            return
            
        to_category_id = data[to_season]["category"]["id"]
        to_category = ctx.guild.get_channel(to_category_id)
        
        if not to_category:
            await ctx.send(f"❌ The target category (ID: {to_category_id}) could not be found.")
            return

        courses = data[from_season].get("courses", [])
        if not courses:
            await ctx.send(f"⚠️ No courses found in `{from_season}` to cycle.")
            return
            
        msg = await ctx.send(f"🔄 Moving {len(courses)} channels from `{from_season}` to target category `{to_category.name}`...")
        
        success_count = 0
        for course in courses:
            channel = ctx.guild.get_channel(course["id"])
            if channel:
                try:
                    await channel.edit(category=to_category)
                    success_count += 1
                except discord.Forbidden:
                    await ctx.send(f"❌ Missing permissions to move {channel.mention}.")
                except Exception as e:
                    await ctx.send(f"❌ Failed to move {channel.mention}: {e}")
            else:
                await ctx.send(f"⚠️ Channel {course['name']} (ID: {course['id']}) not found.")
                
        await msg.edit(content=f"✅ Successfully moved {success_count}/{len(courses)} channels to **{to_category.name}**.")

async def setup(bot):
    await bot.add_cog(Cycle(bot))
