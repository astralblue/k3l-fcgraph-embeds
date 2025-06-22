# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a production-ready Python library for normalizing Farcaster cast embeds into canonical forms and synchronizing them to clean database tables. The package is structured as a namespace package under `k3l.fcgraph.embeds`.

### Current Status (Latest Commit: cde07e9)

The library now includes comprehensive database management and sync capabilities:

1. **Embed Parsing**: Robust parsing of both well-formed JSON and malformed string embeds from real-world Farcaster databases
2. **Database Migrations**: Programmatic Alembic integration with custom version tables and multi-tenant support  
3. **Async Data Sync**: High-performance async pipeline using asyncpg for incremental data synchronization
4. **Production Ready**: Connection pooling support, comprehensive error handling, and detailed documentation

### Farcaster Embeds Context

Farcaster is a decentralized social network where posts are called "casts". Each cast can contain an `embeds` field - an array of embed elements that can be:

1. **URL embeds**: Web URLs or Ethereum asset URIs (following CAIP-19 format)
   - Web URLs: `https://example.com`
   - NFT assets: `chain://eip155:1/erc721:0xa723.../11`
   - Collections: `chain://eip155:1/erc721:0xa723...`

2. **Quote casts**: References to other casts (like sharing/retweeting with commentary)
   - Uses CastId references for efficient storage
   - Implemented via FIP-2 specification

### Key Data Types

**CastId** (composite type):
- `fid` (uint64): Farcaster ID of the user who created the cast
- `hash` (bytes): Unique hash of the specific cast

**Embed** structure:
```
Embed {
  url: string (optional)
  cast_id: CastId (optional)
}
```

This library normalizes these various embed formats into canonical forms for consistent processing, with special handling for malformed data commonly found in real-world databases.

### Real-World Data Challenges

The library specifically addresses data quality issues found in production Farcaster databases:

1. **Malformed JSON strings**: Embeds stored as strings with single quotes instead of double quotes
   - Example: `"[{'url': 'https://example.com'}]"` (stored as JSON string)
   - Handled via `ast.literal_eval()` for safe parsing

2. **Node.js Buffer format**: Cast hashes stored in Node.js Buffer format  
   - Example: `{"data": [1,2,3,...,20], "type": "Buffer"}`
   - Converted to proper 20-byte hash values

3. **Mixed embed formats**: Arrays containing both URL and cast quote embeds
   - Normalized into separate database rows with proper indexing

### Database Schema

The library creates a normalized `k3l_cast_embeds` table:
- **Denormalized structure**: Separate rows for each embed with proper indexing  
- **Efficient querying**: Indexes on cast_hash, embed_type, URLs, and quoted casts
- **Data integrity**: Unique constraints and proper foreign key relationships
- **Audit trail**: Preserves original raw embed data for debugging

## Development Commands

### Environment Setup
Following project convention, use Python 3.9 (minimum supported version) for development:
```bash
# Create venv (using project convention)
python3.9 -m venv --prompt="k3l-fcgraph-embeds/py3.9" .venvs/py3.9

# Install development dependencies
.venvs/py3.9/bin/pip install -e ".[dev]"
```

### Code Quality
```bash
# Format code
.venvs/py3.9/bin/black .
.venvs/py3.9/bin/isort .

# Check formatting (useful for CI)
.venvs/py3.9/bin/black --check .
.venvs/py3.9/bin/isort --check-only .
```

### Testing
```bash
# Run tests  
.venvs/py3.9/bin/pytest

# Run tests with coverage
.venvs/py3.9/bin/pytest --cov=k3l.fcgraph.embeds

# Test migrations against local PostgreSQL
.venvs/py3.9/bin/python test_migrations.py

# Test sync functionality with sample data
.venvs/py3.9/bin/python test_sync.py

# Run examples
.venvs/py3.9/bin/python examples/basic_usage.py
```

### Building
```bash
# Build package
.venvs/py3.9/bin/python -m build
```

## Architecture

### Package Structure
- **Namespace packaging**: `k3l.fcgraph.embeds` as the main module
- **types.py**: Pydantic models for embed parsing and validation
- **migration_manager.py**: Programmatic Alembic integration
- **migrations/**: Database schema definitions and migration files  
- **sync.py**: Async data synchronization pipeline
- **examples/**: Working examples and usage patterns

### Key Dependencies
- **pydantic**: Type-safe parsing and validation of embed data
- **alembic + sqlalchemy**: Database migrations and schema management
- **asyncpg**: High-performance async PostgreSQL driver for sync operations
- **psycopg2-binary**: Synchronous PostgreSQL driver for migrations

### Design Patterns
- **Connection-based APIs**: Primary async functions take connection objects for production use
- **Flexible interfaces**: Both connection-object and connection-string APIs available
- **Comprehensive error handling**: Detailed error reporting with statistics
- **Incremental processing**: Timestamp-based watermarks for efficient data sync
- **Build System**: Uses `flit_core` as the build backend with dynamic versioning
- **Code Style**: Black formatter with isort (using Black profile) for import sorting
- **Documentation**: Napoleon/Google-style docstrings throughout
- **Python Support**: Python 3.9+ with explicit support through 3.13

## Configuration

- **Tool Configuration**: All tool configurations are in `pyproject.toml`
- **Import Sorting**: isort configured with Black profile and `skip_gitignore = true`
- **Version Management**: Dynamic versioning handled by flit from the `__version__` in `__init__.py`
- **Migration Tables**: Configurable version table names (default: `k3l_embeds_alembic`)
- **Schema Support**: Multi-tenant deployments with custom schema names
- **Database Connection**: Uses standard PostgreSQL connection strings

## Usage Patterns

### Database Setup
```python
from k3l.fcgraph.embeds import migrate_up

# Run migrations
migrate_up("postgresql://user:pass@host/db")
```

### Embed Parsing
```python
from k3l.fcgraph.embeds.types import Embeds

# Parse malformed embed strings
embeds = Embeds.model_validate("[{'url': 'https://example.com'}]")
```

### Data Synchronization  
```python
import asyncpg
from k3l.fcgraph.embeds import sync_embeds_async

# Async sync with connection objects (production)
source_conn = await asyncpg.connect("postgresql://source")
target_conn = await asyncpg.connect("postgresql://target")

result = await sync_embeds_async(
    source_conn, target_conn, min_updated_at=timestamp
)
```

### Known Issues

1. **JSONB Insertion**: Malformed JSON strings need proper escaping when inserting into JSONB columns (minor issue in sync pipeline)
2. **Local Testing**: Tests assume local PostgreSQL with `postgresql:///` connection string