import asyncio
import requests
import os
import re
from dotenv import load_dotenv
from openai import OpenAI
import json
from galadrielGpt import getResponseFromGaladrielWithRequest
from spider import Spider
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

client = OpenAI(api_key=openai_api_key)

BOT_HI_MESSAGE = "Telegram bot for summarizing text.\n"


async def hello_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(BOT_HI_MESSAGE)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(BOT_HI_MESSAGE)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(BOT_HI_MESSAGE)


async def get_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    text = message.text

    url_pattern = re.compile(r'^(http|https|ftp|ftps|file|sftp)://\S+')

    if url_pattern.match(text):
        mess = await message.reply_text("🔗 Fetching data from the webpage...")
        try:
            scrapedText = scrape_webpage(text)
            await mess.edit_text("🔍 Cleaning up the text...")
            cleanedText = cleanup_text_corcel(scrapedText)
            await mess.edit_text("✍️ Creating a summary...")
            summarizedText = summarize_text_corcel(cleanedText)
            await message.reply_text(summarizedText)
        except Exception as e:
            await mess.edit_text(f"❌ An error occurred: {e}")
    else:
        mess = await message.reply_text("✍️ Creating a summary...")
        try:
            summarizedText = summarize_text_galadriel(text)
            await message.reply_text(summarizedText)
        except Exception as e:
            await mess.edit_text(f"❌ An error occurred: {e}")




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




if __name__ == "__main__":
    app = ApplicationBuilder().token(telegram_bot_token).build()
    app.add_handler(CommandHandler("hello", hello_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_text))

    app.run_polling()
