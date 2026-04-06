import os
import httpx
from datetime import datetime, timedelta
from typing import Optional
import secrets
import string
import logging
import json

logger = logging.getLogger(__name__)

MARZNESHIN_API_URL = os.getenv("MARZNESHIN_API_URL", "http://localhost:8000")
MARZNESHIN_ADMIN_USERNAME = os.getenv("MARZNESHIN_ADMIN_USERNAME", "admin")
MARZNESHIN_ADMIN_PASSWORD = os.getenv("MARZNESHIN_ADMIN_PASSWORD", "admin")
MARZNESHIN_ACCESS_TOKEN = os.getenv("MARZNESHIN_ACCESS_TOKEN", "")  # Optional pre-obtained token
SERVICE_ID = int(os.getenv("SERVICE_ID", "1"))
INBOUND_ID = int(os.getenv("INBOUND_ID", "1"))
TOKEN_CACHE_FILE = ".token_cache"


class MarzneshinAPI:
    def __init__(self):
        self.api_url = MARZNESHIN_API_URL
        self.admin_username = MARZNESHIN_ADMIN_USERNAME
        self.admin_password = MARZNESHIN_ADMIN_PASSWORD
        # Use pre-obtained token from .env if available
        self.token = MARZNESHIN_ACCESS_TOKEN if MARZNESHIN_ACCESS_TOKEN else None
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        await self.authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def _make_request(self, method: str, url: str, retry_on_401: bool = True, **kwargs):
        """Make HTTP request with automatic retry on 401 (token expired)"""
        try:
            response = await self.client.request(method, url, headers=self._get_headers(), **kwargs)
            
            # If 401 and retry enabled, try to re-authenticate and retry
            if response.status_code == 401 and retry_on_401:
                logger.warning("Token expired (401), re-authenticating...")
                await self.authenticate()
                response = await self.client.request(method, url, headers=self._get_headers(), **kwargs)
            
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"Request failed ({method} {url}): {e}")
            raise
    
    async def authenticate(self):
        """Get admin token from Marzneshin"""
        try:
            # If token already set (from .env), skip authentication
            if self.token:
                logger.info("Token already set (from .env or cache)")
                return
            
            # Try to load cached token first
            cached_token = self._load_cached_token()
            if cached_token:
                logger.info("Using cached token")
                self.token = cached_token
                return
            
            data = {
                "username": self.admin_username,
                "password": self.admin_password,
                "grant_type": "password"
            }
            response = await self.client.post(
                f"{self.api_url}/api/admins/token",
                data=data
            )
            response.raise_for_status()
            token_data = response.json()
            self.token = token_data.get("access_token")
            
            # Cache the token
            self._save_cached_token(self.token)
            logger.info("Token obtained and cached")
        except Exception as e:
            raise Exception(f"Failed to authenticate with Marzneshin: {e}")
    
    def _load_cached_token(self) -> Optional[str]:
        """Load token from cache file if it exists"""
        try:
            if os.path.exists(TOKEN_CACHE_FILE):
                with open(TOKEN_CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    # Check if token is still valid (not expired)
                    if data.get("expires_at"):
                        expires_at = datetime.fromisoformat(data["expires_at"])
                        if expires_at > datetime.utcnow():
                            return data.get("token")
                    os.remove(TOKEN_CACHE_FILE)  # Remove expired token
        except Exception as e:
            logger.debug(f"Failed to load cached token: {e}")
        return None
    
    def _save_cached_token(self, token: str):
        """Save token to cache file with expiration time"""
        try:
            # Token expires in 24 hours (Marzneshin default)
            expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
            with open(TOKEN_CACHE_FILE, 'w') as f:
                json.dump({
                    "token": token,
                    "expires_at": expires_at
                }, f)
        except Exception as e:
            logger.warning(f"Failed to cache token: {e}")
    
    def _get_headers(self):
        """Get headers with authentication token"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def create_user(self, telegram_id: int, subscription_days: int = 30) -> dict:
        """Create a new user in Marzneshin"""
        try:
            # Generate random suffix (8 digits)
            random_suffix = ''.join(secrets.choice(string.digits) for _ in range(8))
            username = f"{telegram_id}{random_suffix}"
            
            # Calculate expire date as ISO datetime string
            expire_datetime = datetime.utcnow() + timedelta(days=subscription_days)
            expire_date_str = expire_datetime.isoformat()
            
            # Create user with unlimited data (0 = unlimited)
            user_data = {
                "username": username,
                "expire_strategy": "fixed_date",
                "expire_date": expire_date_str,
                "data_limit": 0,  # 0 = unlimited
                "service_ids": [SERVICE_ID],
                "key": ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
            }
            
            response = await self._make_request(
                "POST",
                f"{self.api_url}/api/users",
                json=user_data
            )
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to create user: {e}")
    
    async def get_user(self, username: str) -> dict:
        """Get user information from Marzneshin"""
        try:
            response = await self.client.get(
                f"{self.api_url}/api/users/{username}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get user: {e}")
    
    async def modify_user(self, username: str, expire_days: int) -> dict:
        """Modify user subscription date"""
        try:
            expire_datetime = datetime.utcnow() + timedelta(days=expire_days)
            expire_date_str = expire_datetime.isoformat()
            user_data = {
                "expire_strategy": "fixed_date",
                "expire_date": expire_date_str
            }
            
            response = await self.client.put(
                f"{self.api_url}/api/users/{username}",
                json=user_data,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to modify user: {e}")
    
    async def delete_user(self, username: str) -> bool:
        """Delete user from Marzneshin"""
        try:
            response = await self.client.delete(
                f"{self.api_url}/api/users/{username}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return True
        except Exception as e:
            raise Exception(f"Failed to delete user: {e}")
    
    async def enable_user(self, username: str) -> dict:
        """Enable user"""
        try:
            response = await self.client.post(
                f"{self.api_url}/api/users/{username}/enable",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to enable user: {e}")
    
    async def disable_user(self, username: str) -> dict:
        """Disable user"""
        try:
            response = await self.client.post(
                f"{self.api_url}/api/users/{username}/disable",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to disable user: {e}")
    
    async def get_subscription_link(self, username: str, subscription_key: str) -> str:
        """Get subscription link for user"""
        return f"{self.api_url}/sub/{username}/{subscription_key}"
    
    async def revoke_user_subscription(self, username: str) -> dict:
        """Revoke user subscription keys"""
        try:
            response = await self.client.post(
                f"{self.api_url}/api/users/{username}/revoke_sub",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to revoke subscription: {e}")
    
    async def reset_user_data_usage(self, username: str) -> dict:
        """Reset user data usage"""
        try:
            response = await self.client.post(
                f"{self.api_url}/api/users/{username}/reset",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to reset data usage: {e}")
    
    async def get_users_list(self, page: int = 1, size: int = 10) -> dict:
        """Get list of users"""
        try:
            response = await self.client.get(
                f"{self.api_url}/api/users",
                params={"page": page, "size": size},
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get users list: {e}")
    
    async def get_system_stats(self) -> dict:
        """Get system statistics"""
        try:
            stats = {}
            
            # Get users stats
            response = await self.client.get(
                f"{self.api_url}/api/system/stats/users",
                headers=self._get_headers()
            )
            response.raise_for_status()
            stats['users'] = response.json()
            
            # Get nodes stats
            response = await self.client.get(
                f"{self.api_url}/api/system/stats/nodes",
                headers=self._get_headers()
            )
            response.raise_for_status()
            stats['nodes'] = response.json()
            
            return stats
        except Exception as e:
            raise Exception(f"Failed to get system stats: {e}")
    
    async def get_inbounds(self) -> list:
        """Get all inbounds"""
        try:
            response = await self.client.get(
                f"{self.api_url}/api/inbounds",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get inbounds: {e}")
    
    async def resync_node(self, node_id: int) -> dict:
        """Resynchronize a node"""
        try:
            response = await self.client.post(
                f"{self.api_url}/api/nodes/{node_id}/resync",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to resync node: {e}")
