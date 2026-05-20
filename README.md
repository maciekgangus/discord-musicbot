# Discord Music Bot

Stack: `discord.py 2.x` + `yt-dlp` + `FFmpeg` + Docker

## Setup

### 1. Discord Developer Portal

1. Wejdź na https://discord.com/developers/applications
2. New Application → Bot → Reset Token → skopiuj
3. W sekcji **Privileged Gateway Intents** włącz `Message Content Intent`
4. OAuth2 → URL Generator → scope: `bot` → permissions: `Connect`, `Speak`, `Send Messages`, `Embed Links`
5. Wygeneruj link i dodaj bota na serwer

### 2. Na VMce

```bash
git clone <repo> discord-bot
cd discord-bot

cp .env.example .env
# Edytuj .env i wklej token

docker compose up -d --build
```

### 3. Sprawdzenie logów

```bash
docker compose logs -f
```

## Komendy

| Komenda | Opis |
|---------|------|
| `!play <query/url>` | Szuka na YT i gra |
| `!skip` | Pomija utwór |
| `!pause` | Pauzuje / wznawia |
| `!stop` | Zatrzymuje i rozłącza |
| `!queue` | Pokazuje kolejkę |
| `!np` | Aktualnie grający utwór |
| `!loop` | Pętla ON/OFF |
| `!shuffle` | Tasuje kolejkę |
| `!volume 0-100` | Głośność |
| `!remove <nr>` | Usuwa z kolejki |

## Aktualizacja yt-dlp

YT często zmienia API. Jeśli bot przestaje grać:

```bash
docker compose exec bot pip install -U yt-dlp
docker compose restart bot
```

Albo zaktualizuj `requirements.txt` i zrób `docker compose up -d --build`.

## Problemy

**Bot nie łączy się z kanałem głosowym**
- Upewnij się że masz `PyNaCl` w requirements (potrzebny do voice)

**Nic nie gra / błąd FFmpeg**
- Sprawdź `docker compose logs` — jeśli `ffmpeg: not found` to problem z obrazem
- Zrób `docker compose up -d --build --no-cache`

**Błąd 403 od YT**
- YT blokuje requesty z data center IP. Rozwiązania:
  1. Ustaw cookies: pobierz `cookies.txt` z przeglądarki (rozszerzenie "Get cookies.txt") i dodaj do `YDL_OPTS`: `"cookiefile": "/app/cookies.txt"`
  2. Użyj PO Token (zaawansowane — patrz yt-dlp docs)
