"""Add performance indexes

Revision ID: c3d4e5f6a1b2
Revises: a1b2c3d4e5f6
Create Date: 2026-05-30T09:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a1b2'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Event index: store_id + timestamp DESC
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_store_ts ON events(store_id, timestamp DESC)")
    
    # 2. Event index: visitor_id
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_visitor ON events(visitor_id)")
    
    # 3. Event index: event_type
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
    
    # 4. Event index: is_staff (filtered index for customers only)
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_staff ON events(is_staff) WHERE is_staff = false")
    
    # 5. Session index: visitor_id + store_id (re-entry lookup)
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_visitor ON sessions(visitor_id, store_id)")
    
    # 6. Session index: store_id + entry_ts DESC
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_store_ts ON sessions(store_id, entry_ts DESC)")
    
    # 7. POS correlation index: store_id + timestamp DESC
    op.execute("CREATE INDEX IF NOT EXISTS idx_pos_store_ts ON pos_transactions(store_id, timestamp DESC)")

def downgrade() -> None:
    op.drop_index('idx_events_store_ts', table_name='events')
    op.drop_index('idx_events_visitor', table_name='events')
    op.drop_index('idx_events_type', table_name='events')
    op.drop_index('idx_events_staff', table_name='events')
    op.drop_index('idx_sessions_visitor', table_name='sessions')
    op.drop_index('idx_sessions_store_ts', table_name='sessions')
    op.drop_index('idx_pos_store_ts', table_name='pos_transactions')
