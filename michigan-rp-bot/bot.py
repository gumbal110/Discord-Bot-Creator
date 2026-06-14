"""
Michigan RP Welcome Bot
=======================
A professional Discord bot for the Michigan RP community.
Automatically welcomes new members via channel embeds and DMs,
with full slash-command support and live config reloading.
"""

import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging setup — writes to console with timestamp + level
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("MichiganRPBot")

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    """Load and return the config.json file as a dictionary."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def resolve_placeholders(text: str, member: discord.Member) -> str:
    """
    Replace placeholder tokens inside embed text fields with real values.

    Supported placeholders:
      {user}         — e.g. "CoolUser#1234"
      {username}     — display / global name, e.g. "CoolUser"
      {member_count} — total member count of the guild
      {server}       — guild name
      {mention}      — @mention string
    """
    return (
        text.replace("{user}", str(member))
            .replace("{username}", member.display_name)
            .replace("{member_count}", str(member.guild.member_count))
            .replace("{server}", member.guild.name)
            .replace("{mention}", member.mention)
    )


def build_embed(embed_cfg: dict, member: discord.Member) -> discord.Embed:
    """
    Construct a discord.Embed from an embed configuration block.

    The configuration block supports the following keys (all optional except
    where noted):
      title, description, color (hex string like "#FF0000"),
      thumbnail_url, image_url,
      footer_text, footer_icon_url,
      author_name, author_icon_url, author_url
    """
    # --- Color -----------------------------------------------------------
    raw_color = embed_cfg.get("color", "#2b2d31")
    try:
        color = discord.Color(int(raw_color.lstrip("#"), 16))
    except (ValueError, AttributeError):
        color = discord.Color.blurple()

    # --- Core fields -----------------------------------------------------
    title = resolve_placeholders(embed_cfg.get("title", ""), member)
    description = resolve_placeholders(embed_cfg.get("description", ""), member)

    embed = discord.Embed(
        title=title or None,
        description=description or None,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )

    # --- Author ----------------------------------------------------------
    author_name = resolve_placeholders(embed_cfg.get("author_name", ""), member)
    if author_name:
        embed.set_author(
            name=author_name,
            icon_url=embed_cfg.get("author_icon_url") or None,
            url=embed_cfg.get("author_url") or None,
        )

    # --- Thumbnail -------------------------------------------------------
    thumb = embed_cfg.get("thumbnail_url", "")
    if thumb:
        embed.set_thumbnail(url=thumb)

    # --- Large image / banner -------------------------------------------
    image = embed_cfg.get("image_url", "")
    if image:
        embed.set_image(url=image)

    # --- Footer ----------------------------------------------------------
    footer_text = resolve_placeholders(embed_cfg.get("footer_text", ""), member)
    if footer_text:
        embed.set_footer(
            text=footer_text,
            icon_url=embed_cfg.get("footer_icon_url") or None,
        )

    # --- Extra dynamic fields added automatically -----------------------
    embed.add_field(name="Username", value=member.mention, inline=True)
    embed.add_field(
        name="Joined",
        value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Just now",
        inline=True,
    )
    embed.add_field(
        name="Member Count",
        value=f"#{member.guild.member_count}",
        inline=True,
    )

    return embed


# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------

# Intents — member events require the privileged "members" intent which must
# be enabled in the Discord Developer Portal under "Privileged Gateway Intents".
intents = discord.Intents.default()
intents.members = True          # on_member_join / guild.member_count
intents.message_content = False # not needed for slash commands


class MichiganRPBot(commands.Bot):
    """Custom Bot subclass that holds the live config and syncs the command tree."""

    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.config: dict = {}

    async def setup_hook(self) -> None:
        """Called once after login; syncs slash commands to Discord."""
        self.config = load_config()
        log.info("Config loaded.")
        await self.tree.sync()
        log.info("Slash commands synced.")

    async def on_ready(self) -> None:
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=self.config.get("status_message", "Michigan RP"),
            )
        )


bot = MichiganRPBot()


# ---------------------------------------------------------------------------
# Event: on_member_join
# ---------------------------------------------------------------------------

@bot.event
async def on_member_join(member: discord.Member) -> None:
    """
    Fires when a new member joins the guild.
    1. Sends the welcome embed to the configured channel.
    2. Attempts to DM the new member.
    """
    cfg = bot.config

    # --- Channel welcome embed ------------------------------------------
    channel_id = cfg.get("welcome_channel_id")
    if channel_id:
        channel = member.guild.get_channel(int(channel_id))
        if channel:
            try:
                embed = build_embed(cfg.get("welcome_embed", {}), member)
                await channel.send(
                    content=member.mention,   # ping so the member is notified
                    embed=embed,
                )
                log.info("Sent welcome embed for %s in #%s", member, channel.name)
            except discord.Forbidden:
                log.warning("Missing permissions to send in channel %s", channel_id)
            except Exception as exc:
                log.error("Failed to send channel welcome: %s", exc)
        else:
            log.warning("Welcome channel ID %s not found in this guild.", channel_id)

    # --- DM embed -------------------------------------------------------
    try:
        dm_embed = build_embed(cfg.get("dm_embed", {}), member)
        await member.send(embed=dm_embed)
        log.info("Sent DM embed to %s", member)
    except discord.Forbidden:
        # DMs disabled by user — expected; keep the bot running normally
        log.info("Could not DM %s (DMs disabled).", member)
    except Exception as exc:
        log.error("Unexpected error while DMing %s: %s", member, exc)


# ---------------------------------------------------------------------------
# Slash commands
# ---------------------------------------------------------------------------

@bot.tree.command(name="testwelcome", description="Send a test welcome embed in the configured channel.")
@app_commands.checks.has_permissions(manage_guild=True)
async def testwelcome(interaction: discord.Interaction) -> None:
    """
    /testwelcome — sends the welcome embed to the configured channel
    as if the command user had just joined, so staff can preview the output.
    """
    cfg = bot.config
    channel_id = cfg.get("welcome_channel_id")

    if not channel_id:
        await interaction.response.send_message(
            "❌ No `welcome_channel_id` set in config.json.", ephemeral=True
        )
        return

    channel = interaction.guild.get_channel(int(channel_id))
    if not channel:
        await interaction.response.send_message(
            f"❌ Channel `{channel_id}` not found in this server.", ephemeral=True
        )
        return

    try:
        embed = build_embed(cfg.get("welcome_embed", {}), interaction.user)
        await channel.send(content=interaction.user.mention, embed=embed)
        await interaction.response.send_message(
            f"✅ Test welcome embed sent to {channel.mention}.", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to send messages in that channel.", ephemeral=True
        )


@bot.tree.command(name="testdm", description="Send a test DM embed to yourself.")
async def testdm(interaction: discord.Interaction) -> None:
    """
    /testdm — sends the DM welcome embed directly to the command user
    so they can preview what new members will receive.
    """
    cfg = bot.config

    try:
        dm_embed = build_embed(cfg.get("dm_embed", {}), interaction.user)
        await interaction.user.send(embed=dm_embed)
        await interaction.response.send_message(
            "✅ Test DM sent — check your Direct Messages!", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I couldn't DM you. Please enable DMs from server members in your Privacy Settings.",
            ephemeral=True,
        )


@bot.tree.command(name="reload", description="Reload config.json without restarting the bot.")
@app_commands.checks.has_permissions(manage_guild=True)
async def reload_config(interaction: discord.Interaction) -> None:
    """
    /reload — hot-reloads config.json at runtime.
    Useful for updating embed text, colors, or channel IDs without a restart.
    """
    try:
        bot.config = load_config()
        log.info("Config reloaded by %s", interaction.user)
        await interaction.response.send_message(
            "✅ `config.json` reloaded successfully.", ephemeral=True
        )
    except FileNotFoundError:
        await interaction.response.send_message(
            "❌ `config.json` not found.", ephemeral=True
        )
    except json.JSONDecodeError as exc:
        await interaction.response.send_message(
            f"❌ JSON parse error in `config.json`: `{exc}`", ephemeral=True
        )


# ---------------------------------------------------------------------------
# Error handlers for slash command permission checks
# ---------------------------------------------------------------------------

@testwelcome.error
@reload_config.error
async def admin_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You need **Manage Server** permission to use this command.",
            ephemeral=True,
        )
    else:
        log.error("Unhandled command error: %s", error)
        await interaction.response.send_message(
            "❌ An unexpected error occurred.", ephemeral=True
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # The bot token is read from the DISCORD_TOKEN environment variable.
    # Never hard-code your token — set it via a .env file or your hosting
    # platform's secrets manager.
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        log.critical(
            "DISCORD_TOKEN environment variable is not set. "
            "Set it before running the bot."
        )
        raise SystemExit(1)

    bot.run(token, log_handler=None)  # log_handler=None keeps our custom logger
