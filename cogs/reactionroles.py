import discord
from discord.ext import commands
import json
import asyncio
import datetime
import traceback

def get_current_semester():
    now = datetime.datetime.now()
    if 4 <= now.month <= 9:
        return "summer", now.year
    else:
        if now.month <= 3:
            return "winter", now.year - 1
        else:
            return "winter", now.year

class SemesterSelect(discord.ui.Select):
    def __init__(self, degree_type):
        self.degree_type = degree_type
        
        current_season, current_year = get_current_semester()
        options = []
        y = current_year
        s = current_season

        for i in range(25):
            label = f"SoSe {y}" if s == "summer" else f"WiSe {y}/{y+1-2000}"
            val = f"{s}_{y}"
            options.append(discord.SelectOption(label=label, description=f"Started in {label}", value=val))
            
            if s == "summer":
                s = "winter"
                y -= 1
            else:
                s = "summer"
                
        super().__init__(
            placeholder=f"Select your {degree_type.title()} Start Semester",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"semester_select_{degree_type}"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            selected_val = self.values[0]
            start_season, start_year_str = selected_val.split("_")
            start_year = int(start_year_str)
            
            current_season, current_year = get_current_semester()
            
            def get_sem_id(season, year):
                return year * 2 if season == "summer" else year * 2 + 1
                
            start_id = get_sem_id(start_season, start_year)
            curr_id = get_sem_id(current_season, current_year)
            
            sem = (curr_id - start_id) + 1
            if sem < 1: sem = 1
                
            role_prefix = "b_sem" if self.degree_type == "bachelor" else "m_sem"
            role_name = f"{role_prefix}{sem}"
            
            guild = interaction.guild
            member = interaction.user
            
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                role = await guild.create_role(name=role_name, reason="Dynamic semester role")
                    
            roles_to_remove = [r for r in member.roles if r.name.startswith(role_prefix) and r.name != role_name]
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
                    
            await member.add_roles(role)
            await interaction.followup.send(f"✅ Your role has been updated to **{role_name}**!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to assign role: {e}", ephemeral=True)

class SemesterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SemesterSelect("bachelor"))
        self.add_item(SemesterSelect("master"))

