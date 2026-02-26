import discord
from discord.ext import commands, tasks
from database import init_db, get_all_schedules, update_last_sent
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    intents=intents,
    debug_guilds=[1401189837071061023]
)

# -------------------------------
# SCHEDULER LOOP
# -------------------------------
@tasks.loop(minutes=1)
async def scheduler_loop():
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    current_day = now.strftime("%a").upper()[:3]
    today = now.strftime("%Y-%m-%d")

    schedules = get_all_schedules()

    for schedule_id, target, target_ids, message, days, time, last_sent in schedules:
        try:
            # Wrong day
            if current_day not in days.split(","):
                continue

            # Already sent today
            if last_sent == today:
                continue

            # Time not reached yet
            if current_time < time:
                continue

            # ---- DM USERS ----
            if target == "DM":
                for uid in target_ids.split(","):
                    try:
                        user = await bot.fetch_user(int(uid))
                        await user.send(message)
                    except Exception as dm_error:
                        print(f"⚠️ Failed to DM user {uid}: {dm_error}")

            # ---- CHANNEL ----
            elif target == "CHANNEL":
                for cid in target_ids.split(","):
                    channel = bot.get_channel(int(cid))
                    if channel:
                        try:
                            await channel.send(message)
                        except Exception as ch_error:
                            print(f"⚠️ Failed to send to channel {cid}: {ch_error}")
                    else:
                        print(f"⚠️ Channel not found: {cid}")

            # Mark as sent
            update_last_sent(schedule_id, today)

        except Exception as e:
            print("❌ Scheduler error:", e)


# -------------------------------
# WAIT UNTIL BOT IS READY
# -------------------------------
@scheduler_loop.before_loop
async def before_scheduler():
    await bot.wait_until_ready()


# -------------------------------
# BOT READY EVENT
# -------------------------------
@bot.event
async def on_ready():
    init_db()
    if not scheduler_loop.is_running():
        scheduler_loop.start()
    print(f"✅ Bot is online as {bot.user}")


# -------------------------------
# LOAD COMMANDS
# -------------------------------
bot.load_extension("commands.ping")
bot.load_extension("commands.schedule")

bot.run(TOKEN)

