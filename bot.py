import discord
import re
import os
from datetime import datetime

TOKEN = os.getenv('DISCORD_TOKEN')
KANAL_ID_WYJAZDY = int(os.getenv('DISCORD_CHANNEL_ID', '987654321'))
KANAL_ID_STAT = int(os.getenv('DISCORD_REPORT_CHANNEL_ID', '1234567'))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

GRUPA_CZAS = 60

def parsuj_alarm_tekst(tresc):
    """Parsuje zwykly tekst (stary format)."""
    pattern = r'ALARM OSP ([\w\s\u00e0-\u017e]+?) (\d{2}:\d{2}:\d{2})'
    match = re.search(pattern, tresc)
    if match:
        return match.group(1).strip(), match.group(2)
    return None, None

def parsuj_alarm_embed(title, description):
    """Parsuje embed: title='🚨 ALARM — OSP Nazwa', description='🕐 18:35:20'"""
    if not title:
        return None, None
    # Sprawdz czy to alarm (nie TEST ani inny typ)
    title_match = re.search(r'ALARM\s*[—–-]\s*OSP\s+([\w\s\u00e0-\u017e]+)', title)
    if not title_match:
        return None, None
    nazwa = title_match.group(1).strip()
    # Godzina jest w description
    if not description:
        return None, None
    time_match = re.search(r'(\d{2}:\d{2}:\d{2})', description)
    if not time_match:
        return None, None
    return nazwa, time_match.group(1)

def parsuj_alarm(tresc):
    """Zachowana dla kompatybilnosci ze starymi wiadomosciami tekstowymi."""
    return parsuj_alarm_tekst(tresc)

CURRENT_YEAR = datetime.now().year

def wyciagnij_jednostke_i_czas(msg):
    """Wyciaga jednostke i czas z wiadomosci tekstowej lub embeda."""
    # Nowe wiadomosci jako embed
    if msg.embeds:
        for embed in msg.embeds:
            jednostka, godzina = parsuj_alarm_embed(embed.title, embed.description)
            if jednostka and godzina:
                return jednostka, godzina
    # Stare wiadomosci tekstowe
    return parsuj_alarm_tekst(msg.content)

async def zlicz_wszystko():
    wyjazdy_channel = client.get_channel(KANAL_ID_WYJAZDY)
    ostatnie_wyjazdy = {}
    liczniki = {}
    async for msg in wyjazdy_channel.history(limit=None, oldest_first=True):
        if msg.created_at.year != CURRENT_YEAR:
            continue
        jednostka, godzina_str = wyciagnij_jednostke_i_czas(msg)
        if jednostka and godzina_str:
            czas = msg.created_at.replace(tzinfo=None)
            if jednostka in ostatnie_wyjazdy:
                delta = (czas - ostatnie_wyjazdy[jednostka]).total_seconds()
                if delta < GRUPA_CZAS:
                    continue
            ostatnie_wyjazdy[jednostka] = czas
            liczniki[jednostka] = liczniki.get(jednostka, 0) + 1
    if not liczniki:
        info = "Brak danych o wyjazdach w tym roku."
    else:
        info = f"**Statystyki wyjazdow OSP ({CURRENT_YEAR}):**\n"
        for j, count in sorted(liczniki.items(), key=lambda x: -x[1]):
            info += f"- {j.title()}: {count}\n"
    return info

async def zlicz_wyjazdy_jednostki(nazwa_osp):
    wyjazdy_channel = client.get_channel(KANAL_ID_WYJAZDY)
    ostatnie_wyjazdy = {}
    licznik = 0
    async for msg in wyjazdy_channel.history(limit=None, oldest_first=True):
        if msg.created_at.year != CURRENT_YEAR:
            continue
        jednostka, godzina_str = wyciagnij_jednostke_i_czas(msg)
        if jednostka and godzina_str:
            if jednostka.lower() == nazwa_osp.lower():
                czas = msg.created_at.replace(tzinfo=None)
                if jednostka in ostatnie_wyjazdy:
                    delta = (czas - ostatnie_wyjazdy[jednostka]).total_seconds()
                    if delta < GRUPA_CZAS:
                        continue
                ostatnie_wyjazdy[jednostka] = czas
                licznik += 1
    return licznik

@client.event
async def on_ready():
    print(f'Bot zalogowany jako {client.user}')

@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id == KANAL_ID_STAT and message.content.lower().startswith("!policz"):
        parts = message.content.strip().split(" ", 1)
        if len(parts) == 2:
            argument = parts[1].strip().title()

            if argument.lower() == "wszystko":
                print("Otrzymano komende !policz wszystko")
                # Potwierdzenie odebrania komendy
                await message.channel.send(
                    f"⏳ Zliczam wyjazdy wszystkich jednostek OSP za {CURRENT_YEAR}... Moze to chwile zajac."
                )
                info = await zlicz_wszystko()
                await message.channel.send(info)
                print('Statystyki wszystkich jednostek wyslane.')

            else:
                argument = argument.title()
                print(f"Otrzymano komende dla: {argument}")
                # Potwierdzenie odebrania komendy
                await message.channel.send(
                    f"⏳ Zliczam wyjazdy jednostki **OSP {argument}** za {CURRENT_YEAR}..."
                )
                liczba = await zlicz_wyjazdy_jednostki(argument)
                await message.channel.send(
                    f"✅ Liczba wyjazdow OSP {argument} ({CURRENT_YEAR}): **{liczba}**"
                )
                print('Liczba wyjazdow wyslana.')

        else:
            # Uzytkownik wpisal samo "!policz" bez argumentu
            await message.channel.send(
                "❓ Uzycie komendy:\n"
                "`!policz wszystko` — statystyki wszystkich jednostek\n"
                "`!policz NAZWA` — liczba wyjazdow konkretnej jednostki, np. `!policz Warszawa`"
            )

if __name__ == "__main__":
    client.run(TOKEN)
