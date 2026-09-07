"""Canonical evidence hashing and Web3 submission."""
from __future__ import annotations
import hashlib, json, os
from web3 import Web3

ABI = [{"inputs":[{"internalType":"bytes32","name":"evidenceHash","type":"bytes32"}],"name":"storeRecord","outputs":[{"internalType":"uint256","name":"id","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"id","type":"uint256"}],"name":"getRecord","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"id","type":"uint256"},{"indexed":True,"internalType":"bytes32","name":"evidenceHash","type":"bytes32"},{"indexed":True,"internalType":"address","name":"sender","type":"address"},{"indexed":False,"internalType":"uint256","name":"timestamp","type":"uint256"}],"name":"RecordStored","type":"event"}]

def canonical_json(record: dict) -> str: return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def evidence_hash(record: dict) -> str:
    # Every field is canonicalized before hashing: editing any field invalidates verification.
    return hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()

def _contract():
    rpc, address = os.getenv("WEB3_RPC_URL"), os.getenv("CONTRACT_ADDRESS")
    if not rpc or not address: raise RuntimeError("WEB3_RPC_URL and CONTRACT_ADDRESS must be set in .env.")
    web3 = Web3(Web3.HTTPProvider(rpc))
    if not web3.is_connected(): raise RuntimeError(f"Cannot connect to RPC: {rpc}")
    return web3, web3.eth.contract(address=Web3.to_checksum_address(address), abi=ABI)

def submit_record(record: dict) -> dict:
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key: raise RuntimeError("PRIVATE_KEY is missing; cannot sign a transaction.")
    web3, contract = _contract(); account = web3.eth.account.from_key(private_key); digest = evidence_hash(record)
    tx = contract.functions.storeRecord(bytes.fromhex(digest)).build_transaction({"from": account.address, "nonce": web3.eth.get_transaction_count(account.address), "chainId": web3.eth.chain_id, "gasPrice": web3.eth.gas_price})
    signed = account.sign_transaction(tx); tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    event = contract.events.RecordStored().process_receipt(receipt)[0]["args"]
    return {"evidence_hash": digest, "tx_hash": tx_hash.hex(), "block_number": receipt.blockNumber, "record_id": int(event["id"]), "chain_timestamp": int(event["timestamp"]), "contract_address": contract.address}

def fetch_record_hash(record_id: int) -> str:
    _, contract = _contract(); value, _, _ = contract.functions.getRecord(record_id).call()
    return value.hex().removeprefix("0x")
