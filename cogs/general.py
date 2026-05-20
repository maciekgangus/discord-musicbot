import discord
from discord.ext import commands


COMMANDS = {
    "🎵 Muzyka": [
        ("`!play <query/url>`", "Szuka na YT i gra / dodaje do kolejki"),
        ("`!p <query>`", "Alias dla play"),
        ("`!skip`", "Pomija aktualny utwór"),
        ("`!pause`", "Pauzuje / wznawia"),
        ("`!stop`", "Zatrzymuje i rozłącza bota"),
        ("`!queue` / `!q`", "Pokazuje kolejkę"),
        ("`!nowplaying` / `!np`", "Aktualnie grający utwór"),
        ("`!loop`", "Przełącza pętlę"),
        ("`!shuffle`", "Tasuje kolejkę"),
        ("`!volume <0-100>`", "Ustawia głośność"),
        ("`!remove <nr>`", "Usuwa utwór z kolejki"),
    ],
    "⚙️ Ogólne": [
        ("`!help`", "Ta wiadomość"),
        ("`!ping`", "Latencja bota"),
    ],
}


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="📖 Pomoc",
            description=f"Prefix: `{self.bot.command_prefix}`",
            color=0x5865F2,
        )
        for section, cmds in COMMANDS.items():
            value = "\n".join(f"{cmd} — {desc}" for cmd, desc in cmds)
            embed.add_field(name=section, value=value, inline=False)
        embed.set_footer(text="Powered by yt-dlp + discord.py")
        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"🏓 Pong! `{latency}ms`")


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
