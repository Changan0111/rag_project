import httpx
from typing import Optional, List, AsyncGenerator
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self._client = httpx.AsyncClient(timeout=120.0, trust_env=False)

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("LLMService HTTP client closed")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_keep": 24
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except httpx.HTTPError as e:
            logger.error(f"LLM generation error: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_keep": 24
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", 
                url, 
                json=payload,
                headers={"Accept": "application/x-ndjson"}
            ) as response:
                response.raise_for_status()
                
                buffer = ""
                async for chunk in response.aiter_bytes():
                    if chunk:
                        buffer += chunk.decode("utf-8", errors="ignore")
                        
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            
                            if not line:
                                continue
                                
                            try:
                                data = json.loads(line)
                                if data.get("response"):
                                    content = data["response"]
                                    yield content
                                    
                                if data.get("done"):
                                    return
                            except json.JSONDecodeError as e:
                                logger.warning(f"[Stream] Failed to parse line: {line[:100]}... Error: {e}")
                                continue

    async def chat(
        self,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_keep": 24
            }
        }

        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
        except httpx.HTTPError as e:
            logger.error(f"LLM chat error: {e}")
            raise
