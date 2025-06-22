"""Tests for k3l.fcgraph.embeds.types module."""

import base64
import pytest
from pydantic import ValidationError

from k3l.fcgraph.embeds.types import CastId, Embed, _parse_hash


class TestParseHash:
    """Tests for the _parse_hash function."""
    
    def test_parse_hash_0x_prefixed_hex(self):
        """Test parsing 0x-prefixed hex format (canonical)."""
        hash_str = "0xd2b1ddc6c88e865a33cb1a565e0058d757042974"
        expected = bytes.fromhex("d2b1ddc6c88e865a33cb1a565e0058d757042974")
        assert _parse_hash(hash_str) == expected
    
    def test_parse_hash_plain_hex(self):
        """Test parsing plain hex format (no 0x prefix)."""
        hash_str = "d2b1ddc6c88e865a33cb1a565e0058d757042974"
        expected = bytes.fromhex("d2b1ddc6c88e865a33cb1a565e0058d757042974")
        assert _parse_hash(hash_str) == expected
    
    def test_parse_hash_base64(self):
        """Test parsing base64 format."""
        hash_bytes = bytes.fromhex("d2b1ddc6c88e865a33cb1a565e0058d757042974")
        hash_b64 = base64.b64encode(hash_bytes).decode()
        assert _parse_hash(hash_b64) == hash_bytes
    
    def test_parse_hash_bytes_input(self):
        """Test parsing when input is already bytes."""
        hash_bytes = bytes.fromhex("d2b1ddc6c88e865a33cb1a565e0058d757042974")
        assert _parse_hash(hash_bytes) == hash_bytes
    
    def test_parse_hash_wrong_length_bytes(self):
        """Test error when bytes input has wrong length."""
        wrong_length_bytes = b"short"
        with pytest.raises(ValueError, match="Hash must be exactly 20 bytes"):
            _parse_hash(wrong_length_bytes)
    
    def test_parse_hash_wrong_length_hex(self):
        """Test error when hex input has wrong length."""
        short_hex = "0x1234"
        with pytest.raises(ValueError, match="Hash must be exactly 20 bytes"):
            _parse_hash(short_hex)
    
    def test_parse_hash_wrong_length_base64(self):
        """Test error when base64 input decodes to wrong length."""
        short_b64 = base64.b64encode(b"short").decode()
        with pytest.raises(ValueError, match="Hash must be exactly 20 bytes"):
            _parse_hash(short_b64)
    
    def test_parse_hash_invalid_hex(self):
        """Test error when hex input contains invalid characters."""
        invalid_hex = "0xzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"
        with pytest.raises(ValueError, match="Invalid hex format"):
            _parse_hash(invalid_hex)
    
    def test_parse_hash_invalid_type(self):
        """Test error when input is not string, bytes, or dict."""
        with pytest.raises(ValueError, match="Hash must be string, bytes, or Buffer dict"):
            _parse_hash(123)
    
    def test_parse_hash_unparseable_string(self):
        """Test error when string cannot be parsed in any format."""
        unparseable = "not-a-valid-hash-format"
        with pytest.raises(ValueError, match="Unable to parse hash from"):
            _parse_hash(unparseable)
    
    def test_parse_hash_buffer_format(self):
        """Test parsing Node.js Buffer format."""
        buffer_data = {
            "data": [204, 4, 137, 65, 96, 25, 108, 225, 113, 91, 149, 2, 253, 153, 15, 240, 37, 116, 198, 118],
            "type": "Buffer"
        }
        expected = bytes([204, 4, 137, 65, 96, 25, 108, 225, 113, 91, 149, 2, 253, 153, 15, 240, 37, 116, 198, 118])
        assert _parse_hash(buffer_data) == expected
    
    def test_parse_hash_buffer_wrong_length(self):
        """Test error when Buffer data has wrong length."""
        buffer_data = {"data": [1, 2, 3], "type": "Buffer"}
        with pytest.raises(ValueError, match="Hash must be exactly 20 bytes"):
            _parse_hash(buffer_data)
    
    def test_parse_hash_buffer_invalid_data_type(self):
        """Test error when Buffer data is not a list."""
        buffer_data = {"data": "not-a-list", "type": "Buffer"}
        with pytest.raises(ValueError, match="Buffer data must be a list of integers"):
            _parse_hash(buffer_data)
    
    def test_parse_hash_buffer_invalid_byte_values(self):
        """Test error when Buffer data contains invalid byte values."""
        buffer_data = {"data": [256, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19], "type": "Buffer"}
        with pytest.raises(ValueError, match="Invalid Buffer data"):
            _parse_hash(buffer_data)
    
    def test_parse_hash_buffer_missing_type(self):
        """Test error when Buffer format is missing type field."""
        buffer_data = {"data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]}
        with pytest.raises(ValueError, match="Hash dict must be Buffer format"):
            _parse_hash(buffer_data)
    
    def test_parse_hash_buffer_missing_data(self):
        """Test error when Buffer format is missing data field."""
        buffer_data = {"type": "Buffer"}
        with pytest.raises(ValueError, match="Hash dict must be Buffer format"):
            _parse_hash(buffer_data)
    
    def test_parse_hash_dict_wrong_type(self):
        """Test error when dict has wrong type field."""
        wrong_data = {"data": [1, 2, 3], "type": "NotBuffer"}
        with pytest.raises(ValueError, match="Hash dict must be Buffer format"):
            _parse_hash(wrong_data)


class TestCastId:
    """Tests for the CastId model."""
    
    def test_cast_id_valid_0x_hex(self):
        """Test CastId creation with valid 0x-prefixed hex hash."""
        cast_id = CastId(
            fid=12345,
            hash="0xd2b1ddc6c88e865a33cb1a565e0058d757042974"
        )
        assert cast_id.fid == 12345
        assert cast_id.hash == bytes.fromhex("d2b1ddc6c88e865a33cb1a565e0058d757042974")
    
    def test_cast_id_valid_plain_hex(self):
        """Test CastId creation with valid plain hex hash."""
        cast_id = CastId(
            fid=67890,
            hash="d2b1ddc6c88e865a33cb1a565e0058d757042974"
        )
        assert cast_id.fid == 67890
        assert cast_id.hash == bytes.fromhex("d2b1ddc6c88e865a33cb1a565e0058d757042974")
    
    def test_cast_id_valid_base64(self):
        """Test CastId creation with valid base64 hash."""
        hash_bytes = bytes.fromhex("d2b1ddc6c88e865a33cb1a565e0058d757042974")
        hash_b64 = base64.b64encode(hash_bytes).decode()
        cast_id = CastId(fid=111, hash=hash_b64)
        assert cast_id.fid == 111
        assert cast_id.hash == hash_bytes
    
    def test_cast_id_valid_bytes(self):
        """Test CastId creation with bytes hash."""
        hash_bytes = bytes.fromhex("d2b1ddc6c88e865a33cb1a565e0058d757042974")
        cast_id = CastId(fid=222, hash=hash_bytes)
        assert cast_id.fid == 222
        assert cast_id.hash == hash_bytes
    
    def test_cast_id_invalid_hash(self):
        """Test CastId validation error with invalid hash."""
        with pytest.raises(ValidationError):
            CastId(fid=123, hash="invalid-hash")
    
    def test_cast_id_wrong_hash_length(self):
        """Test CastId validation error with wrong hash length."""
        with pytest.raises(ValidationError):
            CastId(fid=123, hash="0x1234")
    
    def test_cast_id_buffer_format(self):
        """Test CastId creation with Buffer format hash."""
        buffer_hash = {
            "data": [204, 4, 137, 65, 96, 25, 108, 225, 113, 91, 149, 2, 253, 153, 15, 240, 37, 116, 198, 118],
            "type": "Buffer"
        }
        cast_id = CastId(fid=253133, hash=buffer_hash)
        assert cast_id.fid == 253133
        expected_bytes = bytes([204, 4, 137, 65, 96, 25, 108, 225, 113, 91, 149, 2, 253, 153, 15, 240, 37, 116, 198, 118])
        assert cast_id.hash == expected_bytes


class TestEmbed:
    """Tests for the Embed model."""
    
    def test_embed_with_url(self):
        """Test Embed creation with URL."""
        embed = Embed(url="https://example.com")
        assert embed.url == "https://example.com"
        assert embed.cast_id is None
    
    def test_embed_with_cast_id(self):
        """Test Embed creation with CastId."""
        cast_id = CastId(
            fid=123,
            hash="0xd2b1ddc6c88e865a33cb1a565e0058d757042974"
        )
        embed = Embed(cast_id=cast_id)
        assert embed.cast_id == cast_id
        assert embed.url is None
    
    def test_embed_with_both_url_and_cast_id(self):
        """Test Embed validation error when both url and cast_id are provided."""
        cast_id = CastId(
            fid=123,
            hash="0xd2b1ddc6c88e865a33cb1a565e0058d757042974"
        )
        with pytest.raises(ValidationError, match="Exactly one of 'url' or 'cast_id' must be provided"):
            Embed(url="https://example.com", cast_id=cast_id)
    
    def test_embed_with_neither_url_nor_cast_id(self):
        """Test Embed validation error when neither url nor cast_id are provided."""
        with pytest.raises(ValidationError, match="Exactly one of 'url' or 'cast_id' must be provided"):
            Embed()