class ReactionRoles(commands.Cog):
    """Module for setting up interactive course/section reaction roles."""
    
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(SemesterView())

    def get_data(self):
        with open('data/structure.json', 'r') as f:
            return json.load(f)

    def save_data(self, data):
        with open('data/structure.json', 'w') as f:
            json.dump(data, f, indent=4)

    def get_all_course_refs(self, data):
        courses = []
        for key, value in data.items():
            if key in ["section", "reaction_messages", "reaction_channel", "semester_config"]:
                continue
            if isinstance(value, dict) and "courses" in value:
                courses.extend(value["courses"])
            elif isinstance(value, dict) and "role" in value and "id" in value:
                courses.append(value)
        return courses

    async def _prompt_missing_emojis(self, ctx, data, courses):
        missing_count = 0
        for c in courses:
            if "role" in c and "id" in c["role"] and not c["role"].get("emoji"):
                missing_count += 1
                
        if missing_count > 0:
            await ctx.send(f"Found **{missing_count}** courses without an assigned emoji. Please react to my prompts...")
            
        processed_ids = set()
        for course in courses:
            c_id = course.get("id")
            if not c_id or c_id in processed_ids:
                continue
            processed_ids.add(c_id)
            
            if course.get("disabled_rr"): 
                continue
            
            role_dict = course.get("role", {})
            if "id" not in role_dict or role_dict.get("emoji"):
                continue
                
            msg = await ctx.send(f"Please react to this message to assign an emoji for: **{course.get('name')}**")
            await msg.add_reaction("📚")
            
            def check(reaction, user):
                return user == ctx.author and reaction.message.id == msg.id
                
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                chosen_emoji = str(reaction.emoji)
                for c_ref in courses:
                    if c_ref.get("id") == c_id:
                        c_ref.setdefault("role", {})["emoji"] = chosen_emoji
                self.save_data(data)
                await msg.edit(content=f"✅ Set {chosen_emoji} for **{course.get('name')}**.")
            except asyncio.TimeoutError:
                await msg.edit(content=f"⏳ Timed out waiting. Using default 📚 for **{course.get('name')}**.")
                for c_ref in courses:
                    if c_ref.get("id") == c_id:
                        c_ref.setdefault("role", {})["emoji"] = "📚"
                self.save_data(data)
                
        return self.get_data(), self.get_all_course_refs(self.get_data())

    def _build_section_groups(self, data, courses):
        section_groups = {}
        processed_ids = set()
        for c in courses:
            if c.get("id") in processed_ids: continue
            processed_ids.add(c.get("id"))
            
            if "role" not in c or "id" not in c["role"]: continue
            if c.get("disabled_rr"): continue # skip disabled
                
            sec = c.get("section", "unknown")
            section_groups.setdefault(sec, []).append(c)
        return section_groups

    def _build_message_content(self, data, sec, sec_courses):
        sec_name = sec
        if "section" in data and sec in data["section"]:
            eng_name = next((n["name"] for n in data["section"][sec] if n["lang"] == "eng"), None)
            if eng_name: sec_name = eng_name
                
        lines = [f"### {sec_name.replace('-', ' ').upper()}"]
        for c in sec_courses:
            emoji = c.get("role", {}).get("emoji", "❓")
            mod = f" ({c['module']})" if "module" in c else ""
            lines.append(f"{emoji} **{c.get('name', 'Unknown').replace('-', ' ').title()}**{mod} - <#{c['id']}>")
        return "\n".join(lines)

    @commands.group(name='rr', invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def rr_group(self, ctx):
        """Reaction Roles configuration commands"""
        pass

    @rr_group.group(name='setup', invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def rr_setup(self, ctx):
        await ctx.send("Usage: `!rr setup courses` or `!rr setup semesters`")
        
    @rr_group.group(name='update', invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def rr_update(self, ctx):
        await ctx.send("Usage: `!rr update courses`")

    @rr_setup.command(name='semesters')
    @commands.has_permissions(manage_roles=True)
    async def rr_setup_semesters(self, ctx, target_channel: discord.TextChannel = None):
        target_channel = target_channel or ctx.channel
        data = self.get_data()
        
        sem_data = data.get("semester_config", {})
        if sem_data.get("channel_id") and sem_data.get("message_id"):
            old_chan = self.bot.get_channel(int(sem_data["channel_id"]))
            if old_chan:
                try:
                    msg = await old_chan.fetch_message(int(sem_data["message_id"]))
                    await msg.delete()
                except: pass
                            
        embed = discord.Embed(
            title="🎓 Choose your Starting Semester",
            description="Select the semester you began your degree to automatically receive your current semester role (e.g. `b_sem8`).\nThe calculation automatically updates as time passes!",
            color=0x3498db
        )
        
        try:
            msg = await target_channel.send(embed=embed, view=SemesterView())
            data["semester_config"] = {"channel_id": str(target_channel.id), "message_id": str(msg.id)}
            self.save_data(data)
            await ctx.send(f"✅ Dynamic dropdown UI deployed to {target_channel.mention}!")
        except Exception as e:
            await ctx.send(f"❌ Failed to post semester messages: {e}")

    @rr_setup.command(name='courses')
    @commands.has_permissions(manage_roles=True)
    async def rr_setup_courses(self, ctx, target_channel: discord.TextChannel = None):
        target_channel = target_channel or ctx.channel
        data = self.get_data()
        courses = self.get_all_course_refs(data)
        
        try:
            data, courses = await self._prompt_missing_emojis(ctx, data, courses)
            
            # Clean old messages
            if "reaction_channel" in data and "reaction_messages" in data:
                old_chan = self.bot.get_channel(int(data["reaction_channel"]))
                if old_chan:
                    for msg_id in data["reaction_messages"].keys():
                        try:
                            old_msg = await old_chan.fetch_message(int(msg_id))
                            await old_msg.delete()
                        except: pass
                                
            data["reaction_messages"] = {}
            data["reaction_channel"] = str(target_channel.id)

            section_groups = self._build_section_groups(data, courses)
            
            for sec, sec_courses in section_groups.items():
                if not sec_courses: continue
                msg_content = self._build_message_content(data, sec, sec_courses)
                
                msg = await target_channel.send(msg_content)
                data["reaction_messages"][str(msg.id)] = sec
                self.save_data(data)
                
                for c in sec_courses:
                    emoji = c.get("role", {}).get("emoji")
                    if emoji:
                        try: await msg.add_reaction(emoji)
                        except: pass
            
            await ctx.send(f"✅ Reaction roles setup complete in {target_channel.mention}!")
        except Exception as e:
            await ctx.send(f"❌ **Error during setup:** `{e}`\n```py\n{traceback.format_exc()[-500:]}\n```")

    @rr_update.command(name='courses')
    @commands.has_permissions(manage_roles=True)
    async def rr_update_courses(self, ctx, target_channel: discord.TextChannel = None):
        data = self.get_data()
        
        if "reaction_messages" not in data or not data.get("reaction_channel"):
            await ctx.send("❌ No existing setup found. Run `!rr setup courses` first.")
            return

        target_channel = self.bot.get_channel(int(data["reaction_channel"]))
        if not target_channel:
            await ctx.send("❌ Old setup channel not found. Please run `!rr setup courses` again.")
            return

        courses = self.get_all_course_refs(data)
        
        try:
            data, courses = await self._prompt_missing_emojis(ctx, data, courses)
            section_groups = self._build_section_groups(data, courses)
            
            # Maps current DB section string to message IDs
            sec_to_msg = {v: k for k, v in data.get("reaction_messages", {}).items()}
            new_reaction_messages = {}

            for sec, sec_courses in section_groups.items():
                if not sec_courses: continue
                msg_content = self._build_message_content(data, sec, sec_courses)
                
                if sec in sec_to_msg:
                    # Message exists, lets edit!
                    try:
                        msg_id = int(sec_to_msg[sec])
                        msg = await target_channel.fetch_message(msg_id)
                        await msg.edit(content=msg_content)
                        new_reaction_messages[str(msg.id)] = sec
                        
                        # Add new reactions, leave old ones
                        for c in sec_courses:
                            emoji = c.get("role", {}).get("emoji")
                            if emoji:
                                try: await msg.add_reaction(emoji)
                                except: pass
                    except discord.NotFound:
                        # Message deleted manually, post a new one
                        msg = await target_channel.send(msg_content)
                        new_reaction_messages[str(msg.id)] = sec
                        for c in sec_courses:
                            if c.get("role", {}).get("emoji"):
                                try: await msg.add_reaction(c["role"]["emoji"])
                                except: pass
                else:
                    # Brand new section!
                    msg = await target_channel.send(msg_content)
                    new_reaction_messages[str(msg.id)] = sec
                    for c in sec_courses:
                        if c.get("role", {}).get("emoji"):
                            try: await msg.add_reaction(c["role"]["emoji"])
                            except: pass

            data["reaction_messages"] = new_reaction_messages
            self.save_data(data)
            await ctx.send("✅ Reaction roles updated seamlessly!")
            
        except Exception as e:
            await ctx.send(f"❌ **Error during update:** `{e}`\n```py\n{traceback.format_exc()[-500:]}\n```")

    @rr_group.command(name='disable')
    @commands.has_permissions(manage_roles=True)
    async def rr_disable(self, ctx, *, course_name: str):
        data = self.get_data()
        courses = self.get_all_course_refs(data)
        
        target = next((c for c in courses if course_name.lower() in c.get("name", "").lower()), None)
        if not target:
            return await ctx.send(f"❌ Course matching `{course_name}` not found.")
            
        for c_ref in courses:
            if c_ref.get("id") == target["id"]:
                c_ref["disabled_rr"] = True
                
        self.save_data(data)
        await ctx.send(f"✅ Disabled **{target.get('name')}**. Run `!rr update courses` to apply changes visually.")
        
    @rr_group.command(name='enable')
    @commands.has_permissions(manage_roles=True)
    async def rr_enable(self, ctx, *, course_name: str):
        data = self.get_data()
        courses = self.get_all_course_refs(data)
        
        target = next((c for c in courses if course_name.lower() in c.get("name", "").lower()), None)
        if not target:
            return await ctx.send(f"❌ Course matching `{course_name}` not found.")
            
        for c_ref in courses:
            if c_ref.get("id") == target["id"]:
                c_ref["disabled_rr"] = False
                
        self.save_data(data)
        await ctx.send(f"✅ Enabled **{target.get('name')}**. Run `!rr update courses` to apply changes visually.")

    @rr_group.command(name='editemoji')
    @commands.has_permissions(manage_roles=True)
    async def rr_editemoji(self, ctx, *, course_name: str):
        data = self.get_data()
        courses = self.get_all_course_refs(data)
        
        target = next((c for c in courses if course_name.lower() in c.get("name", "").lower()), None)
        if not target:
            return await ctx.send(f"❌ Course matching `{course_name}` not found.")
            
        msg = await ctx.send(f"Please react to this message to assign a new emoji for: **{target.get('name')}**")
        await msg.add_reaction("📚")
        
        def check(reaction, user):
            return user == ctx.author and reaction.message.id == msg.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            chosen_emoji = str(reaction.emoji)
            
            for c_ref in courses:
                if c_ref.get("id") == target["id"]:
                    c_ref.setdefault("role", {})["emoji"] = chosen_emoji
                    
            self.save_data(data)
            await ctx.send(f"✅ Set {chosen_emoji} for {target.get('name')}. Run `!rr update courses` to apply changes.")
        except asyncio.TimeoutError:
            await ctx.send("⏳ Timed out.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id: return
        await self.handle_reaction(payload, True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.bot.user.id: return
        await self.handle_reaction(payload, False)

    async def handle_reaction(self, payload, is_add):
        data = self.get_data()
        reaction_messages = data.get("reaction_messages", {})
        
        if str(payload.message_id) not in reaction_messages: return
            
        section = reaction_messages[str(payload.message_id)]
        emoji_str = str(payload.emoji)
        courses = self.get_all_course_refs(data)
        
        role_id = next((c.get("role", {}).get("id") for c in courses 
                       if c.get("section") == section 
                       and c.get("role", {}).get("emoji") == emoji_str
                       and not c.get("disabled_rr")), None)
                       
        if not role_id: return
            
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        role = guild.get_role(role_id)
        if not member or not role: return
            
        try:
            if is_add: await member.add_roles(role)
            else: await member.remove_roles(role)
        except: pass

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
