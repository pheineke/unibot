"""
Temporary script to populate structure.json with channels from the Discord server.
"""
import discord
import json
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

class TempClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        
        # Load the existing structure
        with open('data/structure.json', 'r') as f:
            data = json.load(f)
            
        guild = self.guilds[0] # Assumes the bot is in the server we want
        print(f'Syncing channels for guild: {guild.name}')
        
        for season in ["summer", "winter"]:
            cat_info = data.get(season, {}).get("category")
            if not cat_info:
                continue
                
            cat_id = cat_info.get("id")
            category = guild.get_channel(cat_id)
            
            if not category:
                print(f"Category {cat_id} not found for {season}.")
                continue
                
            # Clear existing courses or keep a mapping
            existing_courses = {c["id"]: c for c in data[season].get("courses", [])}
            new_courses = []
            
            for channel in category.text_channels:
                # Try to find an existing course to keep links/role info, else create new
                course_data = existing_courses.get(channel.id, {
                    "name": channel.name,
                    "id": channel.id,
                    "role": {},
                    "links": []
                })
                # Update name just in case it changed
                course_data["name"] = channel.name
                
                # Simple heuristic for roles: find a role with the same name as the channel
                role = discord.utils.get(guild.roles, name=channel.name)
                if role:
                    course_data["role"] = {"name": role.name, "id": role.id}
                    
                new_courses.append(course_data)
                
            data[season]["courses"] = new_courses
            print(f"Updated {season} with {len(new_courses)} courses.")

        with open('data/structure.json', 'w') as f:
            json.dump(data, f, indent=4)
            
        print("Updated structure.json successfully.")
        await self.close()

if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_bot_token_here":
        print("Please set your DISCORD_TOKEN in the .env file.")
    else:
        client = TempClient()
        client.run(TOKEN)
