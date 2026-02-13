import discord
from discord.ext import commands
import re
from database import save_schedule

# -------------------------------
# TEMP SESSION STORAGE
# -------------------------------
schedule_sessions = {}


class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    schedule = discord.SlashCommandGroup(
        "schedule",
        "Manage scheduled messages"
    )

    @schedule.command(name="create", description="Create a scheduled message")
    async def create(self, ctx: discord.ApplicationContext):
        user_id = ctx.user.id

        schedule_sessions[user_id] = {
            "days": [],
            "target_ids": []
        }

        await ctx.respond(
            "📌 **Schedule setup started!**\n\nChoose where to send the message:",
            view=TargetSelectView(user_id),
            ephemeral=True
        )

    @schedule.command(
        name="list",
        description="List all scheduled messages"
    )
    async def list(self, ctx: discord.ApplicationContext):
        from database import get_all_schedules

        schedules = get_all_schedules()

        if not schedules:
            await ctx.respond("📭 No schedules found.", ephemeral=True)
            return

        lines = ["🗓️ **Scheduled Messages:**\n"]

        for sid, target, target_ids, message, days, time, last_sent in schedules:
            if target == "DM":
                mentions = []
                for uid in target_ids.split(","):
                    user = self.bot.get_user(int(uid))
                    mentions.append(user.mention if user else f"`{uid}`")

                target_text = "📩 DM → " + ", ".join(mentions)

            else:
                channel_id = target_ids.split(",")[0]
                target_text = f"📢 CHANNEL → <#{channel_id}>"

            lines.append(
                f"**ID:** `{sid}`\n"
                f"{target_text}\n"
                f"Days: {days}\n"
                f"Time: {time}\n"
            )

        await ctx.respond("\n".join(lines), ephemeral=True)

    @schedule.command(
        name="delete",
        description="Delete a scheduled message"
    )
    async def delete(self, ctx: discord.ApplicationContext, id: int):
        from database import delete_schedule

        delete_schedule(id)

        await ctx.respond(
            f"🗑️ Schedule `{id}` deleted successfully.",
            ephemeral=True
        )
  
    @schedule.command(
        name="edit",
        description="Edit an existing schedule"
    )
    async def edit(self, ctx: discord.ApplicationContext):
        from database import get_all_schedules

        schedules = get_all_schedules()

        if not schedules:
            await ctx.respond("📭 No schedules found.", ephemeral=True)
            return

        options = []
        for sid, target, target_ids, message, days, time, _ in schedules:
            label = f"{sid} • {target} • {days} @ {time}"
            options.append(discord.SelectOption(label=label[:100], value=str(sid)))

        await ctx.respond(
            "✏️ **Select a schedule to edit:**",
            view=ScheduleEditSelectView(options),
            ephemeral=True
        )

class ScheduleEditSelectView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=60)
        self.add_item(ScheduleEditSelect(options))


class ScheduleEditSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Choose a schedule",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        schedule_id = int(self.values[0])
        from database import get_schedule_by_id

        schedule = get_schedule_by_id(schedule_id)
        if not schedule:
            await interaction.response.send_message(
                "❌ Schedule not found.",
                ephemeral=True
            )
            return

        _, target, target_ids, message, days, time = schedule

        await interaction.response.send_modal(
            ScheduleEditModal(
                schedule_id=schedule_id,
                message=message,
                days=days,
                time=time
            )
        )
class ScheduleEditModal(discord.ui.Modal):
    def __init__(self, schedule_id: int, message: str, days: str, time: str):
        super().__init__(title="Edit Schedule")

        self.schedule_id = schedule_id

        self.message_input = discord.ui.InputText(
            label="Message",
            style=discord.InputTextStyle.long,
            value=message
        )

        self.days_input = discord.ui.InputText(
            label="Days (e.g. MON,WED,FRI)",
            value=days
        )

        self.time_input = discord.ui.InputText(
            label="Time (HH:MM)",
            value=time
        )

        self.add_item(self.message_input)
        self.add_item(self.days_input)
        self.add_item(self.time_input)

    async def callback(self, interaction: discord.Interaction):
        from database import update_schedule

        update_schedule(
            schedule_id=self.schedule_id,
            message=self.message_input.value,
            days=self.days_input.value.upper(),
            time=self.time_input.value
        )

        await interaction.response.send_message(
            "✅ **Schedule updated successfully!**",
            ephemeral=True
        )


