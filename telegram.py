from telethon import TelegramClient

# Your API ID and Hash
api_id = 23608204
api_hash = 'd54e2308757fe6988f876d86c6cdf97b'
# The name of the session
session_name = 'session_name'


async def get_last_messages(channel_username, limit=1000):
    messages = []
    # Connect to the client
    async with TelegramClient(session_name, api_id, api_hash) as client:
        async for message in client.iter_messages(channel_username, limit=limit):
            messages.append((message.sender_id, message.text))
    return messages
