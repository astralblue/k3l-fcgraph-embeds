# k3l-fcgraph-embeds

A Python library for normalizing Farcaster cast embeds into canonical forms and synchronizing them to clean database tables.

## Features

- **Embed Parsing**: Handles both well-formed JSON and malformed string embeds from Farcaster casts
- **Node.js Buffer Support**: Parses cast hashes in Node.js Buffer format (`{"data": [bytes], "type": "Buffer"}`)
- **Database Migrations**: Built-in Alembic migrations with custom version tables
- **Async Synchronization**: High-performance async data pipeline using asyncpg
- **Flexible API**: Both connection-object and connection-string interfaces

## Installation

```bash
pip install k3l-fcgraph-embeds
```

## Quick Start

### 1. Set up the database

```python
from k3l.fcgraph.embeds import migrate_up

# Run migrations to create the k3l_cast_embeds table
migrate_up("postgresql://user:pass@localhost/db")
```

### 2. Parse embeds from various formats

```python
from k3l.fcgraph.embeds.types import Embeds

# Well-formed JSON
embeds = Embeds.model_validate('[{"url": "https://example.com"}]')

# Malformed string (single quotes)
embeds = Embeds.model_validate("[{'url': 'https://example.com'}]")

# Node.js Buffer format for cast quotes
embeds = Embeds.model_validate("""
[{"castId": {"fid": 123, "hash": {"data": [1,2,3,...], "type": "Buffer"}}}]
""")

print(f"Parsed {len(embeds)} embeds")
```

### 3. Sync data from Farcaster database

```python
import asyncio
import asyncpg
from datetime import datetime
from k3l.fcgraph.embeds import sync_embeds_async

async def sync_recent_embeds():
    # Connect to source (Neynar/Farcaster data) and target databases
    source_conn = await asyncpg.connect("postgresql://source_db")
    target_conn = await asyncpg.connect("postgresql://target_db")
    
    try:
        # Sync embeds updated in the last hour
        min_timestamp = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        result = await sync_embeds_async(
            source_conn=source_conn,
            target_conn=target_conn,
            min_updated_at=min_timestamp,
            source_schema="neynarv2",  # Schema containing casts table
            target_schema="public"     # Schema for k3l_cast_embeds table
        )
        
        print(f"Processed {result.casts_processed} casts")
        print(f"Extracted {result.embeds_extracted} embeds") 
        print(f"Inserted {result.embeds_inserted} normalized embeds")
        
    finally:
        await source_conn.close()
        await target_conn.close()

# Run the sync
asyncio.run(sync_recent_embeds())
```

## API Reference

### Migration Management

#### migrate_up(connection_string, schema="public", version_table="k3l_embeds_alembic", revision="head")

Upgrade database to the latest (or specified) migration revision.

**Parameters:**
- `connection_string` (str): PostgreSQL connection string
- `schema` (str, optional): Target schema. Defaults to "public"
- `version_table` (str, optional): Custom migration version table. Defaults to "k3l_embeds_alembic"
- `revision` (str, optional): Target revision. Defaults to "head"

#### migrate_down(connection_string, revision, schema="public", version_table="k3l_embeds_alembic")

Downgrade database to a specified revision.

#### get_migration_status(connection_string, schema="public", version_table="k3l_embeds_alembic")

Get current migration status including current revision, pending migrations, and history.

**Returns:** Dict with migration status information.

### Data Synchronization

#### sync_embeds_async(source_conn, target_conn, min_updated_at, batch_size=1000, source_schema="neynarv2", target_schema="public")

Asynchronously synchronize embeds from source casts table to normalized embeds table.

**Parameters:**
- `source_conn` (asyncpg.Connection): Connection to source database
- `target_conn` (asyncpg.Connection): Connection to target database  
- `min_updated_at` (datetime): Minimum updated_at timestamp to process
- `batch_size` (int, optional): Batch size for processing. Defaults to 1000
- `source_schema` (str, optional): Source schema name. Defaults to "neynarv2"
- `target_schema` (str, optional): Target schema name. Defaults to "public"

**Returns:** `EmbedSyncResult` with processing statistics.

