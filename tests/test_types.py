"""Tests for k3l.fcgraph.embeds.types module."""

import base64
import json

import pytest
from pydantic import ValidationError

from k3l.fcgraph.embeds.types import (
    CastId,
    Embed,
    Embeds,
    _parse_hash,
    parse_embeds_from_string,
)


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
        with pytest.raises(
            ValueError, match="Hash must be string, bytes, or Buffer dict"
        ):
            _parse_hash(123)

    def test_parse_hash_unparseable_string(self):
        """Test error when string cannot be parsed in any format."""
        unparseable = "not-a-valid-hash-format"
        with pytest.raises(ValueError, match="Unable to parse hash from"):
            _parse_hash(unparseable)

    def test_parse_hash_buffer_format(self):
        """Test parsing Node.js Buffer format."""
        buffer_data = {
            "data": [
                204,
                4,
                137,
                65,
                96,
                25,
                108,
                225,
                113,
                91,
                149,
                2,
                253,
                153,
                15,
                240,
                37,
                116,
                198,
                118,
            ],
            "type": "Buffer",
        }
        expected = bytes(
            [
                204,
                4,
                137,
                65,
                96,
                25,
                108,
                225,
                113,
                91,
                149,
                2,
                253,
                153,
                15,
                240,
                37,
                116,
                198,
                118,
            ]
        )
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
        buffer_data = {
            "data": [
                256,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
            ],
            "type": "Buffer",
        }
        with pytest.raises(ValueError, match="Invalid Buffer data"):
            _parse_hash(buffer_data)

    def test_parse_hash_buffer_missing_type(self):
        """Test error when Buffer format is missing type field."""
        buffer_data = {
            "data": [
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
            ]
        }
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
        cast_id = CastId(fid=12345, hash="0xd2b1ddc6c88e865a33cb1a565e0058d757042974")
        assert cast_id.fid == 12345
        assert cast_id.hash == bytes.fromhex("d2b1ddc6c88e865a33cb1a565e0058d757042974")

    def test_cast_id_valid_plain_hex(self):
        """Test CastId creation with valid plain hex hash."""
        cast_id = CastId(fid=67890, hash="d2b1ddc6c88e865a33cb1a565e0058d757042974")
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
            "data": [
                204,
                4,
                137,
                65,
                96,
                25,
                108,
                225,
                113,
                91,
                149,
                2,
                253,
                153,
                15,
                240,
                37,
                116,
                198,
                118,
            ],
            "type": "Buffer",
        }
        cast_id = CastId(fid=253133, hash=buffer_hash)
        assert cast_id.fid == 253133
        expected_bytes = bytes(
            [
                204,
                4,
                137,
                65,
                96,
                25,
                108,
                225,
                113,
                91,
                149,
                2,
                253,
                153,
                15,
                240,
                37,
                116,
                198,
                118,
            ]
        )
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
        cast_id = CastId(fid=123, hash="0xd2b1ddc6c88e865a33cb1a565e0058d757042974")
        embed = Embed(cast_id=cast_id)
        assert embed.cast_id == cast_id
        assert embed.url is None

    def test_embed_with_both_url_and_cast_id(self):
        """Test Embed validation error when both url and cast_id are provided."""
        cast_id = CastId(fid=123, hash="0xd2b1ddc6c88e865a33cb1a565e0058d757042974")
        with pytest.raises(
            ValidationError, match="Exactly one of 'url' or 'cast_id' must be provided"
        ):
            Embed(url="https://example.com", cast_id=cast_id)

    def test_embed_with_neither_url_nor_cast_id(self):
        """Test Embed validation error when neither url nor cast_id are provided."""
        with pytest.raises(
            ValidationError, match="Exactly one of 'url' or 'cast_id' must be provided"
        ):
            Embed()


