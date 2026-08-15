"""baseline

Revision ID: 98d0662cb87f
Revises: 
Create Date: 2026-08-15 22:45:04.562414

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '98d0662cb87f'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
