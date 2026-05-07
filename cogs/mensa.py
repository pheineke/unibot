import datetime
import json
import os
import re

import discord
from discord.ext import commands, tasks


HOUR_OPTIONS = ["11", "12", "13"]
MINUTE_OPTIONS = ["00", "15", "30", "45"]
VALID_TIMES = [
    "11:30",
    "11:45",
    "12:00",
    "12:15",
    "12:30",
    "12:45",
    "13:00",
    "13:15",
    "13:30",
    "13:45",
]
VALID_MINUTES_BY_HOUR = {
    "11": {"30", "45"},
    "12": set(MINUTE_OPTIONS),
    "13": set(MINUTE_OPTIONS),
}

MENSATIME_PATTERN = re.compile(r"^my\.mensatime\s*=\s*(none|now|\d{1,2}(?::\d{2})?)\s*$", re.IGNORECASE)


class MensaButton(discord.ui.Button):
    def __init__(self, cog, kind, value, row):
        style = discord.ButtonStyle.primary if kind == "hour" else discord.ButtonStyle.secondary
        super().__init__(
            style=style,
            label=value,
            custom_id=f"mensa:{kind}:{value}",
            row=row,
        )
        self.cog = cog
        self.kind = kind
        self.value = value

    async def callback(self, interaction: discord.Interaction):
        await self.cog.handle_selection(interaction, self.kind, self.value)


class MensaUserButton(discord.ui.Button):
    def __init__(self, cog, user_id, time_str, label, row):
        super().__init__(
            style=discord.ButtonStyle.success,
            label=label,
            custom_id=f"mensa:user:{user_id}",
            row=row,
        )
        self.cog = cog
        self.user_id = user_id
        self.time_str = time_str

    async def callback(self, interaction: discord.Interaction):
        await self.cog.handle_user_button(interaction, self.user_id, self.time_str)

class MensaLeaveButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Austragen",
            emoji="🚪",
            custom_id="mensa:leave",
            row=4,
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await self.cog.handle_leave_button(interaction)


class MensaView(discord.ui.View):
    def __init__(self, cog, data):
        super().__init__(timeout=None)
        for hour in HOUR_OPTIONS:
            self.add_item(MensaButton(cog, "hour", hour, row=0))
        for minute in MINUTE_OPTIONS:
            self.add_item(MensaButton(cog, "minute", minute, row=1))

        self._add_user_buttons(cog, data)
        self.add_item(MensaLeaveButton(cog))

    def _add_user_buttons(self, cog, data):
        channel_id = data.get("channel", {}).get("id")
        channel = cog.bot.get_channel(int(channel_id)) if channel_id else None
        guild = channel.guild if channel else None
        buckets = cog.build_buckets(data)

        row = 2
        for time_str in VALID_TIMES:
            user_ids = buckets.get(time_str, [])
            if not user_ids:
                continue

            user_id = user_ids[0]
            member = guild.get_member(user_id) if guild else None
            label = member.display_name if member else f"User {user_id}"
            label = label[:80]

            if row > 4:
                return

            self.add_item(MensaUserButton(cog, user_id, time_str, label, row=row))
            row += 1
            if row > 4:
                return