#### sync_embeds(source_connection_string, target_connection_string, min_updated_at, ...)

Synchronous wrapper for `sync_embeds_async` that manages connections automatically.

### Data Types

#### Embeds

A Pydantic model representing a list of embeds with flexible input parsing.

**Supported input formats:**
- List of Embed objects: `[Embed(...), Embed(...)]`
- List of dictionaries: `[{"url": "..."}, {"castId": {...}}]`  
- String representation: `"[{'url': '...'}]"`
- Empty values: `None`, `""`, `[]`

#### Embed

Individual embed object containing either a URL or cast reference.

**Fields:**
- `url` (str, optional): URL string for web links or Ethereum assets
- `cast_id` (CastId, optional): Reference to another cast for quote casts

#### CastId

Farcaster Cast ID consisting of user FID and cast hash.

**Fields:**
- `fid` (int): Farcaster ID of the user who created the cast
- `hash` (bytes): Unique hash of the cast (20 bytes)

## Database Schema

The library creates a `k3l_cast_embeds` table with the following structure:

```sql
CREATE TABLE k3l_cast_embeds (
    id BIGSERIAL PRIMARY KEY,
    cast_hash BYTEA NOT NULL,           -- Hash of the cast containing embeds
    cast_fid BIGINT NOT NULL,           -- FID of the cast author  
    embed_index SMALLINT NOT NULL,      -- Index within the cast (0-based)
    embed_type VARCHAR(32) NOT NULL,    -- 'url' or 'cast_id'
    url TEXT,                           -- URL for url-type embeds
    quoted_cast_hash BYTEA,             -- Hash for cast_id-type embeds
    quoted_cast_fid BIGINT,             -- FID for cast_id-type embeds
    raw_embed_data JSONB NOT NULL,      -- Original raw embed data
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(cast_hash, embed_index)
);
```

## Configuration

### Custom Migration Tables

You can use custom migration version tables to avoid conflicts when multiple libraries use the same database:

```python
# Use a custom version table
migrate_up(
    "postgresql://localhost/db",
    version_table="my_app_embeds_migrations"
)
```

### Custom Schemas

Deploy to non-public schemas:

```python
# Deploy to a specific schema
migrate_up(
    "postgresql://localhost/db", 
    schema="analytics"
)

# Sync to the same schema
result = await sync_embeds_async(
    source_conn, target_conn, min_timestamp,
    target_schema="analytics"
)
```

## Performance Considerations

### Connection Pooling

For production use, leverage asyncpg connection pools:

```python
import asyncpg

async def setup_connection_pool():
    return await asyncpg.create_pool(
        "postgresql://user:pass@host/db",
        min_size=5,
        max_size=20
    )

async def sync_with_pool(pool):
    async with pool.acquire() as source_conn:
        async with pool.acquire() as target_conn:
            result = await sync_embeds_async(
                source_conn, target_conn, min_timestamp
            )
    return result
```

### Batch Processing

Adjust batch size based on your system resources:

```python
# Smaller batches for memory-constrained environments
result = await sync_embeds_async(
    source_conn, target_conn, min_timestamp,
    batch_size=500
)

# Larger batches for high-performance systems
result = await sync_embeds_async(
    source_conn, target_conn, min_timestamp, 
    batch_size=5000
)
```

## Error Handling

The sync process provides detailed error reporting:

```python
result = await sync_embeds_async(source_conn, target_conn, min_timestamp)

if result.errors > 0:
    print(f"Encountered {result.errors} errors:")
    for error in result.error_details:
        print(f"  - {error}")
        
# Check processing statistics
print(f"Success rate: {result.embeds_inserted}/{result.embeds_extracted}")
```

## Contributing

1. Clone the repository
2. Set up development environment:
   ```bash
   python3.9 -m venv --prompt="k3l-fcgraph-embeds/py3.9" .venvs/py3.9
   .venvs/py3.9/bin/pip install -e ".[dev]"
   ```
3. Run tests:
   ```bash
   .venvs/py3.9/bin/pytest
   ```
4. Format code:
   ```bash
   .venvs/py3.9/bin/black .
   .venvs/py3.9/bin/isort .
   ```

## License

MIT License - see LICENSE file for details.