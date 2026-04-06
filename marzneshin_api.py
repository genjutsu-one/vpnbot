import os
import httpx
from datetime import datetime, timedelta
from typing import Optional
import secrets
import string

MARZNESHIN_API_URL = os.getenv("MARZNESHIN_API_URL", "http://localhost:8000")
MARZNESHIN_ADMIN_USERNAME = os.getenv("MARZNESHIN_ADMIN_USERNAME", "admin")
MARZNESHIN_ADMIN_PASSWORD = os.getenv("MARZNESHIN_ADMIN_PASSWORD", "admin")
SERVICE_ID = int(os.getenv("SERVICE_ID", "1"))
INBOUND_ID = int(os.getenv("INBOUND_ID", "1"))


class MarzneshinAPI:
    def __init__(self):
        self.api_url = MARZNESHIN_API_URL
        self.admin_username = MARZNESHIN_ADMIN_USERNAME
        self.admin_password = MARZNESHIN_ADMIN_PASSWORD
        self.token = None
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        await self.authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def authenticate(self):
        """Get admin token from Marzneshin"""
        try:
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
        except Exception as e:
            raise Exception(f"Failed to authenticate with Marzneshin: {e}")
    
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
            
            # Calculate expire date
            expire_date = (datetime.utcnow() + timedelta(days=subscription_days)).isoformat()
            
            # Create user with unlimited data
            user_data = {
                "username": username,
                "expire_date": expire_date,
                "data_limit": 0,  # unlimited
                "services": [SERVICE_ID]
            }
            
            response = await self.client.post(
                f"{self.api_url}/api/users",
                json=user_data,
                headers=self._get_headers()
            )
            response.raise_for_status()
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
            expire_date = (datetime.utcnow() + timedelta(days=expire_days)).isoformat()
            user_data = {
                "expire_date": expire_date
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
        try:
            # This returns the actual subscription config
            response = await self.client.get(
                f"{self.api_url}/sub/{username}/{subscription_key}/xray"
            )
            response.raise_for_status()
            # Return the link format for display
            return f"{self.api_url}/sub/{username}/{subscription_key}"
        except Exception as e:
            raise Exception(f"Failed to get subscription link: {e}")
    
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
                f"{self.api_url}/api/users?page={page}&size={size}",
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
