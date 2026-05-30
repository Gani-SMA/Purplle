"""Initial tables creation

Revision ID: a1b2c3d4e5f6
Revises: None
Create Date: 2026-05-30T09:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def table_exists(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return name in insp.get_table_names()

def upgrade() -> None:
    # 1. Create stores table
    if not table_exists('stores'):
        op.create_table(
            'stores',
            sa.Column('store_id', sa.String(length=50), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('city', sa.String(length=100), nullable=False),
            sa.Column('layout', sa.JSON(), nullable=False),
            sa.Column('open_hours', sa.JSON(), nullable=False),
            sa.Column('cameras', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.TIMESTAMPTZ(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('store_id')
        )

    # 2. Create events table
    if not table_exists('events'):
        op.create_table(
            'events',
            sa.Column('event_id', sa.UUID(), nullable=False),
            sa.Column('store_id', sa.String(length=50), nullable=False),
            sa.Column('camera_id', sa.String(length=50), nullable=False),
            sa.Column('visitor_id', sa.String(length=50), nullable=False),
            sa.Column('event_type', sa.String(length=30), nullable=False),
            sa.Column('timestamp', sa.TIMESTAMPTZ(), nullable=False),
            sa.Column('zone_id', sa.String(length=50), nullable=True),
            sa.Column('dwell_ms', sa.Integer(), server_default='0', nullable=False),
            sa.Column('is_staff', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('confidence', sa.Float(), nullable=False),
            sa.Column('queue_depth', sa.Integer(), nullable=True),
            sa.Column('sku_zone', sa.String(length=100), nullable=True),
            sa.Column('session_seq', sa.Integer(), nullable=False),
            sa.Column('raw_metadata', sa.JSON(), nullable=True),
            sa.Column('ingested_at', sa.TIMESTAMPTZ(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['store_id'], ['stores.store_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('event_id')
        )

    # 3. Create sessions table
    if not table_exists('sessions'):
        op.create_table(
            'sessions',
            sa.Column('session_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('store_id', sa.String(length=50), nullable=False),
            sa.Column('visitor_id', sa.String(length=50), nullable=False),
            sa.Column('entry_ts', sa.TIMESTAMPTZ(), nullable=False),
            sa.Column('exit_ts', sa.TIMESTAMPTZ(), nullable=True),
            sa.Column('is_converted', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('is_reentry', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('total_dwell_ms', sa.Integer(), nullable=True),
            sa.Column('zones_visited', sa.ARRAY(sa.Text()), nullable=True),
            sa.Column('reached_billing', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('abandoned_queue', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('created_at', sa.TIMESTAMPTZ(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['store_id'], ['stores.store_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('session_id')
        )

    # 4. Create pos_transactions table
    if not table_exists('pos_transactions'):
        op.create_table(
            'pos_transactions',
            sa.Column('transaction_id', sa.String(length=50), nullable=False),
            sa.Column('store_id', sa.String(length=50), nullable=False),
            sa.Column('timestamp', sa.TIMESTAMPTZ(), nullable=False),
            sa.Column('basket_value', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('imported_at', sa.TIMESTAMPTZ(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['store_id'], ['stores.store_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('transaction_id')
        )

    # 5. Create anomalies_log table
    if not table_exists('anomalies_log'):
        op.create_table(
            'anomalies_log',
            sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('store_id', sa.String(length=50), nullable=False),
            sa.Column('anomaly_type', sa.String(length=50), nullable=False),
            sa.Column('severity', sa.String(length=10), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('suggested_action', sa.Text(), nullable=False),
            sa.Column('detected_at', sa.TIMESTAMPTZ(), server_default=sa.text('now()'), nullable=False),
            sa.Column('resolved_at', sa.TIMESTAMPTZ(), nullable=True),
            sa.ForeignKeyConstraint(['store_id'], ['stores.store_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

def downgrade() -> None:
    op.drop_table('anomalies_log')
    op.drop_table('pos_transactions')
    op.drop_table('sessions')
    op.drop_table('events')
    op.drop_table('stores')
