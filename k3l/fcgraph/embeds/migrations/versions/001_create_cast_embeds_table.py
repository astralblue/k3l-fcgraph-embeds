"""Create k3l_cast_embeds table

Revision ID: 001
Revises:
Create Date: 2025-06-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create k3l_cast_embeds table for storing normalized cast embed data."""
    op.create_table(
        "k3l_cast_embeds",
        sa.Column(
            "id",
            sa.BigInteger(),
            nullable=False,
            comment="Auto-incrementing primary key",
        ),
        sa.Column(
            "cast_hash",
            sa.LargeBinary(),
            nullable=False,
            comment="Hash of the cast containing these embeds",
        ),
        sa.Column(
            "cast_fid",
            sa.BigInteger(),
            nullable=False,
            comment="FID of the cast author",
        ),
        sa.Column(
            "embed_index",
            sa.SmallInteger(),
            nullable=False,
            comment="Index of this embed within the cast (0-based)",
        ),
        sa.Column(
            "embed_type",
            sa.String(32),
            nullable=False,
            comment="Type of embed: url, cast_id",
        ),
        sa.Column("url", sa.Text(), nullable=True, comment="URL for url-type embeds"),
        sa.Column(
            "quoted_cast_hash",
            sa.LargeBinary(),
            nullable=True,
            comment="Hash of quoted cast for cast_id-type embeds",
        ),
        sa.Column(
            "quoted_cast_fid",
            sa.BigInteger(),
            nullable=True,
            comment="FID of quoted cast author for cast_id-type embeds",
        ),
        sa.Column(
            "raw_embed_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Original raw embed data from source",
        ),
        sa.Column(
            "processed_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="When this embed was processed",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="When this record was created",
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="When this record was last updated",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cast_hash", "embed_index", name="uq_cast_embed_index"),
        comment="Normalized cast embed data extracted from Farcaster casts",
    )

    # Create indexes for efficient querying
    op.create_index("ix_k3l_cast_embeds_cast_hash", "k3l_cast_embeds", ["cast_hash"])
    op.create_index("ix_k3l_cast_embeds_cast_fid", "k3l_cast_embeds", ["cast_fid"])
    op.create_index("ix_k3l_cast_embeds_embed_type", "k3l_cast_embeds", ["embed_type"])
    op.create_index("ix_k3l_cast_embeds_url", "k3l_cast_embeds", ["url"])
    op.create_index(
        "ix_k3l_cast_embeds_quoted_cast",
        "k3l_cast_embeds",
        ["quoted_cast_hash", "quoted_cast_fid"],
    )
    op.create_index(
        "ix_k3l_cast_embeds_processed_at", "k3l_cast_embeds", ["processed_at"]
    )

    # Create a partial index for URL embeds only
    op.create_index(
        "ix_k3l_cast_embeds_url_embeds_only",
        "k3l_cast_embeds",
        ["url"],
        postgresql_where=sa.text("embed_type = 'url' AND url IS NOT NULL"),
    )

    # Create a partial index for cast quote embeds only
    op.create_index(
        "ix_k3l_cast_embeds_quote_embeds_only",
        "k3l_cast_embeds",
        ["quoted_cast_hash", "quoted_cast_fid"],
        postgresql_where=sa.text(
            "embed_type = 'cast_id' AND quoted_cast_hash IS NOT NULL"
        ),
    )


def downgrade() -> None:
    """Drop k3l_cast_embeds table."""
    op.drop_table("k3l_cast_embeds")
