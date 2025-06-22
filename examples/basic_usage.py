#!/usr/bin/env python3
"""Basic usage examples for k3l-fcgraph-embeds."""

import asyncio
import asyncpg
from datetime import datetime

from k3l.fcgraph.embeds import migrate_up, sync_embeds_async
from k3l.fcgraph.embeds.types import Embeds


def example_parsing():
    """Demonstrate embed parsing capabilities."""
    print("=== Embed Parsing Examples ===\n")

    # Well-formed JSON
    print("1. Well-formed JSON:")
    embeds = Embeds.model_validate('[{"url": "https://example.com/image.jpg"}]')
    print(f"   Parsed {len(embeds)} embeds")
    print(f"   First embed URL: {embeds[0].url}\n")

    # Malformed string (single quotes)
    print("2. Malformed JSON string:")
    embeds = Embeds.model_validate("[{'url': 'https://malformed.com/image.jpg'}]")
    print(f"   Parsed {len(embeds)} embeds")
    print(f"   First embed URL: {embeds[0].url}\n")

    # Cast quote with Node.js Buffer format
    print("3. Cast quote with Buffer format:")
    buffer_data = """[{"castId": {"fid": 123, "hash": {"data": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20], "type": "Buffer"}}}]"""
    embeds = Embeds.model_validate(buffer_data)
    print(f"   Parsed {len(embeds)} embeds")
    print(f"   Quote cast FID: {embeds[0].cast_id.fid}")
    print(f"   Quote cast hash: {embeds[0].cast_id.hash.hex()}\n")

    # Mixed embeds
    print("4. Mixed embeds:")
    mixed_data = """[{"url": "https://example.com"}, {"castId": {"fid": 456, "hash": {"data": [21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40], "type": "Buffer"}}}]"""
    embeds = Embeds.model_validate(mixed_data)
    print(f"   Parsed {len(embeds)} embeds")
    print(f"   First embed type: {'URL' if embeds[0].url else 'Cast quote'}")
    print(f"   Second embed type: {'URL' if embeds[1].url else 'Cast quote'}")


def example_migrations():
    """Demonstrate migration management."""
    print("=== Migration Management Examples ===\n")

    connection_string = "postgresql:///"

    print("1. Running database migrations:")
    try:
        migrate_up(connection_string)
        print("   ✓ Migrations completed successfully\n")
    except Exception as e:
        print(f"   ✗ Migration failed: {e}\n")


async def example_sync():
    """Demonstrate async data synchronization."""
    print("=== Data Synchronization Examples ===\n")

    # Note: This example assumes you have source data available
    # In a real scenario, you'd connect to your Neynar/Farcaster database

    print("1. Connecting to databases:")
    try:
        # In production, these would be different databases
        source_conn = await asyncpg.connect("postgresql:///")
        target_conn = await asyncpg.connect("postgresql:///")

        print("   ✓ Connected to source and target databases")

        print("\n2. Running incremental sync:")

        # Sync data from the last hour
        min_timestamp = datetime.now().replace(minute=0, second=0, microsecond=0)

        # This would typically sync from neynarv2.casts to public.k3l_cast_embeds
        # For this example, we'll just show the API call
        print(f"   Would sync data updated since: {min_timestamp}")
        print("   (Skipping actual sync in example)")

        # Uncomment this for actual sync:
        # result = await sync_embeds_async(
        #     source_conn=source_conn,
        #     target_conn=target_conn,
        #     min_updated_at=min_timestamp,
        #     source_schema="neynarv2",
        #     target_schema="public"
        # )
        # print(f"   ✓ Processed {result.casts_processed} casts")
        # print(f"   ✓ Extracted {result.embeds_extracted} embeds")
        # print(f"   ✓ Inserted {result.embeds_inserted} normalized embeds")

        await source_conn.close()
        await target_conn.close()
        print("   ✓ Connections closed\n")

    except Exception as e:
        print(f"   ✗ Sync example failed: {e}\n")


async def main():
    """Run all examples."""
    print("k3l-fcgraph-embeds Usage Examples")
    print("=================================\n")

    example_parsing()
    example_migrations()
    await example_sync()

    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
