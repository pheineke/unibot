"""
Temporary script to move Discord channels to the categories specified in structure.json.
"""
import discord
import json
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

class ApplyStructureClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        super().__init__(intents=intents)

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        
        if not os.path.exists('data/structure.json'):
            print("❌ structure.json not found!")
            await self.close()
            return

        with open('data/structure.json', 'r') as f:
            data = json.load(f)
            
        # Assuming the bot is only in one primary server for this script
        guild = self.guilds[0]
        print(f'Applying structure for guild: {guild.name}')
        
        for season, content in data.items():
            cat_info = content.get("category")
            courses = content.get("courses", [])
            
            if not cat_info or not courses:
                continue
                
            cat_id = cat_info.get("id")
            target_category = guild.get_channel(cat_id)
            
            if not target_category:
                print(f"❌ Category {cat_id} for {season} not found. Skipping.")
                continue
                
            print(f"\nProcessing {season} (Target Category: {target_category.name})")
            
            moved_count = 0
            for course in courses:
                channel_id = course.get("id")
                channel = guild.get_channel(channel_id)
                
                if not channel:
                    print(f"⚠️ Channel {course.get('name', channel_id)} not found.")
                    continue
                    
                if channel.category_id != target_category.id:
                    print(f"  Moving '{channel.name}' -> '{target_category.name}'...")
                    try:
                        await channel.edit(category=target_category)
                        moved_count += 1
                        # Short sleep to avoid rate limits when moving many channels
                        await asyncio.sleep(1)
                    except discord.Forbidden:
                        print(f"  ❌ Missing permissions to move '{channel.name}'.")
                    except Exception as e:
                        print(f"  ❌ Failed to move '{channel.name}': {e}")
                else:
                    print(f"  ✓ '{channel.name}' is already in '{target_category.name}'.")
                    
            print(f"Finished {season}: Moved {moved_count} channels.")

        print("\nStructure applied successfully.")
        await self.close()

if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_bot_token_here":
        print("Please set your DISCORD_TOKEN in the .env file.")
    else:
        client = ApplyStructureClient()
        client.run(TOKEN)
