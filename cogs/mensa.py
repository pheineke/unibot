import discord
from discord.ext import commands, tasks
import json
import os
import datetime

class Mensa(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_reset_date = None
        self.startup_check_done = False
        self.check_reset_time.start()

    def get_data(self):
        if not os.path.exists('data/mensa.json'):
            return None
        with open('data/mensa.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_data(self, data):
        with open('data/mensa.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.startup_check_done:
            print("Bot is ready. Checking Mensa schedule embed...")
            await self.update_embed()
            self.startup_check_done = True

    def cog_unload(self):
        self.check_reset_time.cancel()

    @tasks.loop(minutes=1)
    async def check_reset_time(self):
        data = self.get_data()
        if not data:
            return
            
        reset_time = data.get("reset-time", "14:00")
        now = datetime.datetime.now()
        
        if now.strftime("%H:%M") == reset_time:
            if self.last_reset_date != now.date():
                print(f"[{now}] Resetting Mensa schedule...")
                self.last_reset_date = now.date()
                
                for slot in data.get("slots", {}).values():
                    slot["users"] = []
                self.save_data(data)
                
                channel_id = data.get("channel", {}).get("id")
                msg_id = data.get("message_id")
                if channel_id and msg_id:
                    channel = self.bot.get_channel(int(channel_id))
                    if channel:
                        try:
                            msg = await channel.fetch_message(int(msg_id))
                            await msg.clear_reactions()
                            for slot in data.get("slots", {}).values():
                                if "emoji" in slot:
                                    await msg.add_reaction(slot["emoji"])
                        except discord.NotFound:
                            pass
                await self.update_embed()

    @check_reset_time.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    async def update_embed(self):
        data = self.get_data()
        if not data:
            return
            
        channel_id = data.get("channel", {}).get("id")
        if not channel_id:
            return
            
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return

        title = data.get("embed", {}).get("title", "Mensa Schedule")
        desc = data.get("embed", {}).get("description", "React below!")
        embed = discord.Embed(title=title, description=desc, color=discord.Color.orange())
        
        for slot_key, slot_data in data.get("slots", {}).items():
            time_str = slot_data.get("time", "Unknown")
            emoji = slot_data.get("emoji", "❓")
            users = slot_data.get("users", [])
            
            value = "\n".join([f"<@{user_id}>" for user_id in users]) if users else "_Nobody yet_"
            embed.add_field(name=f"{emoji} {time_str}", value=value, inline=True)

        msg_id = data.get("message_id")
        msg = None
        if msg_id:
            try:
                msg = await channel.fetch_message(int(msg_id))
            except discord.NotFound:
                msg = None
                
        if msg:
            await msg.edit(embed=embed)
        else:
            msg = await channel.send(embed=embed)
            data["message_id"] = msg.id
            self.save_data(data)
            for slot_data in data.get("slots", {}).values():
                emoji = slot_data.get("emoji")
                if emoji:
                    try:
                        await msg.add_reaction(emoji)
                    except:
                        pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        await self.handle_reaction(payload, True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        await self.handle_reaction(payload, False)

    async def handle_reaction(self, payload, is_add):
        data = self.get_data()
        if not data:
            return
            
        msg_id = data.get("message_id")
        if not msg_id or payload.message_id != int(msg_id):
            return
            
        emoji_str = str(payload.emoji)
        changed = False
        
        for slot_key, slot_data in data.get("slots", {}).items():
            if slot_data.get("emoji") == emoji_str:
                users = slot_data.get("users", [])
                user_id = payload.user_id
                
                if is_add and user_id not in users:
                    users.append(user_id)
                    changed = True
                elif not is_add and user_id in users:
                    users.remove(user_id)
                    changed = True
                    
                slot_data["users"] = users
                break
                
        if changed:
            self.save_data(data)
            await self.update_embed()

async def setup(bot):
    await bot.add_cog(Mensa(bot))
