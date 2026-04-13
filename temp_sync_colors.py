import discord
import json
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class ColorSyncClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        super().__init__(intents=intents)

    async def on_ready(self):
        await self.wait_until_ready()
        print(f'Logged in as {self.user}')
        if not os.path.exists('data/structure.json'):
            await self.close()
            return

        with open('data/structure.json', 'r') as f:
            data = json.load(f)
            
        guild = self.guilds[0]
        # properly fetch guild if needed, but wait_until_ready should cache roles
        roles = await guild.fetch_roles()
        role_map = {r.id: r for r in roles}
        
        changes = 0

        for season, season_data in data.items():
            if not isinstance(season_data, dict):
                continue
            for course in season_data.get("courses", []):
                role_info = course.get("role", {})
                if "id" in role_info:
                    role = role_map.get(role_info["id"])
                    if role:
                        color_hex = f"#{role.color.value:06x}" if role.color.value else "#000000"
                        if role_info.get("color") != color_hex:
                            print(f"Syncing color {role.name}: {role_info.get('color')} -> {color_hex}")
                            course["role"]["color"] = color_hex
                            changes += 1
                    else:
                        print(f"Role {role_info['id']} not found on server")

        if changes > 0:
            with open('data/structure.json', 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Saved {changes} color changes to structure.json")
        else:
            print("No color changes found.")

        await self.close()

if __name__ == "__main__":
    client = ColorSyncClient()
    client.run(TOKEN)