class TestEmbedsJsonSerialization:
    """Tests for JSON serialization/deserialization of embeds."""

    def test_embed_url_json_roundtrip(self):
        """Test JSON serialization and deserialization of URL embed."""
        embed = Embed(url="https://example.com")
        json_data = embed.model_dump()
        assert json_data == {"url": "https://example.com", "cast_id": None}

        # Test deserialization
        embed_restored = Embed.model_validate(json_data)
        assert embed_restored.url == "https://example.com"
        assert embed_restored.cast_id is None

    def test_embed_cast_id_json_roundtrip(self):
        """Test JSON serialization and deserialization of CastId embed."""
        cast_id = CastId(fid=123, hash="0xd2b1ddc6c88e865a33cb1a565e0058d757042974")
        embed = Embed(cast_id=cast_id)

        json_data = embed.model_dump()
        expected_hash_bytes = bytes.fromhex("d2b1ddc6c88e865a33cb1a565e0058d757042974")
        assert json_data == {
            "url": None,
            "cast_id": {"fid": 123, "hash": expected_hash_bytes},
        }

        # Test deserialization
        embed_restored = Embed.model_validate(json_data)
        assert embed_restored.url is None
        assert embed_restored.cast_id.fid == 123
        assert embed_restored.cast_id.hash == expected_hash_bytes

    def test_embeds_array_json_serialization(self):
        """Test JSON serialization of an array of embeds."""
        cast_id = CastId(fid=456, hash="0xa48dd46161d8e57725f5e26e34ec19c13ff7f3b9")
        embeds = [
            Embed(url="https://example.com"),
            Embed(url="https://farcaster.xyz"),
            Embed(cast_id=cast_id),
        ]

        json_data = [embed.model_dump() for embed in embeds]
        expected_hash_bytes = bytes.fromhex("a48dd46161d8e57725f5e26e34ec19c13ff7f3b9")

        assert json_data == [
            {"url": "https://example.com", "cast_id": None},
            {"url": "https://farcaster.xyz", "cast_id": None},
            {"url": None, "cast_id": {"fid": 456, "hash": expected_hash_bytes}},
        ]

    def test_embeds_array_json_deserialization(self):
        """Test JSON deserialization of an array of embeds."""
        json_data = [
            {"url": "https://example.com", "cast_id": None},
            {"url": "https://farcaster.xyz", "cast_id": None},
            {
                "url": None,
                "cast_id": {
                    "fid": 789,
                    "hash": "0xd2b1ddc6c88e865a33cb1a565e0058d757042974",
                },
            },
        ]

        embeds = [Embed.model_validate(item) for item in json_data]

        assert len(embeds) == 3
        assert embeds[0].url == "https://example.com"
        assert embeds[0].cast_id is None
        assert embeds[1].url == "https://farcaster.xyz"
        assert embeds[1].cast_id is None
        assert embeds[2].url is None
        assert embeds[2].cast_id.fid == 789
        assert embeds[2].cast_id.hash == bytes.fromhex(
            "d2b1ddc6c88e865a33cb1a565e0058d757042974"
        )

    def test_embeds_array_with_buffer_format(self):
        """Test embeds array with Buffer format hash."""
        json_data = [
            {"url": "https://example.com", "cast_id": None},
            {
                "url": None,
                "cast_id": {
                    "fid": 253133,
                    "hash": {
                        "data": [
                            204,
                            4,
                            137,
                            65,
                            96,
                            25,
                            108,
                            225,
                            113,
                            91,
                            149,
                            2,
                            253,
                            153,
                            15,
                            240,
                            37,
                            116,
                            198,
                            118,
                        ],
                        "type": "Buffer",
                    },
                },
            },
        ]

        embeds = [Embed.model_validate(item) for item in json_data]

        assert len(embeds) == 2
        assert embeds[0].url == "https://example.com"
        assert embeds[1].cast_id.fid == 253133
        expected_bytes = bytes(
            [
                204,
                4,
                137,
                65,
                96,
                25,
                108,
                225,
                113,
                91,
                149,
                2,
                253,
                153,
                15,
                240,
                37,
                116,
                198,
                118,
            ]
        )
        assert embeds[1].cast_id.hash == expected_bytes

    def test_embeds_array_json_string_roundtrip(self):
        """Test JSON string serialization using hex format for compatibility."""
        cast_id = CastId(fid=999, hash="0xd2b1ddc6c88e865a33cb1a565e0058d757042974")
        embeds = [Embed(url="https://example.com"), Embed(cast_id=cast_id)]

        # For real-world JSON serialization, we'd typically convert bytes to hex strings
        def serialize_embed(embed):
            data = embed.model_dump()
            if data.get("cast_id") and data["cast_id"].get("hash"):
                # Convert bytes to hex string for JSON compatibility
                data["cast_id"]["hash"] = "0x" + data["cast_id"]["hash"].hex()
            return data

        json_data = [serialize_embed(embed) for embed in embeds]
        json_string = json.dumps(json_data)

        # Parse back from JSON string
        parsed_data = json.loads(json_string)
        embeds_restored = [Embed.model_validate(item) for item in parsed_data]

        assert len(embeds_restored) == 2
        assert embeds_restored[0].url == "https://example.com"
        assert embeds_restored[1].cast_id.fid == 999
        assert embeds_restored[1].cast_id.hash == bytes.fromhex(
            "d2b1ddc6c88e865a33cb1a565e0058d757042974"
        )


