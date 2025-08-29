#!/usr/bin/env python3
"""
SLIP-39 Passphrase Brute Force Tool

A tool for brute forcing SLIP-39 passphrases using word combinations.
"""

import argparse
import itertools
import math
import os
from typing import List, Iterator, Optional, Union, cast

from dotenv import load_dotenv
import slip39
from balance_checker import EthereumRPCChecker, format_balance


def generate_word_combinations(words: List[str]) -> Iterator[str]:
    """Generate all possible combinations of words from 1 to all words."""
    for length in range(1, len(words) + 1):
        for combo in itertools.combinations(words, length):
            # Try different orders of the selected words
            for perm in itertools.permutations(combo):
                yield " ".join(perm)


def parse_mnemonic_shares(mnemonic: str) -> List[str]:
    """
    Parse a single mnemonic string into individual SLIP-39 shares.
    
    SLIP-39 shares are typically separated by newlines or multiple spaces.
    Each share is a sequence of words.
    
    Args:
        mnemonic: Single string containing one or more SLIP-39 shares
        
    Returns:
        List of individual mnemonic share strings
    """
    if not mnemonic:
        return []
    
    # Split by newlines first, then by multiple spaces
    lines = mnemonic.strip().split('\n')
    shares = []
    
    for line in lines:
        line = line.strip()
        if line:
            # Check if this line contains multiple shares separated by multiple spaces
            # A typical SLIP-39 share has 20 or 33 words
            words = line.split()
            if len(words) >= 40:  # Likely multiple shares in one line
                # Try to split into chunks of ~20-33 words
                share_words = []
                for i, word in enumerate(words):
                    share_words.append(word)
                    # Check if we have a complete share (typically 20 or 33 words)
                    if len(share_words) in [20, 33] or i == len(words) - 1:
                        if share_words:
                            shares.append(' '.join(share_words))
                            share_words = []
            else:
                # Single share per line
                shares.append(line)
    
    return shares


def try_recover_slip39(mnemonic: str, passphrase: str) -> Optional[bytes]:
    """
    Try to recover SLIP-39 secret with given passphrase.
    
    Args:
        mnemonic: SLIP-39 mnemonic string (may contain multiple shares)
        passphrase: Passphrase to try
        
    Returns:
        Secret bytes if successful, None if failed
    """
    try:
        # Parse mnemonic into individual shares
        shares = parse_mnemonic_shares(mnemonic)
        if not shares:
            return None
            
        # Convert passphrase to bytes
        passphrase_bytes = passphrase.encode('utf-8') if passphrase else b""
        
        # Cast the list to the correct type for slip39.recover
        mnemonic_list: List[Union[str, slip39.Share]] = cast(List[Union[str, slip39.Share]], shares)
        secret = slip39.recover(mnemonic_list, passphrase=passphrase_bytes)
        return secret
    except Exception:
        return None


def brute_force_slip39_words(mnemonic: str, words: List[str], check_balance: bool = False, 
                           balance_checker: Optional[EthereumRPCChecker] = None) -> Optional[str]:
    """
    Brute force SLIP-39 passphrase using word combinations.
    
    Args:
        mnemonic: SLIP-39 mnemonic string (may contain multiple shares)
        words: List of words to use for combinations
        check_balance: Whether to check ETH balance of recovered addresses
        balance_checker: EthereumRPCChecker instance
        
    Returns:
        The successful passphrase if found, None otherwise
    """
    print(f"Starting SLIP-39 brute force attack with word combinations...")
    print(f"Using {len(words)} words: {', '.join(words)}")
    
    # First, try empty passphrase (most common case)
    print("Testing empty passphrase first...")
    secret = try_recover_slip39(mnemonic, "")
    if secret is not None:
        print(f"✅ SUCCESS! Empty passphrase works!")
        
        # Generate sample addresses
        try:
            eth_account = slip39.account(secret, 'ETH', "m/44'/60'/0'/0/0")
            btc_account = slip39.account(secret, 'BTC', "m/84'/0'/0'/0/0")
            
            print(f"Sample ETH address: {eth_account.address}")
            print(f"Sample BTC address: {btc_account.address}")
            
        except Exception as e:
            print(f"Error generating addresses: {e}")
        
        # Check balance if requested
        if check_balance and balance_checker:
            try:
                print(f"\nChecking balance on {balance_checker.network}...")
                balance = balance_checker.get_eth_balance(eth_account.address)
                print(f"ETH Balance: {format_balance(balance)}")
                
                if balance and balance > 0:
                    print("🎉 FOUND WALLET WITH BALANCE!")
                else:
                    print("ℹ️  Wallet recovered but no balance found")
                    
            except Exception as e:
                print(f"Error checking balance: {e}")
        
        return ""  # Empty string passphrase
    else:
        print("Empty passphrase doesn't work, trying word combinations...")
    
    # Calculate total combinations
    total_combinations = 0
    for r in range(1, len(words) + 1):
        combinations = math.comb(len(words), r)
        permutations_per_combo = math.factorial(r)
        total_combinations += combinations * permutations_per_combo
    
    print(f"Total combinations to try: {total_combinations:,}")
    
    attempt = 0
    for passphrase in generate_word_combinations(words):
        attempt += 1
        if attempt % 10 == 0:  # Show more frequent updates
            print(f"Attempt {attempt:,}: '{passphrase}'")
        elif attempt <= 10:  # Show first 10 attempts
            print(f"Attempt {attempt:,}: '{passphrase}'")
        
        secret = try_recover_slip39(mnemonic, passphrase)
        if secret is not None:
            print(f"SUCCESS! Passphrase found: '{passphrase}'")
            
            # Generate ETH address to check balance
            if check_balance and balance_checker:
                try:
                    # Generate ETH address from recovered secret
                    eth_account = slip39.account(secret, 'ETH', "m/44'/60'/0'/0/0")
                    print(f"ETH Address: {eth_account.address}")
                    
                    # Check balance
                    balance = balance_checker.get_eth_balance(eth_account.address)
                    print(f"ETH Balance: {format_balance(balance)}")
                    
                    if balance and balance > 0:
                        print("🎉 FOUND WALLET WITH BALANCE!")
                    else:
                        print("ℹ️  Wallet recovered but no balance found")
                        
                except Exception as e:
                    print(f"Error checking balance: {e}")
            
            return passphrase
    
    print("Brute force completed. Passphrase not found.")
    return None


