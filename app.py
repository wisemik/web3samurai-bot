import asyncio
import requests
import os
import re

from dotenv import load_dotenv
from openai import OpenAI
import json
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader


from galadriel import getResponseFromGaladrielWithRequest
from spider import Spider
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, \
    InputFile
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters.command import Command
from aiogram import F
from pathlib import Path
from telegram import get_last_messages
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from youtube_transcript_api.formatters import TextFormatter

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
session = AiohttpSession()
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()
BOT_HI_MESSAGE = (
    "🤖 Welcome to the Web3 Sammurai: Web3 Article Summarizer & Voice Generator Bot! 📚🎵\n\n"
    "Commands:\n"
    "/start - Initialize the bot\n"
    "/telegram @channelname - Summarize latest messages from a Telegram channel\n"
    "Send a URL or text of the article - Get a summary and generate an audio version\n"
    "Enjoy the bot! 🚀"
)
base_dir = os.path.dirname(os.path.abspath(__file__))
json_file_path = os.path.join(base_dir, 'data', 'messages.json')
os.makedirs(os.path.dirname(json_file_path), exist_ok=True)


@dp.message(Command("start"))
async def command_start(message: types.Message):
    await message.reply(BOT_HI_MESSAGE)


@dp.message(Command("audio"))
async def command_audio(message: types.Message):
    match = re.match(r'/audio\s+(.+)', message.text)
    if match:
        mess = await message.reply("🎵 Creating an audio...")
        text = match.group(1)

        await message.reply_audio(audio=generate_audio(text))

        await mess.delete()
    else:
        await message.reply("Please provide the text after the command. Example: /audio Hello, world!")


@dp.message(Command("youtube"))
async def command_youtube(message: types.Message):
    video_url = message.text.replace('/youtube', '').strip()
    if not video_url:
        await message.reply("📎 Please provide a YouTube video link.")
        return

    try:
        mess = await message.reply("🔍 Fetching subtitles, please wait...")
        subtitles = get_youtube_subtitles(video_url)

        await mess.edit_text("✍️ Creating a summary...")
        summarized_text = summarize_text_corcel(subtitles)
        await send_long_message(message, summarized_text)
        await mess.delete()

        mess = await message.reply("🎵 Creating an audio...")
        audio = generate_audio(summarized_text)
        await message.reply_audio(audio=audio)
        await mess.delete()

    except Exception as e:
        await message.reply(f"❗ An unexpected error occurred: {str(e)}")


@dp.message(Command("ask"))
async def rag_response(message: types.Message):
    documents = SimpleDirectoryReader("data").load_data()
    index = VectorStoreIndex.from_documents(documents)

    query_engine = index.as_query_engine()

    original_query = message.text

    response = query_engine.query(original_query)
    print(response)
    await message.reply(response.response)