class Mensa(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_reset_date = None
        self.startup_check_done = False
        self.check_reset_time.start()

    def get_data(self):
        if not os.path.exists("data/mensa.json"):
            return None
        with open("data/mensa.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def save_data(self, data):
        with open("data/mensa.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def build_view(self):
        data = self.get_data() or {}
        return MensaView(self, data)

    def normalize_data(self, data):
        changed = False
        selections = data.setdefault("selections", {})

        legacy_slots = data.pop("slots", None)
        if legacy_slots:
            for slot_data in legacy_slots.values():
                time_str = slot_data.get("time")
                if time_str not in VALID_TIMES:
                    continue

                hour, minute = time_str.split(":", 1)
                for user_id in slot_data.get("users", []):
                    selections[str(user_id)] = {"hour": hour, "minute": minute}
                    changed = True

        return changed

    def is_valid_combination(self, hour, minute):
        return hour in VALID_MINUTES_BY_HOUR and minute in VALID_MINUTES_BY_HOUR[hour]

    def build_buckets(self, data):
        buckets = {time_str: [] for time_str in VALID_TIMES}

        for user_id, selection in data.get("selections", {}).items():
            hour = selection.get("hour")
            minute = selection.get("minute")
            if not self.is_valid_combination(hour, minute):
                continue

            buckets[f"{hour}:{minute}"].append(int(user_id))

        return buckets

    def parse_time_input(self, content):
        match = MENSATIME_PATTERN.match(content.strip())
        if not match:
            return None

        raw_value = match.group(1).lower()
        if raw_value == "none":
            return {"action": "clear"}

        if raw_value == "now":
            requested_time = datetime.datetime.now().time()
            return {
                "action": "set",
                "requested": requested_time,
                "closest": self.get_closest_timeslot(requested_time),
            }

        if ":" in raw_value:
            hour_part, minute_part = raw_value.split(":", 1)
        else:
            hour_part, minute_part = raw_value, "00"

        if len(hour_part) == 1:
            hour_part = f"0{hour_part}"

        try:
            parsed_time = datetime.time(int(hour_part), int(minute_part))
        except ValueError:
            return None

        return {
            "action": "set",
            "requested": parsed_time,
            "closest": self.get_closest_timeslot(parsed_time),
        }

    def get_closest_timeslot(self, requested_time):
        best_time_str = None
        best_distance = None

        for time_str in VALID_TIMES:
            slot_time = datetime.datetime.strptime(time_str, "%H:%M").time()
            distance = abs(
                (datetime.datetime.combine(datetime.date.today(), requested_time) -
                 datetime.datetime.combine(datetime.date.today(), slot_time)).total_seconds()
            )

            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_time_str = time_str

        return best_time_str

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.startup_check_done:
            print("Bot is ready. Checking Mensa schedule embed...")
            await self.update_embed()
            self.startup_check_done = True

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        parsed = self.parse_time_input(message.content)
        if not parsed:
            return

        data = self.get_data()
        if not data:
            return

        selections = data.setdefault("selections", {})
        user_key = str(message.author.id)

        if parsed["action"] == "clear":
            if user_key not in selections:
                try:
                    await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass
                return

            removed_selection = selections.pop(user_key)
            self.save_data(data)
            await self.update_embed()

            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

            channel = message.channel
            if isinstance(channel, discord.abc.Messageable):
                try:
                    await channel.send(
                        f"{message.author.mention} wurde aus {removed_selection.get('hour')}:{removed_selection.get('minute')} ausgetragen.",
                        delete_after=5,
                    )
                except discord.Forbidden:
                    pass
            return

        closest_time = parsed["closest"]
        if not closest_time:
            return

        hour, minute = closest_time.split(":", 1)
        selections[user_key] = {"hour": hour, "minute": minute}
        self.save_data(data)
        await self.update_embed()

        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        channel = message.channel
        if isinstance(channel, discord.abc.Messageable):
            try:
                await channel.send(
                    f"{message.author.mention} wurde auf {closest_time} gesetzt.",
                    delete_after=5,
                )
            except discord.Forbidden:
                pass

    def cog_unload(self):
        self.check_reset_time.cancel()

    async def reset_mensa(self, clear_last_reset=False):
        data = self.get_data()
        if not data:
            return False

        data["selections"] = {}
        self.save_data(data)

        await self.clear_mensa_channel_messages(data)

        if clear_last_reset:
            self.last_reset_date = None

        await self.update_embed()
        return True

    async def clear_mensa_channel_messages(self, data):
        channel_id = data.get("channel", {}).get("id")
        main_message_id = data.get("message_id")
        if not channel_id:
            return

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return

        if main_message_id:
            try:
                main_message_id = int(main_message_id)
            except (TypeError, ValueError):
                main_message_id = None

        try:
            await channel.purge(
                limit=None,
                check=lambda message: message.id != main_message_id,
            )
        except discord.Forbidden:
            pass

    @tasks.loop(minutes=1)
    async def check_reset_time(self):
        data = self.get_data()
        if not data:
            return

        reset_time = data.get("reset-time", "14:00")
        now = datetime.datetime.now()

        if now.strftime("%H:%M") == reset_time and self.last_reset_date != now.date():
            print(f"[{now}] Resetting Mensa schedule...")
            self.last_reset_date = now.date()
            await self.reset_mensa()

    @check_reset_time.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    async def update_embed(self):
        data = self.get_data()
        if not data:
            return

        if self.normalize_data(data):
            self.save_data(data)

        channel_id = data.get("channel", {}).get("id")
        if not channel_id:
            return

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return

        title = data.get("embed", {}).get("title", "Mensa Schedule")
        desc = data.get(
            "embed",
            {},
        ).get(
            "description",
            "Wähle zuerst eine Stunde und dann eine Minute. Die User darunter sind als Buttons dargestellt."
        )
        embed = discord.Embed(title=title, description=desc, color=discord.Color.orange())

        buckets = self.build_buckets(data)
        for time_str in VALID_TIMES:
            users = buckets.get(time_str, [])
            value = "\n".join([f"<@{user_id}>" for user_id in users]) if users else "_Nobody yet_"
            embed.add_field(name=time_str, value=value, inline=True)

        msg_id = data.get("message_id")
        msg = None
        if msg_id:
            try:
                msg = await channel.fetch_message(int(msg_id))
            except discord.NotFound:
                msg = None

        view = self.build_view()
        if msg:
            try:
                await msg.clear_reactions()
            except (discord.Forbidden, discord.NotFound):
                pass
            await msg.edit(embed=embed, view=view)
        else:
            msg = await channel.send(embed=embed, view=view)
            data["message_id"] = msg.id
            self.save_data(data)

    async def handle_selection(self, interaction, kind, value):
        data = self.get_data()
        if not data:
            await interaction.response.send_message("Mensa data not available.", ephemeral=True)
            return

        msg_id = data.get("message_id")
        if not msg_id or interaction.message is None or interaction.message.id != int(msg_id):
            await interaction.response.send_message("This Mensa message is no longer active.", ephemeral=True)
            return

        selections = data.setdefault("selections", {})
        user_key = str(interaction.user.id)
        selection = selections.setdefault(user_key, {"hour": None, "minute": None})
        note = None

        if kind == "hour":
            selection["hour"] = value
            if value == "11" and selection.get("minute") not in {None, "30", "45"}:
                selection["minute"] = None
                note = "Für 11 sind nur 30 und 45 möglich."
        else:
            current_hour = selection.get("hour")
            if current_hour == "11" and value in {"00", "15"}:
                await interaction.response.send_message(
                    "Für 11 kannst du nur 30 oder 45 wählen.",
                    ephemeral=True,
                )
                return
            selection["minute"] = value

        if selection.get("hour") and selection.get("minute") and not self.is_valid_combination(selection["hour"], selection["minute"]):
            await interaction.response.send_message(
                "Diese Uhrzeit ist nicht verfügbar. Bitte wähle eine andere Minute oder Stunde.",
                ephemeral=True,
            )
            return

        self.save_data(data)
        await interaction.response.defer(ephemeral=True)
        await self.update_embed()

        if selection.get("hour") and selection.get("minute"):
            message = f"Gespeichert: {selection['hour']}:{selection['minute']}."
        elif kind == "hour":
            message = f"Stunde auf {value} gesetzt. Jetzt Minute wählen."
        else:
            message = f"Minute auf {value} gesetzt. Jetzt Stunde wählen."

        if note:
            message = f"{message} {note}"

        await interaction.followup.send(message, ephemeral=True)

    async def handle_leave_button(self, interaction):
        data = self.get_data()
        if not data:
            await interaction.response.send_message("Mensa data not available.", ephemeral=True)
            return

        msg_id = data.get("message_id")
        if not msg_id or interaction.message is None or interaction.message.id != int(msg_id):
            await interaction.response.send_message("This Mensa message is no longer active.", ephemeral=True)
            return

        selections = data.setdefault("selections", {})
        user_key = str(interaction.user.id)
        if user_key not in selections:
            await interaction.response.send_message("Du bist aktuell in keinem Slot eingetragen.", ephemeral=True)
            return

        removed_selection = selections.pop(user_key)
        self.save_data(data)
        await interaction.response.defer(ephemeral=True)
        await self.update_embed()

        removed_time = f"{removed_selection.get('hour')}:{removed_selection.get('minute')}"
        await interaction.followup.send(f"Du wurdest aus {removed_time} ausgetragen.", ephemeral=True)

    async def handle_user_button(self, interaction, target_user_id, time_str):
        data = self.get_data()
        if not data:
            await interaction.response.send_message("Mensa data not available.", ephemeral=True)
            return

        msg_id = data.get("message_id")
        if not msg_id or interaction.message is None or interaction.message.id != int(msg_id):
            await interaction.response.send_message("This Mensa message is no longer active.", ephemeral=True)
            return

        selections = data.setdefault("selections", {})

        hour, minute = time_str.split(":", 1)
        current_selection = selections.get(str(interaction.user.id))
        if current_selection and current_selection.get("hour") == hour and current_selection.get("minute") == minute:
            await interaction.response.send_message(
                f"Du bist schon bei {time_str} eingetragen.",
                ephemeral=True,
            )
            return

        selections[str(interaction.user.id)] = {"hour": hour, "minute": minute}
        self.save_data(data)
        await interaction.response.defer(ephemeral=True)
        await self.update_embed()

        await interaction.followup.send(f"Du bist jetzt bei {time_str} eingetragen.", ephemeral=True)

    @commands.command(name="mensa_force_reset", aliases=["mensareset", "mensa-reset"])
    @commands.has_permissions(administrator=True)
    async def mensa_force_reset(self, ctx):
        success = await self.reset_mensa(clear_last_reset=True)
        if not success:
            await ctx.send("Mensa-Daten nicht gefunden.")
            return

        await ctx.send("✅ Mensa wurde manuell zurückgesetzt.")


async def setup(bot):
    cog = Mensa(bot)
    await bot.add_cog(cog)
    bot.add_view(MensaView(cog, cog.get_data() or {}))
