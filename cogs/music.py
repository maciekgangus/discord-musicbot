import asyncio
import discord
from discord.ext import commands
from collections import deque
import yt_dlp

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": False,
    "no_warnings": False,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


class Track:
    def __init__(self, url, title, webpage_url, duration, requester):
        self.url = url
        self.title = title
        self.webpage_url = webpage_url
        self.duration = duration
        self.requester = requester

    @property
    def duration_fmt(self):
        m, s = divmod(self.duration or 0, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


async def fetch_track(query, requester):
    loop = asyncio.get_event_loop()

    def _extract():
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            print(f"[YDL] Extracting: {query}")
            info = ydl.extract_info(query, download=False)
            if "entries" in info:
                info = info["entries"][0]
            return info

    try:
        info = await loop.run_in_executor(None, _extract)
    except Exception as e:
        print(f"[YDL] Extract error: {e}")
        return None

    url = info.get("url") or info.get("webpage_url")
    print(f"[YDL] Got URL (first 80): {str(url)[:80]}")
    print(f"[YDL] Title: {info.get('title')}")

    return Track(
        url=url,
        title=info.get("title", "Unknown"),
        webpage_url=info.get("webpage_url", url),
        duration=info.get("duration", 0),
        requester=requester,
    )


class GuildState:
    def __init__(self):
        self.queue = deque()
        self.current = None
        self.loop = False
        self.volume = 0.5


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.states = {}

    def get_state(self, guild_id):
        if guild_id not in self.states:
            self.states[guild_id] = GuildState()
        return self.states[guild_id]

    async def ensure_voice(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ Wejdź najpierw na kanał głosowy.")
            return None
        vc = ctx.voice_client
        if vc is None:
            print(f"[VC] Connecting to {ctx.author.voice.channel}")
            vc = await ctx.author.voice.channel.connect(timeout=10.0, reconnect=True)
            for _ in range(20):
                if vc.is_connected():
                    break
                await asyncio.sleep(0.25)
            print(f"[VC] Connected: {vc.is_connected()}")
        elif vc.channel != ctx.author.voice.channel:
            await vc.move_to(ctx.author.voice.channel)
        return vc

    def play_next(self, guild_id, vc):
        state = self.get_state(guild_id)
        print(f"[PLAY_NEXT] connected={vc.is_connected()} queue={len(state.queue)} loop={state.loop}")

        if not vc.is_connected():
            print("[PLAY_NEXT] Not connected, aborting")
            state.current = None
            return

        if state.loop and state.current:
            track = state.current
            print(f"[PLAY_NEXT] Looping: {track.title}")
        elif state.queue:
            track = state.queue.popleft()
            state.current = track
            print(f"[PLAY_NEXT] Playing next: {track.title}")
        else:
            print("[PLAY_NEXT] Queue empty, stopping")
            state.current = None
            return

        try:
            print(f"[PLAY_NEXT] Creating FFmpegPCMAudio for url: {str(track.url)[:80]}")
            source = discord.FFmpegPCMAudio(track.url, **FFMPEG_OPTS)
            source = discord.PCMVolumeTransformer(source, volume=state.volume)
        except Exception as e:
            print(f"[PLAY_NEXT] Source creation error: {e}")
            return

        def after(err):
            if err:
                print(f"[AFTER] Playback error: {err}")
            else:
                print("[AFTER] Track finished cleanly")
            fut = asyncio.run_coroutine_threadsafe(
                self._play_next_async(guild_id, vc), self.bot.loop
            )
            try:
                fut.result(timeout=10)
            except Exception as e:
                print(f"[AFTER] Callback error: {e}")

        print("[PLAY_NEXT] Calling vc.play()")
        vc.play(source, after=after)
        print(f"[PLAY_NEXT] vc.is_playing()={vc.is_playing()}")

    async def _play_next_async(self, guild_id, vc):
        self.play_next(guild_id, vc)

    @commands.command(aliases=["p"])
    async def play(self, ctx, *, query: str):
        print(f"[CMD] !play called by {ctx.author} query={query}")
        vc = await self.ensure_voice(ctx)
        if vc is None:
            return

        async with ctx.typing():
            track = await fetch_track(query, ctx.author)
            if track is None:
                await ctx.send("❌ Nie znalazłem nic dla tego zapytania.")
                return

        state = self.get_state(ctx.guild.id)
        state.queue.append(track)
        print(f"[CMD] Queue size after append: {len(state.queue)}")

        if not vc.is_playing() and not vc.is_paused():
            self.play_next(ctx.guild.id, vc)
            await ctx.send(f"▶️ Teraz gram: **{track.title}** `[{track.duration_fmt}]`")
        else:
            pos = len(state.queue)
            await ctx.send(f"📋 Dodano do kolejki `#{pos}`: **{track.title}** `[{track.duration_fmt}]`")

    @commands.command()
    async def skip(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await ctx.send("⏭️ Pominięto.")
        else:
            await ctx.send("❌ Nic nie gram.")

    @commands.command()
    async def pause(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("⏸️ Zapauzowano.")
        elif vc and vc.is_paused():
            vc.resume()
            await ctx.send("▶️ Wznowiono.")
        else:
            await ctx.send("❌ Nic nie gram.")

    @commands.command()
    async def stop(self, ctx):
        vc = ctx.voice_client
        state = self.get_state(ctx.guild.id)
        state.queue.clear()
        state.current = None
        state.loop = False
        if vc:
            vc.stop()
            await vc.disconnect()
        await ctx.send("⏹️ Zatrzymano i rozłączono.")

    @commands.command(aliases=["q"])
    async def queue(self, ctx):
        state = self.get_state(ctx.guild.id)
        embed = discord.Embed(title="🎵 Kolejka", color=0x5865F2)
        if state.current:
            loop_icon = "🔁 " if state.loop else ""
            embed.add_field(
                name=f"{loop_icon}Teraz gram",
                value=f"[{state.current.title}]({state.current.webpage_url}) `{state.current.duration_fmt}`",
                inline=False,
            )
        if state.queue:
            lines = []
            for i, t in enumerate(list(state.queue)[:10], 1):
                lines.append(f"`{i}.` [{t.title}]({t.webpage_url}) `{t.duration_fmt}`")
            if len(state.queue) > 10:
                lines.append(f"...i {len(state.queue) - 10} więcej")
            embed.add_field(name="W kolejce", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="W kolejce", value="Pusta.", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def loop(self, ctx):
        state = self.get_state(ctx.guild.id)
        state.loop = not state.loop
        await ctx.send(f"🔁 Pętla: {'ON' if state.loop else 'OFF'}")

    @commands.command()
    async def volume(self, ctx, vol: int):
        if not 0 <= vol <= 100:
            await ctx.send("❌ Podaj wartość 0-100.")
            return
        state = self.get_state(ctx.guild.id)
        state.volume = vol / 100
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = state.volume
        await ctx.send(f"🔊 Głośność: {vol}%")

    @commands.command(aliases=["np"])
    async def nowplaying(self, ctx):
        state = self.get_state(ctx.guild.id)
        if not state.current:
            await ctx.send("❌ Nic nie gram.")
            return
        t = state.current
        embed = discord.Embed(
            title="▶️ Teraz gram",
            description=f"[{t.title}]({t.webpage_url})",
            color=0x5865F2,
        )
        embed.set_footer(text=f"Dodane przez {t.requester.display_name} • {t.duration_fmt}")
        await ctx.send(embed=embed)

    @commands.command()
    async def remove(self, ctx, index: int):
        state = self.get_state(ctx.guild.id)
        if not 1 <= index <= len(state.queue):
            await ctx.send("❌ Nieprawidłowy numer.")
            return
        items = list(state.queue)
        removed = items.pop(index - 1)
        state.queue = deque(items)
        await ctx.send(f"🗑️ Usunięto: **{removed.title}**")

    @commands.command()
    async def shuffle(self, ctx):
        import random
        state = self.get_state(ctx.guild.id)
        items = list(state.queue)
        random.shuffle(items)
        state.queue = deque(items)
        await ctx.send("🔀 Kolejka potasowana.")


async def setup(bot):
    await bot.add_cog(Music(bot))
