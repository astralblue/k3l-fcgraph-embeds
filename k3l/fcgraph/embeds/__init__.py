"""k3l-fcgraph-embeds: Normalize Farcaster cast embeds into canonical forms.

A Python library for parsing, normalizing, and synchronizing Farcaster cast embed data.
Handles both well-formed and malformed embed data commonly found in Farcaster databases.

This library provides:

1. **Robust Parsing**: Handle malformed JSON strings, Node.js Buffer formats, and various
   hash encodings commonly found in real-world Farcaster data.

2. **Database Migrations**: Built-in Alembic migrations with customizable schemas and
   version tables for multi-tenant deployments.

3. **High-Performance Sync**: Async data pipeline using asyncpg for efficient
   synchronization from source databases to normalized tables.

4. **Flexible API**: Both connection-object and connection-string interfaces to
   accommodate different usage patterns.

Quick Start:
    >>> from k3l.fcgraph.embeds import migrate_up, sync_embeds_async
    >>> from k3l.fcgraph.embeds.types import Embeds
    >>>
    >>> # Set up database
    >>> migrate_up("postgresql://localhost/db")
    >>>
    >>> # Parse embeds
    >>> embeds = Embeds.model_validate("[{'url': 'https://example.com'}]")
    >>> print(f"Parsed {len(embeds)} embeds")
    >>>
    >>> # Sync data (in async context)
    >>> result = await sync_embeds_async(source_conn, target_conn, min_timestamp)
    >>> print(f"Processed {result.casts_processed} casts")

For detailed usage examples, see the README.md file.
"""

__version__ = "0.1.0"

from .migration_manager import MigrationManager, create_migration_manager
from .sync import EmbedSyncResult, sync_embeds, sync_embeds_async


# Public API for migration management
def migrate_up(
    connection_string: str,
    schema: str = "public",
    version_table: str = "k3l_embeds_alembic",
    revision: str = "head",
) -> None:
    """Upgrade database to specified revision.

    Args:
        connection_string: Database connection string
        schema: Database schema to use (default: "public")
        version_table: Table name for migration versions (default: "k3l_embeds_alembic")
        revision: Target revision (default: "head" for latest)
    """
    manager = create_migration_manager(connection_string, schema, version_table)
    manager.upgrade(revision)


def migrate_down(
    connection_string: str,
    revision: str,
    schema: str = "public",
    version_table: str = "k3l_embeds_alembic",
) -> None:
    """Downgrade database to specified revision.

    Args:
        connection_string: Database connection string
        revision: Target revision
        schema: Database schema to use (default: "public")
        version_table: Table name for migration versions (default: "k3l_embeds_alembic")
    """
    manager = create_migration_manager(connection_string, schema, version_table)
    manager.downgrade(revision)


def get_migration_status(
    connection_string: str,
    schema: str = "public",
    version_table: str = "k3l_embeds_alembic",
) -> dict:
    """Get migration status information.

    Args:
        connection_string: Database connection string
        schema: Database schema to use (default: "public")
        version_table: Table name for migration versions (default: "k3l_embeds_alembic")

    Returns:
        Dictionary with migration status information
    """
    manager = create_migration_manager(connection_string, schema, version_table)

    return {
        "current_revision": manager.current_revision(),
        "pending_migrations": manager.pending_migrations(),
        "migration_history": manager.migration_history(),
    }


__all__ = [
    "MigrationManager",
    "create_migration_manager",
    "migrate_up",
    "migrate_down",
    "get_migration_status",
    "sync_embeds",
    "sync_embeds_async",
    "EmbedSyncResult",
]
