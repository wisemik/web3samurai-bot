import asyncio
import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource,
)
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters.command import Command
from aiogram import F
from aiogram.types import FSInputFile
import json
from galadrielGpt import getResonseFromGaladrielWithRequest

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

session = AiohttpSession()
client = OpenAI(api_key=openai_api_key)
bot = Bot(token=telegram_bot_token, session=session)
dp = Dispatcher()

# Define a global constant for the message text
BOT_HI_MESSAGE = ("Telegram bot for summarizing text.\n")


@dp.message(Command("start"))
async def command_start(message: types.Message):
    await message.reply(BOT_HI_MESSAGE)


@dp.message(Command("id"))
async def command_id(message: types.Message):
    await message.reply(
        f"chat id: {message.chat.id}\n" f"user_id: {message.from_user.id}"
    )


@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.reply(BOT_HI_MESSAGE)


@dp.message(F.text)
async def get_text(message: types.Message):
    await message.reply(summarize_text_galadriel(message.text))


# def galadrielSimpleScript(text: str) -> str:
#     rpc_url = os.getenv("RPC_URL")
#     if not rpc_url:
#         raise ValueError("Missing RPC_URL in .env")
#     private_key = os.getenv("PRIVATE_KEY")
#     if not private_key:
#         raise ValueError("Missing PRIVATE_KEY in .env")
#     contract_address = os.getenv("SIMPLE_LLM_CONTRACT_ADDRESS")
#     if not contract_address:
#         raise ValueError("Missing SIMPLE_LLM_CONTRACT_ADDRESS in .env")
#
#     # Connect to the Ethereum node
#     web3 = Web3(Web3.HTTPProvider(rpc_url))
#     web3.middleware_onion.inject(geth_poa_middleware, layer=0)
#
#     # Load contract ABI
#     with open('./abis/OpenAiSimpleLLM.json') as f:
#         abi = json.load(f)
#
#     # Create contract instance
#     contract = web3.eth.contract(address=contract_address, abi=abi)
#     account = web3.eth.account.privateKeyToAccount(private_key)
#     nonce = web3.eth.getTransactionCount(account.address)
#
#     # Get user input
#     message = "HELLO"
#
#     # Send the message
#     transaction = contract.functions.sendMessage(message).buildTransaction({
#         'from': account.address,
#         'nonce': nonce,
#         'gas': 2000000,
#         'gasPrice': web3.toWei('50', 'gwei')
#     })
#     signed_txn = web3.eth.account.signTransaction(transaction, private_key)
#     tx_hash = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
#
#     # Wait for the transaction to be mined
#     receipt = web3.eth.waitForTransactionReceipt(tx_hash)
#     print(f"Message sent, tx hash: {receipt.transactionHash.hex()}")
#     print(f"Chat started with message: \"{message}\"")
#
#     # Read the LLM response on-chain
#     while True:
#         response = contract.functions.response().call()
#         if response:
#             print("Response from contract:", response)
#             break
#         await asyncio.sleep(2)

def summarize_text_galadriel(text: str) -> str:
    message = ("Your are an AI assistant that helps summarize articles."
               f"Here is the article text:{text}")

    content = getResonseFromGaladrielWithRequest(message)
    print(content)

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
                "content": "Your are an AI assistant that helps summarize articles. Here are the guidelines to follow: You will be provided with an article. Identify Key Points: Read the entire article carefully and identify the key points, main ideas, and important details. Concise Summary: Provide a concise summary of the article, capturing the essence and significant information without unnecessary details. Maintain Context: Ensure that the summary maintains the context and intent of the original article. Highlight Critical Information: Highlight any critical information, statistics, quotes, or data that are essential to understanding the article's main points. Clear Structure: Organize the summary in a clear and structured format, making it easy to read and understand. Length Limit: Ensure the final summary is no longer than 4000 characters."
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

    # Extract the value of "content"
    content = data[0]["choices"][0]["delta"]["content"]

    return content


def summarize_text(text: str) -> str:
    response = client.chat.completions.create(model="gpt-4o",
                                              messages=[
                                                  {
                                                      "role": "system",
                                                      "content": f"""
Your are an AI assistant that helps summarize articles. Here are the guidelines to follow:
You will be provided with an article.
Identify Key Points: Read the entire article carefully and identify the key points, main ideas, and important details.
Concise Summary: Provide a concise summary of the article, capturing the essence and significant information without unnecessary details.
Maintain Context: Ensure that the summary maintains the context and intent of the original article.
Highlight Critical Information: Highlight any critical information, statistics, quotes, or data that are essential to understanding the article's main points.
Clear Structure: Organize the summary in a clear and structured format, making it easy to read and understand.
Length Limit: Ensure the final summary is no longer than 4000 characters.
"""
                                                  },
                                                  {
                                                      "role": "user",
                                                      "content": f"Here is the article text:\n\n{text}"
                                                  }
                                              ])
    summary = response.choices[0].message.content.strip()
    return summary


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


def get_text_file_path(file_path: str) -> str:
    directory, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)
    new_file_path = os.path.join(directory, f"{name}.txt")
    return new_file_path


def save_string_to_file(text: str, file_path: str) -> str:
    with open(file_path, "w") as file:
        file.write(text)
    return file_path


def transcribe_audio(file_path: str) -> str:
    try:
        # Create a Deepgram client using the API key
        deepgram = DeepgramClient(deepgram_api_key)

        with open(file_path, "rb") as file:
            buffer_data = file.read()

        payload: FileSource = {
            "buffer": buffer_data,
        }

        options = PrerecordedOptions(
            smart_format=True,
            punctuate=True,
            paragraphs=True,
            language="ru",
            model="nova-2"
        )
        file_response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)

        json_response = file_response.to_dict()

        results = json_response['results']
        alternatives = results['channels'][0]['alternatives']
        paragraphs = alternatives[0]['paragraphs']
        transcript = paragraphs['transcript']
        return transcript

    except Exception as e:
        return ""


@dp.message(F.voice)
@dp.message(F.audio)
async def get_audio(message: types.Message):
    mess = await message.reply("Скачиваем файл...")
    try:
        voice_object = message.voice or message.audio
        file_id = voice_object.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
    except Exception as E:
        await message.reply(f"Ошибка: не получилось скачать файл.\n{E}")
        raise E
    finally:
        await mess.delete()

    mess = await message.reply("Преобразуем аудио в текст...")
    try:
        text = transcribe_audio(file_path)
        os.remove(file_path)

        if text == "":
            await message.reply(f"Аудио сообщение не содержит текста")
        else:
            text_file_path = save_string_to_file(text, get_text_file_path(file_path))
            text_file = FSInputFile(text_file_path, filename="summary.txt")
            await mess.reply_document(text_file)
            os.remove(text_file_path)
    except Exception as E:
        await message.reply(f"Ошибка: не получилось сделать summary.\n{E}")
        raise E
    finally:
        await mess.delete()

    mess = await message.reply("Собираем summary текста...")
    try:
        summary = summarize_text(text)
        await send_long_message(message, summary)
    except Exception as E:
        await message.reply(f"Ошибка: не получилось собрать summary.\n{E}")
        raise E
    finally:
        await mess.delete()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
