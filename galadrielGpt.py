import json
import time
from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv()

# Загрузка переменных окружения из файла .env
RPC_URL = os.getenv('RPC_URL')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
CONTRACT_ADDRESS = os.getenv('SIMPLE_LLM_CONTRACT_ADDRESS')

if not RPC_URL:
    raise ValueError("Missing RPC_URL in .env")
if not PRIVATE_KEY:
    raise ValueError("Missing PRIVATE_KEY in .env")
if not CONTRACT_ADDRESS:
    raise ValueError("Missing SIMPLE_LLM_CONTRACT_ADDRESS in .env")

# Инициализация провайдера и web3
web3 = Web3(Web3.HTTPProvider(RPC_URL))
if not web3.is_connected():
    raise ConnectionError("Unable to connect to Ethereum node")

# Загрузка ABI
with open('abis/OpenAiSimpleLLM.json', 'r') as file:
    contract_abi = json.load(file)

# Инициализация контракта
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)
account = web3.eth.account.from_key(PRIVATE_KEY)


def get_user_input(prompt):
    return input(prompt)


def send_message_to_contract(message):
    nonce = web3.eth.get_transaction_count(account.address)
    txn = contract.functions.sendMessage(message).build_transaction({
        'chainId': 696969,
        'gas': 2000000,
        'gasPrice': web3.to_wei('5', 'gwei'),
        'nonce': nonce
    })

    signed_txn = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)

    return tx_hash


def wait_for_transaction_receipt(tx_hash):
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt


def get_contract_response():
    while True:
        response = contract.functions.response().call()
        if response:
            return response
        time.sleep(2)


def getResonseFromGaladrielWithRequest(message) -> str:
    # chain_id = web3.eth.chain_id
    # print(f"Chain ID: {chain_id}")
    # message = get_user_input("Message ChatGPT: ")
    print(message)
    tx_hash = send_message_to_contract(message)
    print(f"Message sent, tx hash: {tx_hash.hex()}")
    receipt = wait_for_transaction_receipt(tx_hash)
    print(f"Message sent, tx hash: {receipt['transactionHash'].hex()}")
    print(f"Chat started with message: \"{message}\"")

    response = get_contract_response()
    print("Response from contract:", response)
    return response