class TestDegenerateStringParsing:
    """Tests for parsing embeds from degenerate string representations."""

    def test_camel_case_field_names(self):
        """Test that castId (camelCase) field name is accepted."""
        data = {
            "url": None,
            "castId": {
                "fid": 123,
                "hash": "0xd2b1ddc6c88e865a33cb1a565e0058d757042974",
            },
        }
        embed = Embed.model_validate(data)
        assert embed.cast_id.fid == 123
        assert embed.cast_id.hash == bytes.fromhex(
            "d2b1ddc6c88e865a33cb1a565e0058d757042974"
        )

    def test_snake_case_field_names(self):
        """Test that cast_id (snake_case) field name still works."""
        data = {
            "url": None,
            "cast_id": {
                "fid": 456,
                "hash": "0xd2b1ddc6c88e865a33cb1a565e0058d757042974",
            },
        }
        embed = Embed.model_validate(data)
        assert embed.cast_id.fid == 456
        assert embed.cast_id.hash == bytes.fromhex(
            "d2b1ddc6c88e865a33cb1a565e0058d757042974"
        )

    def test_parse_single_line_url_embed(self):
        """Test parsing single line URL embed string."""
        embeds_str = "[{'url': \"https://meco.ham.cooking/swap?token=0xb9d7B18d6C94190DC248E6BD8a3EE62288ce8b07&symbol=Hom's&type=clanker\"}]"
        embeds = parse_embeds_from_string(embeds_str)

        assert len(embeds) == 1
        assert (
            embeds[0].url
            == "https://meco.ham.cooking/swap?token=0xb9d7B18d6C94190DC248E6BD8a3EE62288ce8b07&symbol=Hom's&type=clanker"
        )
        assert embeds[0].cast_id is None

    def test_parse_single_line_cast_embed(self):
        """Test parsing single line cast embed string with Buffer format."""
        embeds_str = "[{'castId': {'fid': 417907, 'hash': {'data': [119, 26, 101, 27, 69, 195, 221, 4, 79, 138, 26, 149, 22, 60, 35, 132, 113, 18, 32, 16], 'type': 'Buffer'}}}]"
        embeds = parse_embeds_from_string(embeds_str)

        assert len(embeds) == 1
        assert embeds[0].url is None
        assert embeds[0].cast_id.fid == 417907
        expected_bytes = bytes(
            [
                119,
                26,
                101,
                27,
                69,
                195,
                221,
                4,
                79,
                138,
                26,
                149,
                22,
                60,
                35,
                132,
                113,
                18,
                32,
                16,
            ]
        )
        assert embeds[0].cast_id.hash == expected_bytes

    def test_parse_each_example_separately(self):
        """Test parsing each example line as separate embeds field values."""
        # First embeds field
        embeds_str1 = "[{'url': \"https://meco.ham.cooking/swap?token=0xb9d7B18d6C94190DC248E6BD8a3EE62288ce8b07&symbol=Hom's&type=clanker\"}]"
        embeds1 = parse_embeds_from_string(embeds_str1)
        assert len(embeds1) == 1
        assert (
            embeds1[0].url
            == "https://meco.ham.cooking/swap?token=0xb9d7B18d6C94190DC248E6BD8a3EE62288ce8b07&symbol=Hom's&type=clanker"
        )

        # Second embeds field
        embeds_str2 = (
            "[{'url': 'https://leaderboard.frm.lol/leaderboard/user/338631/1000'}]"
        )
        embeds2 = parse_embeds_from_string(embeds_str2)
        assert len(embeds2) == 1
        assert (
            embeds2[0].url == "https://leaderboard.frm.lol/leaderboard/user/338631/1000"
        )

        # Third embeds field
        embeds_str3 = "[{'castId': {'fid': 417907, 'hash': {'data': [119, 26, 101, 27, 69, 195, 221, 4, 79, 138, 26, 149, 22, 60, 35, 132, 113, 18, 32, 16], 'type': 'Buffer'}}}]"
        embeds3 = parse_embeds_from_string(embeds_str3)
        assert len(embeds3) == 1
        assert embeds3[0].cast_id.fid == 417907
        expected_bytes = bytes(
            [
                119,
                26,
                101,
                27,
                69,
                195,
                221,
                4,
                79,
                138,
                26,
                149,
                22,
                60,
                35,
                132,
                113,
                18,
                32,
                16,
            ]
        )
        assert embeds3[0].cast_id.hash == expected_bytes

    def test_parse_multiple_embeds_in_single_array(self):
        """Test parsing multiple embeds within a single embeds field."""
        embeds_str = "[{'url': 'https://example.com'}, {'castId': {'fid': 123, 'hash': '0xd2b1ddc6c88e865a33cb1a565e0058d757042974'}}]"
        embeds = parse_embeds_from_string(embeds_str)

        assert len(embeds) == 2
        assert embeds[0].url == "https://example.com"
        assert embeds[0].cast_id is None
        assert embeds[1].url is None
        assert embeds[1].cast_id.fid == 123

    def test_parse_empty_string(self):
        """Test parsing empty string returns empty list."""
        assert parse_embeds_from_string("") == []
        assert parse_embeds_from_string("   \n  \n   ") == []

    def test_parse_invalid_syntax(self):
        """Test error handling for invalid Python syntax."""
        with pytest.raises(ValueError, match="Failed to parse embeds string"):
            parse_embeds_from_string("[{'url': 'invalid syntax")

    def test_parse_non_list_format(self):
        """Test error handling when line doesn't contain a list."""
        with pytest.raises(ValueError, match="Expected list"):
            parse_embeds_from_string("{'url': 'https://example.com'}")

    def test_parse_invalid_embed_format(self):
        """Test error handling when list contains non-dict items."""
        with pytest.raises(ValueError, match="Expected dict in embeds list"):
            parse_embeds_from_string("['not-a-dict']")


