import asyncio
import requests
import os
import re

from dotenv import load_dotenv
from openai import OpenAI
import json

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

@dp.message(Command("start"))
async def command_start(message: types.Message):
    await message.reply(BOT_HI_MESSAGE)



@dp.message(Command("telegram"))
async def command_telegram(message: types.Message):
    match = re.match(r'/telegram\s+@(\S+)', message.text)
    if match:
        mess = await message.reply("⏳ Fetching data from the Telegram channel...")
        channel_name = f"@{match.group(1)}"
        messages = await get_last_messages(channel_name)
        await mess.edit_text("✍️ Creating a summary...")
        summary = summarize_messages_corcel(messages)
        await send_long_message(message, summary)
        await mess.delete()
    else:
        await message.reply("Please provide a valid channel name after the /telegram command.")




@dp.message(F.text)
async def get_text(message: types.Message) -> None:
    text = message.text

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


def escape_markdown(text: str) -> str:
    escape_chars = r'_[]*()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)


async def send_long_message(message: types.Message, text: str):
    max_length = 4000
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
