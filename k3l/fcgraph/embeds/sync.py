"""Asynchronous synchronization functions for embedding cast data using asyncpg.

This module provides high-performance async functions for synchronizing Farcaster cast
embed data from source databases (like Neynar) to normalized target tables. It handles
malformed data, provides batch processing, and supports incremental updates.

Key features:
- High-performance async processing using asyncpg
- Incremental sync using timestamp watermarks
- Robust parsing of malformed embed data
- Batch processing with configurable sizes
- Comprehensive error reporting and statistics
- Connection-based API for production use

Example:
    >>> import asyncio
    >>> import asyncpg
    >>> from datetime import datetime
    >>> from k3l.fcgraph.embeds import sync_embeds_async
    >>>
    >>> async def sync_recent_data():
    ...     source_conn = await asyncpg.connect("postgresql://source")
    ...     target_conn = await asyncpg.connect("postgresql://target")
    ...
    ...     try:
    ...         result = await sync_embeds_async(
    ...             source_conn, target_conn,
    ...             min_updated_at=datetime.now().replace(hour=0)
    ...         )
    ...         print(f"Processed {result.casts_processed} casts")
    ...     finally:
    ...         await source_conn.close()
    ...         await target_conn.close()
    >>>
    >>> asyncio.run(sync_recent_data())
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg
from sqlalchemy import create_engine

from .types import Embeds

logger = logging.getLogger(__name__)


class EmbedSyncResult:
    """Result of embed synchronization operation.

    Contains comprehensive statistics and error information from a sync operation.
    Use this to monitor sync performance, track errors, and implement retry logic.

    Attributes:
        casts_processed (int): Number of casts processed from source
        embeds_extracted (int): Number of embeds successfully parsed
        embeds_inserted (int): Number of embeds successfully inserted to target
        errors (int): Total number of errors encountered
        max_updated_at (datetime, optional): Latest updated_at timestamp processed
        error_details (List[str]): Detailed error messages for debugging

    Examples:
        >>> result = await sync_embeds_async(source_conn, target_conn, min_timestamp)
        >>> print(f"Success rate: {result.embeds_inserted}/{result.embeds_extracted}")
        >>> if result.errors > 0:
        ...     print("Errors encountered:")
        ...     for error in result.error_details:
        ...         print(f"  - {error}")
    """

    def __init__(self):
        self.casts_processed = 0
        self.embeds_extracted = 0
        self.embeds_inserted = 0
        self.errors = 0
        self.max_updated_at: Optional[datetime] = None
        self.error_details: List[str] = []


async def sync_embeds_async(
    source_conn: asyncpg.Connection,
    target_conn: asyncpg.Connection,
    min_updated_at: datetime,
    batch_size: int = 1000,
    source_schema: str = "neynarv2",
    target_schema: str = "public",
) -> EmbedSyncResult:
    """Asynchronously synchronize embeds from source casts table to normalized embeds table.

    Args:
        source_conn: asyncpg connection to source database
        target_conn: asyncpg connection to target database
        min_updated_at: Minimum updated_at timestamp to process
        batch_size: Number of casts to process in each batch
        source_schema: Schema containing source casts table (default: "neynarv2")
        target_schema: Schema containing target embeds table (default: "public")

    Returns:
        EmbedSyncResult with processing statistics
    """
    result = EmbedSyncResult()

    try:
        # Process in batches
        offset = 0
        while True:
            batch_result = await _process_batch_async(
                source_conn,
                target_conn,
                min_updated_at,
                offset,
                batch_size,
                source_schema,
                target_schema,
            )

            # Accumulate results
            result.casts_processed += batch_result.casts_processed
            result.embeds_extracted += batch_result.embeds_extracted
            result.embeds_inserted += batch_result.embeds_inserted
            result.errors += batch_result.errors
            result.error_details.extend(batch_result.error_details)

            # Update max timestamp
            if batch_result.max_updated_at:
                if (
                    not result.max_updated_at
                    or batch_result.max_updated_at > result.max_updated_at
                ):
                    result.max_updated_at = batch_result.max_updated_at

            # Check if we're done
            if batch_result.casts_processed < batch_size:
                break

            offset += batch_size

    except Exception as e:
        logger.error(f"Error during embed sync: {e}")
        result.errors += 1
        result.error_details.append(f"Sync error: {str(e)}")

    return result


async def _process_batch_async(
    source_conn: asyncpg.Connection,
    target_conn: asyncpg.Connection,
    min_updated_at: datetime,
    offset: int,
    batch_size: int,
    source_schema: str,
    target_schema: str,
) -> EmbedSyncResult:
    """Process a single batch of casts asynchronously."""
    result = EmbedSyncResult()

    # Query source casts
    query = f"""
    SELECT 
        hash,
        fid,
        embeds,
        updated_at
    FROM {source_schema}.casts 
    WHERE updated_at >= $1
    ORDER BY updated_at, id
    OFFSET $2 LIMIT $3
    """

    casts = await source_conn.fetch(query, min_updated_at, offset, batch_size)
    result.casts_processed = len(casts)

    if not casts:
        return result

    # Prepare batch data for insertion
    embed_rows = []

    for cast in casts:
        try:
            # Update max timestamp
            if not result.max_updated_at or cast["updated_at"] > result.max_updated_at:
                result.max_updated_at = cast["updated_at"]

            # Parse embeds using the library
            embeds_data = cast["embeds"]
            if not embeds_data:
                continue

            # Handle both JSON and string formats
            if isinstance(embeds_data, str):
                # If it's a quoted string (from JSONB storage), unquote it first
                if embeds_data.startswith('"') and embeds_data.endswith('"'):
                    # Remove outer quotes and unescape
                    embeds_data = (
                        embeds_data[1:-1].replace('\\"', '"').replace("\\\\", "\\")
                    )
                embeds = Embeds.model_validate(embeds_data)
            else:
                # Already parsed JSON
                embeds = Embeds.model_validate(embeds_data)

            result.embeds_extracted += len(embeds)

            # Convert each embed to database row
            for embed_index, embed in enumerate(embeds):
                row_data = _embed_to_row(
                    cast["hash"],
                    cast["fid"],
                    embed_index,
                    embed,
                    embeds_data,  # Original raw data
                )
                embed_rows.append(row_data)

        except Exception as e:
            logger.warning(f"Error parsing embeds for cast {cast['hash'].hex()}: {e}")
            result.errors += 1
            result.error_details.append(
                f"Parse error for cast {cast['hash'].hex()}: {str(e)}"
            )
            continue

    # Batch insert to target database
    if embed_rows:
        try:
            async with target_conn.transaction():
                # Delete existing embeds for these casts (for upsert behavior)
                cast_hashes = [row["cast_hash"] for row in embed_rows]
                unique_hashes = list(set(cast_hashes))

                await target_conn.execute(
                    f"""
                DELETE FROM {target_schema}.k3l_cast_embeds 
                WHERE cast_hash = ANY($1)
                """,
                    unique_hashes,
                )

                # Prepare data for batch insert
                insert_data = [
                    (
                        row["cast_hash"],
                        row["cast_fid"],
                        row["embed_index"],
                        row["embed_type"],
                        row["url"],
                        row["quoted_cast_hash"],
                        row["quoted_cast_fid"],
                        row["raw_embed_data"],
                    )
                    for row in embed_rows
                ]

                # Batch insert new embeds
                await target_conn.executemany(
                    f"""
                INSERT INTO {target_schema}.k3l_cast_embeds (
                    cast_hash, cast_fid, embed_index, embed_type,
                    url, quoted_cast_hash, quoted_cast_fid, raw_embed_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                    insert_data,
                )

                result.embeds_inserted = len(embed_rows)

        except Exception as e:
            logger.error(f"Error inserting batch: {e}")
            result.errors += 1
            result.error_details.append(f"Insert error: {str(e)}")

    return result