# -------------------------------
# TARGET SELECTION
# -------------------------------
class TargetSelectView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    @discord.ui.button(label="📩 DM Users", style=discord.ButtonStyle.primary)
    async def dm_users(self, button, interaction):
        schedule_sessions[self.user_id]["target"] = "DM"
        await interaction.response.send_message(
            "👥 **Select users to DM:**",
            view=UserSelectView(self.user_id),
            ephemeral=True
        )

    @discord.ui.button(label="📢 Channel", style=discord.ButtonStyle.secondary)
    async def channel(self, button, interaction):
        schedule_sessions[self.user_id]["target"] = "CHANNEL"
        await interaction.response.send_message(
            "📢 **Select a channel:**",
            view=ChannelSelectView(self.user_id),
            ephemeral=True
        )


# -------------------------------
# USER SELECT (MULTI DM)
# -------------------------------
class UserSelectView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.user_select(
        placeholder="Select users",
        min_values=1,
        max_values=10
    )
    async def select_users(self, select, interaction):
        schedule_sessions[self.user_id]["target_ids"] = [
            user.id for user in select.values
        ]
        await interaction.response.send_modal(MessageModal(self.user_id))


# -------------------------------
# CHANNEL SELECT
# -------------------------------
class ChannelSelectView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.channel_select(
        channel_types=[discord.ChannelType.text],
        placeholder="Select a channel"
    )
    async def select_channel(self, select, interaction):
        channel = select.values[0]
        schedule_sessions[self.user_id]["target_ids"] = [channel.id]
        await interaction.response.send_modal(MessageModal(self.user_id))


# -------------------------------
# MESSAGE MODAL
# -------------------------------
class MessageModal(discord.ui.Modal):
    def __init__(self, user_id: int):
        super().__init__(title="Schedule Message")
        self.user_id = user_id

        self.message = discord.ui.InputText(
            label="Message",
            style=discord.InputTextStyle.long
        )
        self.add_item(self.message)

    async def callback(self, interaction: discord.Interaction):
        schedule_sessions[self.user_id]["message"] = self.message.value

        await interaction.response.send_message(
            "📅 **Select days:**",
            view=DaySelectView(self.user_id),
            ephemeral=True
        )


# -------------------------------
# DAY SELECTION
# -------------------------------
class DaySelectView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id

    def toggle(self, day: str):
        days = schedule_sessions[self.user_id]["days"]
        if day in days:
            days.remove(day)
        else:
            days.append(day)

    async def handle(self, interaction, day: str):
        self.toggle(day)
        await interaction.response.send_message(
            f"Selected days: {', '.join(schedule_sessions[self.user_id]['days'])}",
            ephemeral=True
        )

    @discord.ui.button(label="Monday")
    async def monday(self, button, interaction):
        await self.handle(interaction, "MON")

    @discord.ui.button(label="Tuesday")
    async def tuesday(self, button, interaction):
        await self.handle(interaction, "TUE")

    @discord.ui.button(label="Wednesday")
    async def wednesday(self, button, interaction):
        await self.handle(interaction, "WED")

    @discord.ui.button(label="Thursday")
    async def thursday(self, button, interaction):
        await self.handle(interaction, "THU")

    @discord.ui.button(label="Friday")
    async def friday(self, button, interaction):
        await self.handle(interaction, "FRI")

    @discord.ui.button(label="Saturday")
    async def saturday(self, button, interaction):
        await self.handle(interaction, "SAT")

    @discord.ui.button(label="Sunday")
    async def sunday(self, button, interaction):
        await self.handle(interaction, "SUN")

    @discord.ui.button(label="✅ Done", style=discord.ButtonStyle.success, row=3)
    async def done(self, button, interaction):
        await interaction.response.send_modal(TimeModal(self.user_id))


# -------------------------------
# TIME MODAL
# -------------------------------
class TimeModal(discord.ui.Modal):
    def __init__(self, user_id: int):
        super().__init__(title="Schedule Time")
        self.user_id = user_id

        self.time = discord.ui.InputText(
            label="Time (HH:MM)",
            placeholder="16:30"
        )
        self.add_item(self.time)

    async def callback(self, interaction: discord.Interaction):
        time_value = self.time.value.strip()

        if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", time_value):
            await interaction.response.send_message(
                "❌ Invalid time format (HH:MM)",
                ephemeral=True
            )
            return

        data = schedule_sessions[self.user_id]

        save_schedule(
            target=data["target"],
            target_ids=data["target_ids"],
            message=data["message"],
            days=data["days"],
            time=time_value
        )

        await interaction.response.send_message(
            "🎉 **Schedule created successfully!**",
            ephemeral=True
        )


def setup(bot):
    bot.add_cog(Schedule(bot))
