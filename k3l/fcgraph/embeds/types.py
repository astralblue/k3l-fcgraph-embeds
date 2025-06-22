"""Farcaster data type models using Pydantic V2."""

import ast
import base64
from typing import Iterator, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator


def _parse_hash(value: Union[str, bytes, dict]) -> bytes:
    """Parse hash from various formats into bytes.

    Accepts:
    - "0x..." (canonical Farcaster format)
    - "..." (hex without prefix)
    - Base64 encoded strings
    - {"data": [byte_array], "type": "Buffer"} (Node.js Buffer format)

    Returns exactly 20 bytes (160 bits) for cast hashes.
    """
    if isinstance(value, bytes):
        if len(value) != 20:
            raise ValueError(f"Hash must be exactly 20 bytes, got {len(value)}")
        return value

    # Handle Node.js Buffer format: {"data": [byte_array], "type": "Buffer"}
    if isinstance(value, dict):
        if value.get("type") == "Buffer" and "data" in value:
            data = value["data"]
            if not isinstance(data, list):
                raise ValueError("Buffer data must be a list of integers")
            if len(data) != 20:
                raise ValueError(f"Hash must be exactly 20 bytes, got {len(data)}")
            try:
                result = bytes(data)
                return result
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid Buffer data: {e}")
        else:
            raise ValueError(
                "Hash dict must be Buffer format with 'data' and 'type' fields"
            )

    if not isinstance(value, str):
        raise ValueError("Hash must be string, bytes, or Buffer dict")

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

    @field_validator("hash", mode="before")
    @classmethod
    def validate_hash(cls, v):
        """Validate and normalize hash from various formats."""
        return _parse_hash(v)


class Embed(BaseModel):
    """A Farcaster embed that can contain either a URL or a cast reference."""

    model_config = ConfigDict(populate_by_name=True)

    url: Optional[str] = Field(
        None, description="URL string for web links or Ethereum assets"
    )
    cast_id: Optional[CastId] = Field(
        None, alias="castId", description="Reference to another cast for quote casts"
    )

    def model_post_init(self, __context) -> None:
        """Validate that exactly one of url or cast_id is provided."""
        if not ((self.url is None) ^ (self.cast_id is None)):
            raise ValueError("Exactly one of 'url' or 'cast_id' must be provided")


def parse_embeds_from_string(embeds_str: str) -> List[Embed]:
    """Parse embeds from string representation.

    Handles degenerate cases where a single embeds field is represented as:
    - String literal of Python list: "[{'url': '...'}]"
    - String literal containing multiple embeds: "[{'url': '...'}, {'castId': {...}}]"

    Args:
        embeds_str: String representation of a single embeds array

    Returns:
        List of Embed objects

    Raises:
        ValueError: If string cannot be parsed
    """
    if not embeds_str.strip():
        return []

    try:
        # Use ast.literal_eval to safely parse Python literal
        parsed_data = ast.literal_eval(embeds_str.strip())

        # Should be a list of embed dictionaries
        if not isinstance(parsed_data, list):
            raise ValueError(f"Expected list, got {type(parsed_data)}")

        embeds = []
        for item in parsed_data:
            if isinstance(item, dict):
                embed = Embed.model_validate(item)
                embeds.append(embed)
            else:
                raise ValueError(f"Expected dict in embeds list, got {type(item)}")

        return embeds

    except (ValueError, SyntaxError) as e:
        raise ValueError(f"Failed to parse embeds string: {e}")


class Embeds(RootModel[List[Embed]]):
    """A Pydantic model representing a list of embeds with flexible input parsing.

    Supports multiple input formats:
    - List of Embed objects: [Embed(...), Embed(...)]
    - List of dictionaries: [{"url": "..."}, {"castId": {...}}]
    - String representation: "[{'url': '...'}]"
    - Empty values: None, "", []

    Implements sequence-like behavior.
    """

    @field_validator("root", mode="before")
    @classmethod
    def parse_embeds(cls, value):
        """Parse embeds from various input formats."""
        if value is None or value == "":
            return []
        elif isinstance(value, str):
            return parse_embeds_from_string(value)
        else:
            return value

    # Sequence protocol implementation
    def __len__(self) -> int:
        return len(self.root)

    def __getitem__(self, index):
        return self.root[index]

    def __iter__(self) -> Iterator[Embed]:
        return iter(self.root)

    def __contains__(self, item) -> bool:
        return item in self.root

    # Additional list-like methods for convenience
    def append(self, value: Embed) -> None:
        self.root.append(value)

    def extend(self, values) -> None:
        self.root.extend(values)

    def insert(self, index: int, value: Embed) -> None:
        self.root.insert(index, value)

    def remove(self, value: Embed) -> None:
        self.root.remove(value)

    def pop(self, index: int = -1) -> Embed:
        return self.root.pop(index)

    def clear(self) -> None:
        self.root.clear()

    def count(self, value: Embed) -> int:
        return self.root.count(value)

    def index(self, value: Embed, start: int = 0, stop: int = None) -> int:
        if stop is None:
            return self.root.index(value, start)
        else:
            return self.root.index(value, start, stop)

    def reverse(self) -> None:
        self.root.reverse()

    def __repr__(self) -> str:
        return f"Embeds({self.root!r})"

    def __str__(self) -> str:
        return str(self.root)
