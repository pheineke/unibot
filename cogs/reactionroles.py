import discord
from discord.ext import commands
import json
import asyncio
import datetime

class ReactionRoles(commands.Cog):
    """Module for setting up interactive course/section reaction roles."""
    
    def __init__(self, bot):
        self.bot = bot

    def get_data(self):
        with open('data/structure.json', 'r') as f:
            return json.load(f)

    def save_data(self, data):
        with open('data/structure.json', 'w') as f:
            json.dump(data, f, indent=4)

    def get_all_course_refs(self, data):
        """Returns a list of all course dictionaries to modify them by ref"""
        courses = []
        for key, value in data.items():
            if key == "section" or key.startswith("reaction") or key == "semester_roles":
                continue
            if isinstance(value, dict) and "courses" in value:
                courses.extend(value["courses"])
            elif isinstance(value, dict) and "role" in value and "id" in value:
                courses.append(value)
        return courses

    @commands.group(name='rr', invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def rr_group(self, ctx):
        """Reaction Roles commands"""
        await ctx.send("Usage:\n`!rr setup <#channel>` - Setup or update messages\n`!rr editemoji <course_name>` - Change emoji for a course\n`!rr semesters <#channel>` - Setup semester calculation roles")

    @rr_group.command(name='semesters')
    @commands.has_permissions(manage_roles=True)
    async def rr_semesters(self, ctx, target_channel: discord.TextChannel):
        """
        Builds the semester role selection messages.
        Usage: !rr semesters #choose-roles
        """
        data = self.get_data()
        sem_data = data.get("semester_roles", {})
        if not sem_data:
            await ctx.send("No `semester_roles` configured in structure.json!")
            return

        # Clean old messages
        old_b = sem_data.get("bachelor_message_id")
        old_m = sem_data.get("master_message_id")
        old_chan_id = sem_data.get("channel_id")
        
        if old_chan_id:
            old_chan = self.bot.get_channel(int(old_chan_id))
            if old_chan:
                for mid in [old_b, old_m]:
                    if mid:
                        try:
                            msg = await old_chan.fetch_message(int(mid))
                            await msg.delete()
                        except:
                            pass
                            
        # Post Bachelor message
        b_lines = ["### BACHELOR START SEMESTER", "React below to set the semester you started your Bachelor:"]
        b_options = sem_data.get("bachelor", {}).get("options", [])
        for opt in b_options:
            b_lines.append(f"{opt['emoji']} **{opt['label']}**")
            
        b_msg = await target_channel.send("\n".join(b_lines))
        for opt in b_options:
            try:
                await b_msg.add_reaction(opt['emoji'])
            except Exception:
                pass
                
        # Post Master message 
        m_lines = ["### MASTER START SEMESTER", "React below to set the semester you started your Master:"]
        m_options = sem_data.get("master", {}).get("options", [])
        for opt in m_options:
            m_lines.append(f"{opt['emoji']} **{opt['label']}**")
            
        m_msg = await target_channel.send("\n".join(m_lines))
        for opt in m_options:
            try:
                await m_msg.add_reaction(opt['emoji'])
            except Exception:
                pass
                
        # Save to data
        sem_data["channel_id"] = str(target_channel.id)
        sem_data["bachelor_message_id"] = str(b_msg.id)
        sem_data["master_message_id"] = str(m_msg.id)
        data["semester_roles"] = sem_data
        self.save_data(data)
        
        await ctx.send(f"✅ Semester roles setup complete in {target_channel.mention}!")

    @rr_group.command(name='setup')
    @commands.has_permissions(manage_roles=True)
    async def rr_setup(self, ctx, target_channel: discord.TextChannel):
        """
        Interactively builds the reaction role directory inside a specific channel.
        If any courses are missing emojis, the bot will prompt you to set them first.
        It then deletes any old reaction messages and posts a fresh set grouped by section.
        Usage: !rr setup #choose-roles
        """
        data = self.get_data()
        courses = self.get_all_course_refs(data)
        
        # 1. Check for missing emojis and prompt
        missing_count = 0
        processed_check_ids = set()
        for c in courses:
            c_id = c.get("id")
            if not c_id or c_id in processed_check_ids:
                continue
            processed_check_ids.add(c_id)
            if "role" in c and "id" in c["role"] and (not c["role"].get("emoji")):
                missing_count += 1
        
        if missing_count > 0:
            await ctx.send(f"Found **{missing_count}** courses without an assigned emoji. I will prompt you for each now. React to my messages!")
            
        processed_ids = set()
        for course in courses:
            c_id = course.get("id")
            if not c_id or c_id in processed_ids:
                continue
            processed_ids.add(c_id)
            
            role_dict = course.get("role", {})
            if "id" not in role_dict:
                continue
                
            if "emoji" not in role_dict or not role_dict["emoji"]:
                msg_content = f"Please react to this message to assign an emoji for: **{course.get('name')}**"
                msg = await ctx.send(msg_content)
                await msg.add_reaction("📚")
                
                def check(reaction, user):
                    return user == ctx.author and reaction.message.id == msg.id
                    
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    chosen_emoji = str(reaction.emoji)
                    
                    # Update explicitly ALL references of this course
                    for c_ref in courses:
                        if c_ref.get("id") == c_id:
                            if "role" not in c_ref:
                                c_ref["role"] = {}
                            c_ref["role"]["emoji"] = chosen_emoji
                            
                    self.save_data(data) # save immediately just in case
                    await msg.edit(content=f"✅ Set {chosen_emoji} for **{course.get('name')}**.")
                except asyncio.TimeoutError:
                    await msg.edit(content=f"⏳ Timed out waiting. Using default 📚 for **{course.get('name')}**.")
                    for c_ref in courses:
                        if c_ref.get("id") == c_id:
                            if "role" not in c_ref:
                                c_ref["role"] = {}
                            c_ref["role"]["emoji"] = "📚"
                    self.save_data(data)

        # Reload data as we might have modified it heavily
        data = self.get_data()
        courses = self.get_all_course_refs(data)
        
        # 2. Delete old messages if they exist
        if "reaction_messages" in data:
            old_channel_id = data.get("reaction_channel")
            if old_channel_id:
                old_chan = self.bot.get_channel(int(old_channel_id))
                if old_chan:
                    for msg_id in data["reaction_messages"].keys():
                        try:
                            old_msg = await old_chan.fetch_message(int(msg_id))
                            await old_msg.delete()
                        except:
                            pass
                            
        data["reaction_messages"] = {}
        data["reaction_channel"] = str(target_channel.id)

        # 3. Post messages grouped by section
        section_groups = {}
        processed_ids = set()
        for c in courses:
            if c.get("id") in processed_ids:
                continue
            processed_ids.add(c.get("id"))
            
            if "role" not in c or "id" not in c["role"]:
                continue
                
            sec = c.get("section", "unknown")
            if sec not in section_groups:
                section_groups[sec] = []
            section_groups[sec].append(c)

        for sec, sec_courses in section_groups.items():
            # lookup section name
            sec_name = sec
            if "section" in data and sec in data["section"]:
                sec_list = data["section"][sec]
                eng_name = next((n["name"] for n in sec_list if n["lang"] == "eng"), None)
                if eng_name:
                    sec_name = eng_name
            
            # format message
            lines = [f"### {sec_name.replace('-', ' ').upper()}"]
            for c in sec_courses:
                emoji = c.get("role", {}).get("emoji", "❓")
                mod = f" ({c['module']})" if "module" in c else ""
                lines.append(f"{emoji} **{c.get('name', 'Unknown').replace('-', ' ').title()}**{mod} - <#{c['id']}>")
                
            msg_content = "\n".join(lines)
            
            if len(sec_courses) > 0:
                msg = await target_channel.send(msg_content)
                # save to global config matching exactly the section
                data["reaction_messages"][str(msg.id)] = sec
                self.save_data(data) # save immediately so listener sees it
                
                # add reactions to the message
                for c in sec_courses:
                    emoji = c.get("role", {}).get("emoji")
                    if emoji:
                        try:
                            await msg.add_reaction(emoji)
                        except Exception as e:
                            print(f"Failed to add reaction {emoji}: {e}")
                            
        await ctx.send(f"✅ Reaction roles setup complete in {target_channel.mention}!")

    @rr_group.command(name='editemoji')
    @commands.has_permissions(manage_roles=True)
    async def rr_editemoji(self, ctx, *, course_name: str):
        """
        Manually replace or update an emoji for a specific course by reacting to the prompt.
        Usage: !rr editemoji software development
        After setting, you must run !rr setup again to visually refresh the embeds!
        """
        data = self.get_data()
        courses = self.get_all_course_refs(data)
        
        target_course = None
        for c in courses:
            if course_name.lower() in c.get("name", "").lower():
                target_course = c
                break
                
        if not target_course:
            await ctx.send(f"❌ Course matching `{course_name}` not found.")
            return
            
        msg = await ctx.send(f"Please react to this message to assign a new emoji for: **{target_course.get('name')}**")
        await msg.add_reaction("📚")
        
        def check(reaction, user):
            return user == ctx.author and reaction.message.id == msg.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            chosen_emoji = str(reaction.emoji)
            
            c_id = target_course["id"]
            for c_ref in courses:
                if c_ref.get("id") == c_id:
                    if "role" not in c_ref:
                        c_ref["role"] = {}
                    c_ref["role"]["emoji"] = chosen_emoji
                    
            self.save_data(data)
            await ctx.send(f"✅ Set {chosen_emoji} for {target_course.get('name')}. Run `!rr setup <#channel>` to update the messages visually.")
        except asyncio.TimeoutError:
            await ctx.send("⏳ Timed out.")

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

    async def handle_semester_reaction(self, payload, degree_type, is_add, data):
        emoji_str = str(payload.emoji)
        options = data.get("semester_roles", {}).get(degree_type, {}).get("options", [])
        
        selected_opt = None
        for opt in options:
            if opt["emoji"] == emoji_str:
                selected_opt = opt
                break
                
        if not selected_opt:
            return
            
        now = datetime.datetime.now()
        if 4 <= now.month <= 9:
            current_season = "summer"
            current_year = now.year
        else:
            current_season = "winter"
            if now.month <= 3:
                current_year = now.year - 1
            else:
                current_year = now.year
                
        def get_id(season, year):
            return year * 2 if season == "summer" else year * 2 + 1
            
        start_id = get_id(selected_opt["season"], selected_opt["year"])
        curr_id = get_id(current_season, current_year)
        
        sem = (curr_id - start_id) + 1
        if sem < 1:
            sem = 1
            
        role_prefix = "b_sem" if degree_type == "bachelor" else "m_sem"
        role_name = f"{role_prefix}{sem}"
        
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not guild or not member:
            return
            
        role = discord.utils.get(guild.roles, name=role_name)
        
        # If adding reaction, we might need to create the role and remove old semantic roles
        if is_add:
            if not role:
                try:
                    role = await guild.create_role(name=role_name, reason="Dynamic semester role")
                except Exception as e:
                    print(f"Failed to create role {role_name}: {e}")
                    return
                    
            # Remove any already existing semester roles of this type
            roles_to_remove = [r for r in member.roles if r.name.startswith(role_prefix) and r.name != role_name]
            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove)
                except:
                    pass
                    
            try:
                await member.add_roles(role)
            except Exception as e:
                print(f"Failed to add dynamic role: {e}")
        else:
            # removing reaction
            if role and role in member.roles:
                try:
                    await member.remove_roles(role)
                except Exception as e:
                    print(f"Failed to remove dynamic role: {e}")

    async def handle_reaction(self, payload, is_add):
        data = self.get_data()
        msg_id_str = str(payload.message_id)
        
        # Check if it's a semester role message
        sem_data = data.get("semester_roles", {})
        if msg_id_str == sem_data.get("bachelor_message_id"):
            await self.handle_semester_reaction(payload, "bachelor", is_add, data)
            return
        elif msg_id_str == sem_data.get("master_message_id"):
            await self.handle_semester_reaction(payload, "master", is_add, data)
            return
        
        reaction_messages = data.get("reaction_messages", {})
        if msg_id_str not in reaction_messages:
            return
            
        section = reaction_messages[msg_id_str]
        emoji_str = str(payload.emoji)
        
        courses = self.get_all_course_refs(data)
        
        role_id = None
        for c in courses:
            if c.get("section") == section:
                if c.get("role", {}).get("emoji") == emoji_str:
                    role_id = c.get("role", {}).get("id")
                    break
                    
        if not role_id:
            return
            
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
            
        member = guild.get_member(payload.user_id)
        if not member:
            return
            
        role = guild.get_role(role_id)
        if not role:
            return
            
        try:
            if is_add:
                await member.add_roles(role)
            else:
                await member.remove_roles(role)
        except Exception as e:
            print(f"Failed to {'add' if is_add else 'remove'} role: {e}")

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