def load_mnemonic_from_env() -> Optional[str]:
    """Load single SLIP-39 mnemonic from environment variable."""
    mnemonic = os.getenv('MNEMONIC', '').strip()
    return mnemonic if mnemonic else None


def load_words_from_env() -> List[str]:
    """Load word list from environment variable."""
    words_env = os.getenv('WORDS', '').strip()
    if not words_env:
        return []
    
    # Support both comma and space separated
    if ',' in words_env:
        words = [w.strip() for w in words_env.split(',') if w.strip()]
    else:
        words = words_env.split()
    
    return words


def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="SLIP-39 Passphrase Brute Force Tool")
    parser.add_argument("--mnemonic", help="SLIP-39 mnemonic string (overrides .env file)")
    parser.add_argument("--words", nargs="*", help="Words to use for passphrase combinations (overrides .env file)")
    parser.add_argument("--check-balance", action="store_true", help="Check ETH balance of recovered addresses")
    parser.add_argument("--network", default="mainnet", choices=["mainnet", "goerli", "sepolia"], 
                       help="Ethereum network to use for balance checking")
    
    args = parser.parse_args()
    
    # Load mnemonic from command line or .env file
    if args.mnemonic:
        mnemonic = args.mnemonic
    else:
        mnemonic = load_mnemonic_from_env()
    
    if not mnemonic:
        print("Error: No SLIP-39 mnemonic found. Please set MNEMONIC in .env file or provide --mnemonic argument.")
        return
    
    print(f"Loaded SLIP-39 mnemonic: {mnemonic[:50]}..." if len(mnemonic) > 50 else f"Loaded SLIP-39 mnemonic: {mnemonic}")
    
    # Load words from command line or .env file
    if args.words:
        words = args.words
    else:
        words = load_words_from_env()
    
    if not words:
        print("Error: No words found for brute force. Please set WORDS in .env file or provide --words argument.")
        return
    
    print(f"Loaded {len(words)} words for combinations: {', '.join(words)}")
    
    # Initialize balance checker if requested
    balance_checker = None
    if args.check_balance:
        # For RPC, we can use public endpoints without API key
        # But if user provides RPC_API_KEY, use it with a provider
        rpc_provider = os.getenv('RPC_PROVIDER', '').strip()  # 'infura', 'alchemy', etc.
        rpc_api_key = os.getenv('RPC_API_KEY', '').strip()
        custom_rpc_url = os.getenv('RPC_URL', '').strip()
        
        try:
            if custom_rpc_url:
                balance_checker = EthereumRPCChecker(network=args.network, rpc_url=custom_rpc_url)
            elif rpc_provider and rpc_api_key:
                balance_checker = EthereumRPCChecker(network=args.network, provider=rpc_provider, api_key=rpc_api_key)
            else:
                # Use public RPC (much faster than Etherscan, no API key needed)
                balance_checker = EthereumRPCChecker(network=args.network)
            
            print(f"Balance checking enabled for {args.network} network")
        except Exception as e:
            print(f"Warning: Could not initialize RPC checker: {e}")
            print("Balance checking disabled.")
            args.check_balance = False
    
    # Start brute force attack
    result = brute_force_slip39_words(mnemonic, words, args.check_balance, balance_checker)
    
    if result:
        print(f"\n🎉 SUCCESS! The passphrase is: '{result}'")
        
        # Try to recover the secret and show some info
        try:
            secret = try_recover_slip39(mnemonic, result)
            if secret:
                print(f"Secret recovered: {secret.hex()}")
                
                # Generate sample addresses
                eth_account = slip39.account(secret, 'ETH', "m/44'/60'/0'/0/0")
                btc_account = slip39.account(secret, 'BTC', "m/84'/0'/0'/0/0")
                
                print(f"Sample ETH address: {eth_account.address}")
                print(f"Sample BTC address: {btc_account.address}")
                
        except Exception as e:
            print(f"Error recovering secret: {e}")
    else:
        print("\n❌ Passphrase not found with the given parameters.")


if __name__ == "__main__":
    main()
