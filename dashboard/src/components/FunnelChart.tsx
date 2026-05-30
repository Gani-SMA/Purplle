import React, { useState } from 'react';
import { FunnelResponse } from '../api';
import { FrostedGlassCard } from './ui/interactive-frosted-glass-card';

interface FunnelChartProps { data: FunnelResponse | null; }

const STAGE_LABELS: Record<string, string> = {
  stage_1_entry:    'Entry',
  stage_2_browse:   'Browse',
  stage_3_checkout: 'Checkout',
  stage_4_purchase: 'Purchase',
};

const BAR_COLORS = ['#818cf8', '#34d399', '#fbbf24', '#f87171'];

export function FunnelChart({ data }: FunnelChartProps) {
  const [hoveredRow, setHoveredRow] = useState<number | null>(null);

  if (!data?.funnel?.length) {
    return (
      <FrostedGlassCard noTilt style={{
        padding: 24, height: 300,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--text-3)', fontSize: 13,
      }}>
        No funnel data
      </FrostedGlassCard>
    );
  }

  const rows = data.funnel.map((item, i) => ({
    name:  STAGE_LABELS[item.stage] ?? item.stage,
    count: item.count,
    pct:   Math.round(item.percentage * 100),
    color: BAR_COLORS[i % BAR_COLORS.length],
  }));
  const max = rows[0]?.count || 1;

  return (
    <FrostedGlassCard noTilt style={{ padding: '22px 22px 18px' }}>
      {/* Header */}
      <div style={{ marginBottom: 18 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-1)', letterSpacing: '-0.01em' }}>
            Conversion Funnel
          </div>
          <span style={{
            fontSize: 10.5, fontWeight: 700, color: 'var(--text-3)',
            letterSpacing: '0.06em', textTransform: 'uppercase',
          }}>
            {rows[rows.length - 1]?.pct ?? 0}% overall
          </span>
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--text-3)', marginTop: 3 }}>
          Visitor progression through purchase stages
        </div>
      </div>

      {/* Rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {rows.map((row, i) => {
          const isHov = hoveredRow === i;
          return (
            <div
              key={i}
              className="funnel-row"
              onMouseEnter={() => setHoveredRow(i)}
              onMouseLeave={() => setHoveredRow(null)}
              style={{ borderLeft: `2px solid ${isHov ? row.color : 'transparent'}` }}
            >
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', marginBottom: 7,
              }}>
                <span style={{
                  fontSize: 12, fontWeight: 600,
                  color: isHov ? row.color : 'var(--text-2)',
                  textShadow: isHov ? `0 0 12px ${row.color}80` : 'none',
                  transition: 'color 0.15s, text-shadow 0.15s',
                }}>
                  {row.name}
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                  <span style={{
                    fontSize: 13, fontWeight: 800,
                    fontVariantNumeric: 'tabular-nums',
                    color: isHov ? '#fff' : 'var(--text-1)',
                    textShadow: isHov ? `0 0 16px ${row.color}` : 'none',
                    transition: 'color 0.15s, text-shadow 0.15s',
                  }}>
                    {row.count.toLocaleString()}
                  </span>
                  <span style={{
                    fontSize: 10.5, fontWeight: 800, color: row.color,
                    background: isHov ? `${row.color}28` : `${row.color}14`,
                    border: `1px solid ${isHov ? row.color + '70' : row.color + '30'}`,
                    padding: '1px 8px', borderRadius: 6,
                    boxShadow: isHov ? `0 0 12px ${row.color}55` : 'none',
                    transition: 'background 0.15s, border-color 0.15s, box-shadow 0.15s',
                  }}>
                    {row.pct}%
                  </span>
                </div>
              </div>

              {/* Track */}
              <div style={{
                height: isHov ? 9 : 7, borderRadius: 5,
                background: 'rgba(255,255,255,0.05)',
                border: `1px solid ${isHov ? row.color + '30' : 'rgba(255,255,255,0.06)'}`,
                overflow: 'hidden',
                transition: 'height 0.2s, border-color 0.15s',
              }}>
                <div style={{
                  height: '100%',
                  width: `${(row.count / max) * 100}%`,
                  borderRadius: 5,
                  background: isHov
                    ? `linear-gradient(90deg, ${row.color}, white)`
                    : `linear-gradient(90deg, ${row.color}bb, ${row.color})`,
                  boxShadow: isHov ? `0 0 16px ${row.color}90` : `0 0 6px ${row.color}40`,
                  transition: 'background 0.2s, box-shadow 0.2s, width 0.7s cubic-bezier(0.4,0,0.2,1)',
                  animation: 'barGrow 0.7s cubic-bezier(0.4,0,0.2,1) both',
                }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{
        marginTop: 18, paddingTop: 14,
        borderTop: '1px solid rgba(255,255,255,0.07)',
        display: 'flex', justifyContent: 'space-between',
        fontSize: 11, color: 'var(--text-3)',
      }}>
        <span>{rows[0]?.count.toLocaleString()} entered</span>
        <span>→ {rows[rows.length - 1]?.count.toLocaleString()} converted ({rows[rows.length - 1]?.pct}%)</span>
      </div>
    </FrostedGlassCard>
  );
}
