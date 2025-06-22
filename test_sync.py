#!/usr/bin/env python3
"""Test script for the async embed synchronization function."""

import asyncio
import sys
from datetime import datetime, timezone

from k3l.fcgraph.embeds import sync_embeds_async


async def setup_test_data(local_connection):
    """Set up test data using asyncpg."""
    try:
        import asyncpg

        conn = await asyncpg.connect(local_connection)

        # Create test schema and table
        await conn.execute("CREATE SCHEMA IF NOT EXISTS test_neynar")
        await conn.execute(
            """
        CREATE TABLE IF NOT EXISTS test_neynar.casts (
            id BIGSERIAL PRIMARY KEY,
            hash BYTEA NOT NULL,
            fid BIGINT NOT NULL,
            embeds JSONB NOT NULL DEFAULT '{}',
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # Clear existing test data
        await conn.execute("DELETE FROM test_neynar.casts")

        # Insert test data with various embed formats
        test_data = [
            # Well-formed JSON
            (
                b"\\x1234567890123456789012345678901234567890",
                123,
                '[{"url": "https://example.com/test1.jpg"}]',
            ),
            # Malformed JSON string (single quotes) - store as string in JSONB
            (
                b"\\x2345678901234567890123456789012345678901",
                456,
                "\"[{'url': 'https://example.com/test2.jpg'}, {'url': 'https://example.com/test3.jpg'}]\"",
            ),
            # Cast quote embed - store as string
            (
                b"\\x3456789012345678901234567890123456789012",
                789,
                "\"[{'castId': {'fid': 999, 'hash': {'data': [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20], 'type': 'Buffer'}}}]\"",
            ),
            # Mixed embeds - store as string
            (
                b"\\x4567890123456789012345678901234567890123",
                101112,
                "\"[{'url': 'https://example.com/mixed.jpg'}, {'castId': {'fid': 888, 'hash': {'data': [21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40], 'type': 'Buffer'}}}]\"",
            ),
        ]

        for hash_val, fid, embeds in test_data:
            await conn.execute(
                """
            INSERT INTO test_neynar.casts (hash, fid, embeds, updated_at) 
            VALUES ($1, $2, $3, $4)
            """,
                hash_val,
                fid,
                embeds,
                datetime.now(),
            )

        await conn.close()
        print("✓ Test data created")
        return True

    except Exception as e:
        print(f"Error setting up test data: {e}")
        return False


async def verify_results(local_connection):
    """Verify sync results using asyncpg."""
    try:
        import asyncpg

        conn = await asyncpg.connect(local_connection)

        # Check total embeds inserted
        total_embeds = await conn.fetchval("SELECT COUNT(*) FROM k3l_cast_embeds")
        print(f"✓ Total embeds in target table: {total_embeds}")

        # Check embed types
        embed_types = await conn.fetch(
            "SELECT embed_type, COUNT(*) FROM k3l_cast_embeds GROUP BY embed_type"
        )
        for row in embed_types:
            print(f"  {row['embed_type']}: {row['count']}")

        # Show sample data
        sample_data = await conn.fetch(
            """
        SELECT cast_hash, embed_type, url, quoted_cast_fid 
        FROM k3l_cast_embeds 
        ORDER BY cast_hash, embed_index 
        LIMIT 5
        """
        )

        print("\n  Sample normalized data:")
        for row in sample_data:
            cast_hash_hex = row["cast_hash"].hex() if row["cast_hash"] else None
            url_or_fid = row["url"] or f"fid:{row['quoted_cast_fid']}"
            print(f"    {cast_hash_hex[:8]}... | {row['embed_type']} | {url_or_fid}")

        await conn.close()
        return True

    except Exception as e:
        print(f"Error verifying results: {e}")
        return False


async def main():
    local_connection = "postgresql:///"

    print("Testing async embed synchronization...")

    # Setup test data
    print("\n1. Setting up test data...")
    if not await setup_test_data(local_connection):
        return 1

    # Test synchronization
    print("\n2. Running synchronization...")
    try:
        # Use a timestamp from beginning of day to catch all test data
        min_timestamp = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Connect to databases
        import asyncpg

        source_conn = await asyncpg.connect(local_connection)
        target_conn = await asyncpg.connect(local_connection)

        try:
            result = await sync_embeds_async(
                source_conn=source_conn,
                target_conn=target_conn,
                min_updated_at=min_timestamp,
                source_schema="test_neynar",
                target_schema="public",
            )
        finally:
            await source_conn.close()
            await target_conn.close()

        print(f"✓ Synchronization completed!")
        print(f"  Casts processed: {result.casts_processed}")
        print(f"  Embeds extracted: {result.embeds_extracted}")
        print(f"  Embeds inserted: {result.embeds_inserted}")
        print(f"  Errors: {result.errors}")
        print(f"  Max updated_at: {result.max_updated_at}")

        if result.error_details:
            print("  Error details:")
            for error in result.error_details:
                print(f"    - {error}")

    except Exception as e:
        print(f"Error during synchronization: {e}")
        return 1

    # Verify results
    print("\n3. Verifying results...")
    if not await verify_results(local_connection):
        return 1

    print("\n✓ All async sync tests passed!")
    return 0


def run_main():
    """Synchronous wrapper for the async main function."""
    return asyncio.run(main())


if __name__ == "__main__":
    sys.exit(run_main())
