import asyncio
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat

API_ID   = 34601220
API_HASH = "bb0feaf7e3575cb01a8af262bc7a4018"
PHONE    = "+66824323703"
SESSION_NAME = "monitor_session"


async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(phone=PHONE)
    me = await client.get_me()
    print(f"Logged in as @{me.username}\n")
    print(f"{'No.':<5} {'Username / ID':<35} {'Title'}")
    print("-" * 90)

    i = 1
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if isinstance(entity, (Channel, Chat)):
            if getattr(entity, "username", None):
                identifier = f"@{entity.username}"
            else:
                identifier = str(dialog.id)
            print(f"{i:<5} {identifier:<35} {dialog.name}")
            i += 1

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