def _embed_to_row(
    cast_hash: bytes, cast_fid: int, embed_index: int, embed, raw_embed_data: Any
) -> Dict[str, Any]:
    """Convert an Embed object to database row data."""

    # Convert raw_embed_data to JSON string if needed
    if isinstance(raw_embed_data, str):
        raw_data_json = raw_embed_data
    else:
        raw_data_json = json.dumps(raw_embed_data)

    if embed.url:
        return {
            "cast_hash": cast_hash,
            "cast_fid": cast_fid,
            "embed_index": embed_index,
            "embed_type": "url",
            "url": embed.url,
            "quoted_cast_hash": None,
            "quoted_cast_fid": None,
            "raw_embed_data": raw_data_json,
        }
    elif embed.cast_id:
        return {
            "cast_hash": cast_hash,
            "cast_fid": cast_fid,
            "embed_index": embed_index,
            "embed_type": "cast_id",
            "url": None,
            "quoted_cast_hash": embed.cast_id.hash,
            "quoted_cast_fid": embed.cast_id.fid,
            "raw_embed_data": raw_data_json,
        }
    else:
        raise ValueError("Embed must have either url or cast_id")


async def _sync_embeds_with_connection_strings(
    source_connection_string: str,
    target_connection_string: str,
    min_updated_at: datetime,
    batch_size: int = 1000,
    source_schema: str = "neynarv2",
    target_schema: str = "public",
) -> EmbedSyncResult:
    """Helper function that manages connections and calls sync_embeds_async."""
    source_conn = await asyncpg.connect(source_connection_string)
    target_conn = await asyncpg.connect(target_connection_string)

    try:
        return await sync_embeds_async(
            source_conn,
            target_conn,
            min_updated_at,
            batch_size,
            source_schema,
            target_schema,
        )
    finally:
        await source_conn.close()
        await target_conn.close()


def sync_embeds(
    source_connection_string: str,
    target_connection_string: str,
    min_updated_at: datetime,
    batch_size: int = 1000,
    source_schema: str = "neynarv2",
    target_schema: str = "public",
) -> EmbedSyncResult:
    """Synchronous wrapper for async sync_embeds_async function.

    Args:
        source_connection_string: Connection string for source database
        target_connection_string: Connection string for target database
        min_updated_at: Minimum updated_at timestamp to process
        batch_size: Number of casts to process in each batch
        source_schema: Schema containing source casts table (default: "neynarv2")
        target_schema: Schema containing target embeds table (default: "public")

    Returns:
        EmbedSyncResult with processing statistics
    """
    try:
        # Try to get current event loop
        asyncio.get_running_loop()
        # If we're already in an event loop, we can't use asyncio.run()
        raise RuntimeError(
            "sync_embeds() cannot be called from within an async context. Use sync_embeds_async() instead."
        )
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(
            _sync_embeds_with_connection_strings(
                source_connection_string,
                target_connection_string,
                min_updated_at,
                batch_size,
                source_schema,
                target_schema,
            )
        )
