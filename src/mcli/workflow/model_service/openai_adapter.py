"""
OpenAI API Adapter for MCLI Model Service

Provides OpenAI-compatible endpoints for tools like aider.
"""

import json
import time
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class Message(BaseModel):
    """OpenAI message format"""

    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """OpenAI chat completion request"""

    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None
    max_tokens: Optional[int] = 2048
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    user: Optional[str] = None


class ChatCompletionChoice(BaseModel):
    """Chat completion choice"""

    index: int
    message: Message
    finish_reason: str


class Usage(BaseModel):
    """Token usage information"""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI chat completion response"""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage


class ModelInfo(BaseModel):
    """Model information"""

    id: str
    object: str = "model"
    created: int
    owned_by: str = "mcli"


class ModelListResponse(BaseModel):
    """Model list response"""

    object: str = "list"
    data: List[ModelInfo]


class APIKeyManager:
    """Manages API key authentication"""

    def __init__(self):
        self.valid_keys: Dict[str, Dict[str, Any]] = {}

    def add_key(self, key: str, name: str = "default", metadata: Optional[Dict] = None):
        """Add a valid API key"""
        self.valid_keys[key] = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "usage_count": 0,
        }

    def validate_key(self, key: str) -> bool:
        """Validate an API key"""
        if key in self.valid_keys:
            self.valid_keys[key]["usage_count"] += 1
            return True
        return False

    def remove_key(self, key: str):
        """Remove an API key"""
        if key in self.valid_keys:
            del self.valid_keys[key]

    def list_keys(self) -> List[Dict[str, Any]]:
        """List all API keys (without showing the actual key)"""
        return [
            {
                "name": info["name"],
                "created_at": info["created_at"],
                "usage_count": info["usage_count"],
            }
            for info in self.valid_keys.values()
        ]


class OpenAIAdapter:
    """Adapter to make MCLI model service OpenAI-compatible"""

    def __init__(self, model_manager, require_auth: bool = True):
        self.model_manager = model_manager
        self.require_auth = require_auth
        self.api_key_manager = APIKeyManager()
        self.router = APIRouter(prefix="/v1")

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup OpenAI-compatible routes"""

        @self.router.get("/models", response_model=ModelListResponse)
        async def list_models(api_key: str = Depends(self.verify_api_key)):
            """List available models (OpenAI compatible)"""
            models = []

            # Get loaded models from model manager
            if hasattr(self.model_manager, "loaded_models"):
                for model_name in self.model_manager.loaded_models.keys():
                    models.append(
                        ModelInfo(
                            id=model_name,
                            object="model",
                            created=int(time.time()),
                            owned_by="mcli",
                        )
                    )

            # If no models loaded, return available lightweight models
            if not models:
                from .lightweight_model_server import LIGHTWEIGHT_MODELS

                for model_key in LIGHTWEIGHT_MODELS.keys():
                    models.append(
                        ModelInfo(
                            id=model_key,
                            object="model",
                            created=int(time.time()),
                            owned_by="mcli",
                        )
                    )

            return ModelListResponse(object="list", data=models)

        @self.router.post("/chat/completions")
        async def create_chat_completion(
            request: ChatCompletionRequest, api_key: str = Depends(self.verify_api_key)
        ):
            """Create a chat completion (OpenAI compatible)"""
            try:
                # Extract the conversation history
                messages = request.messages
                prompt = self._messages_to_prompt(messages)

                # Generate response using the model
                if request.stream:
                    return StreamingResponse(
                        self._generate_stream(request, prompt), media_type="text/event-stream"
                    )
                else:
                    response_text = await self._generate_response(request, prompt)

                    # Create OpenAI-compatible response
                    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
                    response = ChatCompletionResponse(
                        id=completion_id,
                        object="chat.completion",
                        created=int(time.time()),
                        model=request.model,
                        choices=[
                            ChatCompletionChoice(
                                index=0,
                                message=Message(role="assistant", content=response_text),
                                finish_reason="stop",
                            )
                        ],
                        usage=Usage(
                            prompt_tokens=len(prompt.split()),
                            completion_tokens=len(response_text.split()),
                            total_tokens=len(prompt.split()) + len(response_text.split()),
                        ),
                    )

                    return response

            except Exception as e:
                logger.error(f"Error in chat completion: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _messages_to_prompt(self, messages: List[Message]) -> str:
        """Convert OpenAI messages format to a simple prompt"""
        prompt_parts = []

        for message in messages:
            role = message.role
            content = message.content

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        return "\n\n".join(prompt_parts)

    async def _generate_response(self, request: ChatCompletionRequest, prompt: str) -> str:
        """Generate a response from the model"""
        try:
            # Use the lightweight model server if available
            if hasattr(self.model_manager, "loaded_models"):
                # Get the first loaded model or the requested model
                model_name = request.model
                available_models = list(self.model_manager.loaded_models.keys())

                if not available_models:
                    # Try to auto-load the requested model
                    from .lightweight_model_server import LIGHTWEIGHT_MODELS

                    if model_name in LIGHTWEIGHT_MODELS:
                        logger.info(f"Auto-loading model: {model_name}")
                        success = self.model_manager.download_and_load_model(model_name)
                        if not success:
                            raise HTTPException(
                                status_code=500, detail=f"Failed to load model: {model_name}"
                            )
                    else:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Model {model_name} not found. Available models: {list(LIGHTWEIGHT_MODELS.keys())}",
                        )

                # Generate response (placeholder - would use actual model inference)
                response = f"This is a response from MCLI model service using {model_name}. In a production environment, this would use the actual model for inference.\n\nYour prompt was: {prompt[:100]}..."

                return response
            else:
                return "Model manager not properly initialized"

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _generate_stream(
        self, request: ChatCompletionRequest, prompt: str
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response"""
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"

        # Generate response
        response_text = await self._generate_response(request, prompt)

        # Stream the response word by word
        words = response_text.split()
        for i, word in enumerate(words):
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": word + " " if i < len(words) - 1 else word},
                        "finish_reason": None if i < len(words) - 1 else "stop",
                    }
                ],
            }

            yield f"data: {json.dumps(chunk)}\n\n"

        # Send final message
        yield "data: [DONE]\n\n"

    async def verify_api_key(self, authorization: Optional[str] = Header(None)) -> str:
        """Verify API key from Authorization header"""
        if not self.require_auth:
            return "no-auth-required"

        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract API key from "Bearer <key>" format
        try:
            scheme, key = authorization.split()
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate the API key
        if not self.api_key_manager.validate_key(key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return key


def create_openai_adapter(model_manager, require_auth: bool = True) -> OpenAIAdapter:
    """Create an OpenAI adapter instance"""
    return OpenAIAdapter(model_manager, require_auth)
