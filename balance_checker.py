#!/usr/bin/env python3
"""
Ethereum Balance Checker using direct RPC calls

A tool for checking ETH balances using direct Ethereum RPC calls instead of Etherscan API.
This is much faster for bulk balance checking operations.
"""

import time
from typing import List, Dict, Optional
import requests


class EthereumRPCChecker:
    """Ethereum balance checker using direct RPC calls."""
    
    # Public RPC endpoints (no API key required)
    PUBLIC_RPCS = {
        "mainnet": [
            "https://ethereum-rpc.publicnode.com",
            "https://rpc.ankr.com/eth",
            "https://eth.llamarpc.com",
            "https://ethereum.blockpi.network/v1/rpc/public",
        ],
        "goerli": [
            "https://goerli.blockpi.network/v1/rpc/public",
            "https://rpc.ankr.com/eth_goerli",
        ],
        "sepolia": [
            "https://sepolia.blockpi.network/v1/rpc/public",
            "https://rpc.ankr.com/eth_sepolia",
        ]
    }
    
    # Private RPC endpoints (require API key)
    PRIVATE_RPCS = {
        "infura": {
            "mainnet": "https://mainnet.infura.io/v3/{api_key}",
            "goerli": "https://goerli.infura.io/v3/{api_key}",
            "sepolia": "https://sepolia.infura.io/v3/{api_key}",
        },
        "alchemy": {
            "mainnet": "https://eth-mainnet.g.alchemy.com/v2/{api_key}",
            "goerli": "https://eth-goerli.g.alchemy.com/v2/{api_key}",
            "sepolia": "https://eth-sepolia.g.alchemy.com/v2/{api_key}",
        }
    }
    
    def __init__(self, network: str = "mainnet", rpc_url: Optional[str] = None, 
                 provider: Optional[str] = None, api_key: Optional[str] = None, 
                 timeout: int = 10, max_retries: int = 3):
        """
        Initialize the RPC checker.
        
        Args:
            network: Network name ('mainnet', 'goerli', 'sepolia')
            rpc_url: Custom RPC URL (overrides other settings)
            provider: Provider name ('infura', 'alchemy', or None for public)
            api_key: API key for private providers
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries per request
        """
        self.network = network.lower()
        self.timeout = timeout
        self.max_retries = max_retries
        self.request_count = 0
        self.session = requests.Session()
        
        # Set up RPC URL
        if rpc_url:
            self.rpc_url = rpc_url
        elif provider and api_key:
            if provider not in self.PRIVATE_RPCS:
                raise ValueError(f"Unknown provider: {provider}")
            if self.network not in self.PRIVATE_RPCS[provider]:
                raise ValueError(f"Network {self.network} not supported by {provider}")
            self.rpc_url = self.PRIVATE_RPCS[provider][self.network].format(api_key=api_key)
        else:
            # Use public RPC
            if self.network not in self.PUBLIC_RPCS:
                raise ValueError(f"Unsupported network: {self.network}")
            self.rpc_url = self.PUBLIC_RPCS[self.network][0]  # Use first available
            
        print(f"Using RPC: {self.rpc_url}")
    
    def _make_rpc_call(self, method: str, params: List) -> Optional[str]:
        """Make a JSON-RPC call to the Ethereum node."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_count
        }
        
        self.request_count += 1
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    self.rpc_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                data = response.json()
                if "error" in data:
                    print(f"RPC error: {data['error']}")
                    return None
                
                return data.get("result")
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"RPC call failed after {self.max_retries} attempts: {e}")
                    return None
                time.sleep(0.1 * (attempt + 1))  # Exponential backoff
        
        return None
    
    def get_eth_balance(self, address: str) -> Optional[float]:
        """
        Get ETH balance for a single address.
        
        Args:
            address: Ethereum address
            
        Returns:
            Balance in ETH, or None if error
        """
        if not address.startswith('0x'):
            address = '0x' + address
            
        # Get balance in wei
        balance_wei = self._make_rpc_call("eth_getBalance", [address, "latest"])
        if balance_wei is None:
            return None
        
        try:
            # Convert hex to int, then wei to ETH
            balance_wei_int = int(balance_wei, 16)
            balance_eth = balance_wei_int / 10**18
            return balance_eth
        except (ValueError, TypeError) as e:
            print(f"Error converting balance: {e}")
            return None
    
    def get_multiple_balances(self, addresses: List[str]) -> Dict[str, Optional[float]]:
        """
        Get ETH balances for multiple addresses using batch request.
        
        Args:
            addresses: List of Ethereum addresses
            
        Returns:
            Dictionary mapping address to balance (in ETH)
        """
        if not addresses:
            return {}
        
        # Prepare batch request
        batch_payload = []
        for i, address in enumerate(addresses):
            if not address.startswith('0x'):
                address = '0x' + address
            
            batch_payload.append({
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [address, "latest"],
                "id": self.request_count + i
            })
        
        self.request_count += len(addresses)
        
        # Make batch request
        results = {}
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    self.rpc_url,
                    json=batch_payload,
                    timeout=self.timeout * 2,  # Double timeout for batch
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                batch_results = response.json()
                if not isinstance(batch_results, list):
                    batch_results = [batch_results]
                
                for i, result in enumerate(batch_results):
                    if i >= len(addresses):
                        break
                        
                    address = addresses[i]
                    if "error" in result:
                        print(f"RPC error for {address}: {result['error']}")
                        results[address] = None
                    else:
                        try:
                            balance_wei = result.get("result")
                            if balance_wei:
                                balance_wei_int = int(balance_wei, 16)
                                balance_eth = balance_wei_int / 10**18
                                results[address] = balance_eth
                            else:
                                results[address] = None
                        except (ValueError, TypeError):
                            results[address] = None
                
                return results
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"Batch RPC call failed after {self.max_retries} attempts: {e}")
                    # Return None for all addresses
                    return {addr: None for addr in addresses}
                time.sleep(0.1 * (attempt + 1))
        
        return results
    
    def has_balance(self, address: str, min_balance: float = 0.0) -> bool:
        """
        Check if an address has a balance above the minimum threshold.
        
        Args:
            address: Ethereum address
            min_balance: Minimum balance threshold in ETH
            
        Returns:
            True if balance is above threshold, False otherwise
        """
        balance = self.get_eth_balance(address)
        return balance is not None and balance > min_balance
    
    def get_transaction_count(self, address: str) -> Optional[int]:
        """
        Get the transaction count (nonce) for an address.
        Useful to check if an address has been used.
        
        Args:
            address: Ethereum address
            
        Returns:
            Transaction count, or None if error
        """
        if not address.startswith('0x'):
            address = '0x' + address
            
        nonce_hex = self._make_rpc_call("eth_getTransactionCount", [address, "latest"])
        if nonce_hex is None:
            return None
        
        try:
            return int(nonce_hex, 16)
        except (ValueError, TypeError):
            return None
    
    def get_block_number(self) -> Optional[int]:
        """Get the current block number."""
        block_hex = self._make_rpc_call("eth_blockNumber", [])
        if block_hex is None:
            return None
        
        try:
            return int(block_hex, 16)
        except (ValueError, TypeError):
            return None


def format_balance(balance: Optional[float]) -> str:
    """Format balance for display."""
    if balance is None:
        return "Unknown"
    if balance == 0:
        return "0 ETH"
    if balance < 0.001:
        return f"{balance:.8f} ETH"
    return f"{balance:.6f} ETH"


def test_rpc_checker():
    """Test the RPC checker with a known address."""
    checker = EthereumRPCChecker()
    
    # Test with Vitalik's address
    vitalik_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    balance = checker.get_eth_balance(vitalik_address)
    print(f"Vitalik's balance: {format_balance(balance)}")
    
    # Test batch request
    test_addresses = [
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",  # Vitalik
        "0x0000000000000000000000000000000000000000",  # Zero address
    ]
    
    balances = checker.get_multiple_balances(test_addresses)
    for addr, bal in balances.items():
        print(f"{addr}: {format_balance(bal)}")


if __name__ == "__main__":
    test_rpc_checker()