def load_messages(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_messages(file_path, messages):
    with open(file_path, 'w') as file:
        json.dump(messages, file, indent=4)


def add_message(new_message, file_path=json_file_path):
    # Load existing messages
    messages = load_messages(file_path)
    # Add the new message
    messages.append(new_message)
    # Save the updated messages
    save_messages(file_path, messages)

@dp.message(Command("telegram"))
async def command_telegram(message: types.Message):
    try:
        match = re.match(r'/telegram\s+@(\S+)', message.text)
        if match:
            mess = await message.reply("⏳ Fetching data from the Telegram channel...")
            channel_name = f"@{match.group(1)}"

            try:
                messages = await get_last_messages(channel_name)
                if not messages:
                    await mess.edit_text("❌ No messages found for the specified channel.")
                    return

                await mess.edit_text("✍️ Creating a summary...")
                summary = summarize_messages_corcel(messages)

                await send_long_message(message, summary)
                await mess.delete()
            except Exception as e:
                await mess.edit_text(f"❌ An error occurred while fetching messages: {str(e)}")
        else:
            await message.reply("Please provide a valid channel name after the /telegram command.")
    except Exception as e:
        await message.reply(f"❌ An unexpected error occurred: {str(e)}")


async def process_text(message: types.Message, text: str):
    url_pattern = re.compile(r'^(http|https|ftp|ftps|file|sftp)://\S+')
    if url_pattern.match(text):
        mess = await message.reply("🔗 Fetching data from the webpage...")
        try:
            scrapedText = scrape_webpage(text)
            await mess.edit_text("🔍 Cleaning up the text...")
            cleanedText = cleanup_text_corcel(scrapedText)

            await mess.edit_text("✍️ Creating a summary...")
            summarizedText = summarize_text_corcel(cleanedText)
            await send_long_message(message, summarizedText)

            await mess.delete()
            mess = await message.reply("🎵 Creating an audio...")
            await message.reply_audio(audio=generate_audio(summarizedText))
        except Exception as e:
            await mess.edit_text(f"❌ An error occurred: {e}")
    else:
        mess = await message.reply("✍️ Creating a summary...")
        try:
            summarizedText = summarize_text_galadriel(text)
            await message.reply(summarizedText)
            await mess.delete()
            if "Vitailik" in text:
                mess = await message.reply("🎵 Creating a song...")
                voice = get_suno_first_audio_url(summarizedText, "ballade, male singer", "Vitailik")
                await message.reply(voice)
                await mess.delete()
            else:
                mess = await message.reply("🎵 Creating an audio...")
                await message.reply_audio(audio=generate_audio(summarizedText))
                await mess.delete()
        except Exception as e:
            await mess.edit_text(f"❌ An error occurred: {e}")

@dp.message(Command("summary"))
async def command_telegram(message: types.Message):
    text = message.text.replace('/summary', '').strip()
    await process_text(message, text)



@dp.message(F.text)
async def handle_text(message: types.Message) -> None:
    await process_text(message, message.text)


def get_youtube_subtitles(video_url):
    preferred_languages = ['en']
    video_id = video_url.split('v=')[1]

    try:
        # Get available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try to find a transcript in the preferred languages
        transcript = None
        for language in preferred_languages:
            try:
                transcript = transcript_list.find_transcript([language])
                break
            except NoTranscriptFound:
                continue

        # If no preferred language transcript found, get the first available
        if not transcript:
            transcript = transcript_list[0]

        # Fetch the transcript data
        transcript_data = transcript.fetch()

        # Format the transcript data into text
        formatter = TextFormatter()
        formatted_transcript = formatter.format_transcript(transcript_data)

        return formatted_transcript

    except TranscriptsDisabled:
        return "Transcripts are disabled for this video."
    except NoTranscriptFound:
        return "No transcripts found for this video."
    except VideoUnavailable:
        return "This video is unavailable."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


def escape_markdown(text: str) -> str:
    escape_chars = r'_[]*()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)


async def send_long_message(message: types.Message, text: str):
    max_length = 4000
    new_message = {
        "text": text
    }
    add_message(new_message)  # Save the message
    escaped_text = escape_markdown(text)
    if len(escaped_text) > max_length:
        parts = [escaped_text[i:i + max_length] for i in range(0, len(escaped_text), max_length)]
        for part in parts:
            await message.reply(part, parse_mode="MarkdownV2")
    else:
        await message.reply(escaped_text, parse_mode="MarkdownV2")

def summarize_text_galadriel(text: str) -> str:
    message = ("Your are an AI assistant that helps summarize articles."
               "Format the response for Telegram message, use emoji!"
               f"Here is the article text:{text}")

    content = getResponseFromGaladrielWithRequest(message)
    return content

def cleanup_text_corcel(text: str) -> str:
    url = "https://api.corcel.io/v1/text/cortext/chat"

    payload = {
        "model": "cortext-ultra",
        "stream": False,
        "top_p": 1,
        "temperature": 0.0001,
        "max_tokens": 4096,
        "messages": [
            {
                "role": "system",
                "content": "You are an assistant who receives text scraped from a webpage."
                           "Your task is to clean up the text by removing all unnecessary HTML symbols and tags."
                           "Ensure that only the clean article text remains."
                           "Please provide the cleaned text without any HTML tags or symbols."
            },
            {
                "role": "user",
                "content": f"Here is the scraped text:\n\n{text}"
            }
        ]
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": "133c4ba0-4523-4141-a04e-a2d32965cf0a"
    }

    response = requests.post(url, json=payload, headers=headers)
    print(response.text)

    data = json.loads(response.text)

    content = data[0]["choices"][0]["delta"]["content"]

    return content

def summarize_text_corcel(text: str) -> str:
    url = "https://api.corcel.io/v1/text/cortext/chat"

    payload = {
        "model": "cortext-ultra",
        "stream": False,
        "top_p": 1,
        "temperature": 0.0001,
        "max_tokens": 4096,
        "messages": [
            {
                "role": "system",
                "content": "Your are an AI assistant that helps summarize articles. "
                           "Here are the guidelines to follow:"
                           "You will be provided with an article. "
                           "Identify Key Points: Read the entire article carefully "
                           "and identify the key points, main ideas, and important details. "
                           "Concise Summary: Provide a concise summary of the article, capturing the essence "
                           "and significant information without unnecessary details."
                           "Maintain Context: Ensure that the summary maintains the context and intent of the original article. "
                           "Highlight Critical Information: Highlight any critical information, "
                           "statistics, quotes, or data that are essential to understanding the article's main points."
                           "Clear Structure: Organize the summary in a clear and structured format,"
                           "making it easy to read and understand."
                           "Format the response for Telegram message, use emoji!"
                           "Length Limit: Ensure the final summary is no longer than 4000 characters."
            },
            {
                "role": "user",
                "content": f"Here is the article text:\n\n{text}"
            }
        ]
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": "133c4ba0-4523-4141-a04e-a2d32965cf0a"
    }

    response = requests.post(url, json=payload, headers=headers)
    print(response.text)

    data = json.loads(response.text)

    content = data[0]["choices"][0]["delta"]["content"]

    return content


def summarize_messages_corcel(text: str) -> str:
    url = "https://api.corcel.io/v1/text/cortext/chat"

    payload = {
        "model": "cortext-ultra",
        "stream": False,
        "top_p": 1,
        "temperature": 0.0001,
        "max_tokens": 4096,
        "messages": [
            {
                "role": "system",
                "content": "You are an assistant who receives messages from Telegram or Discord."
                           "Your task is to summarize main themes that were discussed in them."
                           "Format the response for Telegram message, use emoji!"
                           "Extract and highlight critically important messages,"
                           "key contacts (names, emails, telegram links),"
                           "key points, and any urgent or actionable information,"
                           "critically important messages, key points and highlights,"
                           "urgent or actionable information,"
                           "specific details such as dates, times, and names."
                           "Don't use general worlds, be specific, concise, clear and structured."
                           "Length Limit: Ensure the final summary is no longer than 4000 characters."
            },
            {
                "role": "user",
                "content": f"Here are the messages:\n\n{text}"
            }
        ]
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": "133c4ba0-4523-4141-a04e-a2d32965cf0a"
    }

    response = requests.post(url, json=payload, headers=headers)
    print(response.text)

    data = json.loads(response.text)

    content = data[0]["choices"][0]["delta"]["content"]

    return content

def scrape_webpage(url: str) -> str:
    app = Spider(api_key=os.getenv("SPIDER_API_KEY"))
    scraped_data = app.scrape_url(url)
    crawler_params = {
        'limit': 1,
        'proxy_enabled': True,
        'store_data': False,
        'metadata': False,
        'request': 'http'
    }
    crawl_result = app.crawl_url(url, params=crawler_params)
    return crawl_result

def get_suno_first_audio_url(prompt, tags, title, make_instrumental=False, wait_audio=True) -> str:
    url = 'https://suno-api-1uz1.vercel.app/api/custom_generate'

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    data = {
        "prompt": prompt,
        "tags": tags,
        "title": title,
        "make_instrumental": make_instrumental,
        "wait_audio": wait_audio
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        response_data = response.json()
        if response_data:
            first_audio_url = response_data[0].get('audio_url')
            if first_audio_url:
                return first_audio_url
    else:
        print(response.text)
        return "Error generating audio"

def generate_audio(text: str) -> FSInputFile:
    speech_file_path = Path(__file__).parent / "speech.mp3"
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )
    print(speech_file_path)
    response.stream_to_file(speech_file_path)
    voice = FSInputFile(speech_file_path)
    return voice

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
