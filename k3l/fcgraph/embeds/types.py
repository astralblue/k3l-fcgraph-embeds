"""Farcaster data type models using Pydantic V2."""

import base64
from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator


def _parse_hash(value: Union[str, bytes]) -> bytes:
    """Parse hash from various string formats into bytes.
    
    Accepts:
    - "0x..." (canonical Farcaster format)  
    - "..." (hex without prefix)
    - Base64 encoded strings
    
    Returns exactly 20 bytes (160 bits) for cast hashes.
    """
    if isinstance(value, bytes):
        if len(value) != 20:
            raise ValueError(f"Hash must be exactly 20 bytes, got {len(value)}")
        return value
    
    if not isinstance(value, str):
        raise ValueError("Hash must be string or bytes")
    
    # Try 0x-prefixed hex first (canonical)
    if value.startswith("0x"):
        try:
            result = bytes.fromhex(value[2:])
            if len(result) != 20:
                raise ValueError(f"Hash must be exactly 20 bytes, got {len(result)}")
            return result
        except ValueError as e:
            if "non-hexadecimal" in str(e):
                raise ValueError(f"Invalid hex format: {value}")
            raise
    
    # Try plain hex (40 chars = 20 bytes)
    if len(value) == 40:
        try:
            result = bytes.fromhex(value)
            if len(result) != 20:
                raise ValueError(f"Hash must be exactly 20 bytes, got {len(result)}")
            return result
        except ValueError:
            pass  # Fall through to base64 attempt
    
    # Try base64 
    try:
        result = base64.b64decode(value)
        if len(result) != 20:
            raise ValueError(f"Hash must be exactly 20 bytes, got {len(result)}")
        return result
    except ValueError as e:
        if "Hash must be exactly 20 bytes" in str(e):
            raise  # Re-raise our own length validation error
        pass  # Fall through to final error for invalid base64
    except Exception:
        pass
    
    raise ValueError(f"Unable to parse hash from: {value}")


class CastId(BaseModel):
    """A Farcaster Cast ID consisting of user FID and cast hash."""
    
    fid: int = Field(description="Farcaster ID of the user who created the cast")
    hash: bytes = Field(description="Unique hash of the specific cast")
    
    @field_validator('hash', mode='before')
    @classmethod
    def validate_hash(cls, v):
        """Validate and normalize hash from various formats."""
        return _parse_hash(v)


class Embed(BaseModel):
    """A Farcaster embed that can contain either a URL or a cast reference."""
    
    url: Optional[str] = Field(None, description="URL string for web links or Ethereum assets")
    cast_id: Optional[CastId] = Field(None, description="Reference to another cast for quote casts")
    
    def model_post_init(self, __context) -> None:
        """Validate that exactly one of url or cast_id is provided."""
        if not ((self.url is None) ^ (self.cast_id is None)):
            raise ValueError("Exactly one of 'url' or 'cast_id' must be provided")