class TestEmbedsModel:
    """Tests for the Embeds Pydantic model with sequence protocol."""

    def test_embeds_from_list_of_dicts(self):
        """Test creating Embeds from list of dictionaries."""
        data = [
            {"url": "https://example.com"},
            {
                "castId": {
                    "fid": 123,
                    "hash": "0xd2b1ddc6c88e865a33cb1a565e0058d757042974",
                }
            },
        ]
        embeds = Embeds(data)

        assert len(embeds) == 2
        assert embeds[0].url == "https://example.com"
        assert embeds[1].cast_id.fid == 123

    def test_embeds_from_list_of_embed_objects(self):
        """Test creating Embeds from list of Embed objects."""
        cast_id = CastId(fid=456, hash="0xa48dd46161d8e57725f5e26e34ec19c13ff7f3b9")
        embed_list = [Embed(url="https://farcaster.xyz"), Embed(cast_id=cast_id)]
        embeds = Embeds(embed_list)

        assert len(embeds) == 2
        assert embeds[0].url == "https://farcaster.xyz"
        assert embeds[1].cast_id.fid == 456

    def test_embeds_from_string_representation(self):
        """Test creating Embeds from string representation."""
        embeds_str = "[{'url': 'https://example.com'}, {'castId': {'fid': 789, 'hash': '0xd2b1ddc6c88e865a33cb1a565e0058d757042974'}}]"
        embeds = Embeds(embeds_str)

        assert len(embeds) == 2
        assert embeds[0].url == "https://example.com"
        assert embeds[1].cast_id.fid == 789

    def test_embeds_from_degenerate_string(self):
        """Test creating Embeds from the degenerate string formats."""
        # Test each of the original examples
        embeds1 = Embeds(
            "[{'url': \"https://meco.ham.cooking/swap?token=0xb9d7B18d6C94190DC248E6BD8a3EE62288ce8b07&symbol=Hom's&type=clanker\"}]"
        )
        assert len(embeds1) == 1
        assert "meco.ham.cooking" in embeds1[0].url

        embeds2 = Embeds(
            "[{'url': 'https://leaderboard.frm.lol/leaderboard/user/338631/1000'}]"
        )
        assert len(embeds2) == 1
        assert (
            embeds2[0].url == "https://leaderboard.frm.lol/leaderboard/user/338631/1000"
        )

        embeds3 = Embeds(
            "[{'castId': {'fid': 417907, 'hash': {'data': [119, 26, 101, 27, 69, 195, 221, 4, 79, 138, 26, 149, 22, 60, 35, 132, 113, 18, 32, 16], 'type': 'Buffer'}}}]"
        )
        assert len(embeds3) == 1
        assert embeds3[0].cast_id.fid == 417907

    def test_embeds_from_empty_values(self):
        """Test creating Embeds from empty values."""
        assert len(Embeds(None)) == 0
        assert len(Embeds("")) == 0
        assert len(Embeds([])) == 0
        assert len(Embeds("[]")) == 0

    def test_sequence_protocol_indexing(self):
        """Test sequence protocol indexing operations."""
        embeds = Embeds(
            [
                {"url": "https://example.com"},
                {"url": "https://farcaster.xyz"},
                {
                    "castId": {
                        "fid": 123,
                        "hash": "0xd2b1ddc6c88e865a33cb1a565e0058d757042974",
                    }
                },
            ]
        )

        # Test indexing
        assert embeds[0].url == "https://example.com"
        assert embeds[1].url == "https://farcaster.xyz"
        assert embeds[2].cast_id.fid == 123

        # Test negative indexing
        assert embeds[-1].cast_id.fid == 123

        # Test slicing
        first_two = embeds[:2]
        assert len(first_two) == 2

    def test_sequence_protocol_iteration(self):
        """Test sequence protocol iteration."""
        embeds = Embeds(
            [{"url": "https://example.com"}, {"url": "https://farcaster.xyz"}]
        )

        urls = [embed.url for embed in embeds]
        assert urls == ["https://example.com", "https://farcaster.xyz"]

    def test_list_like_operations(self):
        """Test list-like operations."""
        embeds = Embeds([{"url": "https://example.com"}])

        # Test append
        new_embed = Embed(url="https://farcaster.xyz")
        embeds.append(new_embed)
        assert len(embeds) == 2
        assert embeds[1].url == "https://farcaster.xyz"

        # Test count
        assert embeds.count(new_embed) == 1

        # Test pop
        popped = embeds.pop()
        assert popped.url == "https://farcaster.xyz"
        assert len(embeds) == 1

    def test_sequence_protocol_membership(self):
        """Test sequence protocol membership operations."""
        embed1 = Embed(url="https://example.com")
        embed2 = Embed(url="https://farcaster.xyz")
        embeds = Embeds([embed1])

        assert embed1 in embeds
        assert embed2 not in embeds

    def test_embeds_repr_and_str(self):
        """Test string representations."""
        embeds = Embeds([{"url": "https://example.com"}])

        repr_str = repr(embeds)
        assert "Embeds(" in repr_str
        assert "https://example.com" in repr_str

        str_str = str(embeds)
        assert "https://example.com" in str_str

    def test_embeds_json_serialization(self):
        """Test JSON serialization of Embeds model."""
        embeds = Embeds(
            [
                {"url": "https://example.com"},
                {
                    "castId": {
                        "fid": 123,
                        "hash": "0xd2b1ddc6c88e865a33cb1a565e0058d757042974",
                    }
                },
            ]
        )

        # Test model_dump
        data = embeds.model_dump()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["url"] == "https://example.com"
        assert data[1]["cast_id"]["fid"] == 123

        # Test round-trip
        embeds_restored = Embeds(data)
        assert len(embeds_restored) == 2
        assert embeds_restored[0].url == "https://example.com"
        assert embeds_restored[1].cast_id.fid == 123
