import os
import time
from dotenv import load_dotenv
from web3 import Web3
from apscheduler.schedulers.blocking import BlockingScheduler

load_dotenv()

# === CONFIGURACIÓN ===
RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ACCOUNT_ADDRESS = Web3.to_checksum_address(os.getenv("ACCOUNT_ADDRESS"))

ROUTER_ADDRESS = Web3.to_checksum_address("0x165C3410fC91EF562C50559f7d2289fEbed552d9")
PWR_TOKEN = Web3.to_checksum_address("0x3Eb3B7b3D95Cb3699295D7868F85e43b56AeeFcB")
WPLS_TOKEN = Web3.to_checksum_address("0xA1077a294dDE1B09bB078844df40758a5D0f9a27")

AMOUNT_IN_WPLS = Web3.to_wei(100, 'ether')  # 100 WPLS
SLIPPAGE = 0.05  # 5%
GAS_LIMIT = 600000

w3 = Web3(Web3.HTTPProvider(RPC_URL))

with open("router_abi.json") as f:
    router_abi = f.read()

router = w3.eth.contract(address=ROUTER_ADDRESS, abi=router_abi)
step = "buy"  # Alterna entre 'buy' y 'sell'


def buy_pwr():
    global step
    print("Ejecutando COMPRA de PWR...")
    deadline = int(time.time()) + 600
    path = [WPLS_TOKEN, PWR_TOKEN]

    txn = router.functions.swapExactETHForTokensSupportingFeeOnTransferTokens(
        0,  # amountOutMin = 0 (puedes ajustar si quieres mínimo)
        path,
        ACCOUNT_ADDRESS,
        deadline
    ).build_transaction({
        'from': ACCOUNT_ADDRESS,
        'value': AMOUNT_IN_WPLS,
        'gas': GAS_LIMIT,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
    })

    signed = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_Transaction)
    print(f"Compra enviada. Tx: {tx_hash.hex()}")
    step = "sell"


def sell_pwr():
    global step
    print("Ejecutando VENTA de PWR...")
    deadline = int(time.time()) + 600
    path = [PWR_TOKEN, WPLS_TOKEN]

    # Verificamos balance y aprobamos PWR
    balance = w3.eth.contract(address=PWR_TOKEN, abi=[
        {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
         "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}],
         "type": "function"},
        {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
         "name": "approve", "outputs": [{"name": "success", "type": "bool"}], "type": "function"},
    ])
    pwr_balance = balance.functions.balanceOf(ACCOUNT_ADDRESS).call()
    balance.functions.approve(ROUTER_ADDRESS, pwr_balance).transact({'from': ACCOUNT_ADDRESS})

    txn = router.functions.swapExactTokensForETHSupportingFeeOnTransferTokens(
        pwr_balance,
        0,
        path,
        ACCOUNT_ADDRESS,
        deadline
    ).build_transaction({
        'from': ACCOUNT_ADDRESS,
        'gas': GAS_LIMIT,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
    })

    signed = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_Transaction)
    print(f"Venta enviada. Tx: {tx_hash.hex()}")
    step = "buy"


def run_bot():
    global step
    try:
        if step == "buy":
            buy_pwr()
        else:
            sell_pwr()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(run_bot, 'interval', hours=8)
    print("Bot iniciado. Ejecutando cada 8 horas...")
    run_bot()  # Primer run inmediato
    scheduler.start()
