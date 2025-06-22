"""Migration management for k3l.fcgraph.embeds using programmatic Alembic."""

import importlib.resources
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class MigrationManager:
    """Manages database migrations for k3l.fcgraph.embeds."""

    def __init__(
        self,
        connection_string: str,
        schema: str = "public",
        version_table: str = "k3l_embeds_alembic",
    ):
        """Initialize migration manager.

        Args:
            connection_string: Database connection string
            schema: Database schema to use (default: "public")
            version_table: Table name for migration versions (default: "k3l_embeds_alembic")
        """
        self.connection_string = connection_string
        self.schema = schema
        self.version_table = version_table
        self.engine = create_engine(connection_string)

    def _get_alembic_config(self) -> Config:
        """Create Alembic configuration programmatically."""
        config = Config()

        # Get migrations directory from package resources
        migrations_path = importlib.resources.files("k3l.fcgraph.embeds.migrations")
        script_location = str(migrations_path)

        # Configure Alembic
        config.set_main_option("script_location", script_location)
        config.set_main_option("sqlalchemy.url", self.connection_string)
        config.set_main_option("version_table", self.version_table)
        config.set_main_option("version_table_schema", self.schema)

        # Set target metadata for autogenerate support
        # This will be populated when we add SQLAlchemy models
        config.attributes["target_metadata"] = None

        return config

    def _ensure_schema_exists(self):
        """Ensure the target schema exists."""
        if self.schema != "public":
            with self.engine.connect() as conn:
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema}"))
                conn.commit()

    def upgrade(self, revision: str = "head") -> None:
        """Upgrade database to specified revision.

        Args:
            revision: Target revision (default: "head" for latest)
        """
        self._ensure_schema_exists()
        config = self._get_alembic_config()
        command.upgrade(config, revision)

    def downgrade(self, revision: str) -> None:
        """Downgrade database to specified revision.

        Args:
            revision: Target revision
        """
        config = self._get_alembic_config()
        command.downgrade(config, revision)

    def current_revision(self) -> Optional[str]:
        """Get current database revision.

        Returns:
            Current revision or None if no migrations applied
        """
        with self.engine.connect() as conn:
            context = MigrationContext.configure(
                conn,
                opts={
                    "version_table": self.version_table,
                    "version_table_schema": (
                        self.schema if self.schema != "public" else None
                    ),
                },
            )
            return context.get_current_revision()

    def pending_migrations(self) -> list[str]:
        """Get list of pending migration revisions.

        Returns:
            List of pending revision IDs
        """
        config = self._get_alembic_config()
        script = ScriptDirectory.from_config(config)

        current = self.current_revision()
        heads = script.get_heads()

        if not current:
            # No migrations applied yet
            return [rev.revision for rev in script.walk_revisions()]

        pending = []
        for head in heads:
            for rev in script.iterate_revisions(head, current):
                if rev.revision != current:
                    pending.append(rev.revision)

        return pending

    def migration_history(self) -> list[dict]:
        """Get migration history.

        Returns:
            List of migration info dictionaries
        """
        config = self._get_alembic_config()
        script = ScriptDirectory.from_config(config)

        history = []
        for rev in script.walk_revisions():
            history.append(
                {
                    "revision": rev.revision,
                    "down_revision": rev.down_revision,
                    "description": rev.doc,
                    "branch_labels": rev.branch_labels,
                }
            )

        return history


def create_migration_manager(
    connection_string: str,
    schema: str = "public",
    version_table: str = "k3l_embeds_alembic",
) -> MigrationManager:
    """Factory function to create a MigrationManager.

    Args:
        connection_string: Database connection string
        schema: Database schema to use (default: "public")
        version_table: Table name for migration versions (default: "k3l_embeds_alembic")

    Returns:
        Configured MigrationManager instance
    """
    return MigrationManager(connection_string, schema, version_table)
