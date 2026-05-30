import React, { useState } from 'react';
import { Database, Cpu, CheckCircle2, AlertCircle } from 'lucide-react';
import { HealthResponse } from '../api';
import { FrostedGlassCard } from './ui/interactive-frosted-glass-card';

interface HealthTableProps {
  health: HealthResponse | null;
  loading: boolean;
}

const fmtLag = (lag: number | null) => {
  if (lag === null) return '—';
  if (lag < 1) return '< 1 min';
  return `${Math.round(lag)} min`;
};

const fmtTs = (ts: string | null) => {
  if (!ts) return 'No events';
  try { return new Date(ts).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }); }
  catch { return ts; }
};

export function HealthTable({ health, loading }: HealthTableProps) {
  const [hoveredStore, setHoveredStore] = useState<string | null>(null);
  const [hoveredBlock, setHoveredBlock] = useState<string | null>(null);

  if (loading) {
    return (
      <FrostedGlassCard noTilt style={{
        padding: 24, height: 190,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 10, color: 'var(--text-3)', fontSize: 13,
      }}>
        <div style={{
          width: 18, height: 18,
          border: '2.5px solid rgba(129,140,248,0.2)',
          borderTopColor: '#818cf8', borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
          boxShadow: '0 0 12px rgba(129,140,248,0.35)',
        }} />
        Loading diagnostics…
      </FrostedGlassCard>
    );
  }

  if (!health) {
    return (
      <FrostedGlassCard noTilt style={{
        padding: 24, height: 190,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 10, color: '#f87171', fontSize: 13,
      }}>
        <AlertCircle style={{ width: 16, height: 16 }} /> Failed to load system health
      </FrostedGlassCard>
    );
  }

  return (
    <FrostedGlassCard noTilt style={{ padding: '22px 22px 18px' }}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-1)', letterSpacing: '-0.01em' }}>
          Infrastructure
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--text-3)', marginTop: 3 }}>
          Database, cache, and feed status
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: 16 }}>
        {/* Connection blocks */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            { icon: Database, label: 'PostgreSQL', key: 'pg' },
            { icon: Cpu,      label: 'Redis Cache', key: 'redis' },
          ].map(({ icon: Icon, label, key }) => {
            const isHov = hoveredBlock === key;
            return (
              <div
                key={key}
                className="infra-block"
                onMouseEnter={() => setHoveredBlock(key)}
                onMouseLeave={() => setHoveredBlock(null)}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 13px', borderRadius: 9,
                  background: isHov ? 'rgba(52,211,153,0.14)' : 'rgba(52,211,153,0.06)',
                  border: `1px solid ${isHov ? 'rgba(52,211,153,0.45)' : 'rgba(52,211,153,0.18)'}`,
                  cursor: 'default',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Icon style={{
                    width: 13, height: 13,
                    color: isHov ? '#34d399' : 'var(--text-3)',
                    filter: isHov ? 'drop-shadow(0 0 5px #34d399)' : 'none',
                    transition: 'color 0.2s, filter 0.2s',
                  }} />
                  <span style={{
                    fontSize: 12, fontWeight: 500,
                    color: isHov ? 'var(--text-1)' : 'var(--text-2)',
                    transition: 'color 0.2s',
                  }}>{label}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <CheckCircle2 style={{
                    width: 12, height: 12, color: '#34d399',
                    filter: isHov ? 'drop-shadow(0 0 6px #34d399)' : 'none',
                    transition: 'filter 0.2s',
                  }} />
                  <span style={{
                    fontSize: 11, color: '#34d399', fontWeight: 700,
                    textShadow: isHov ? '0 0 8px #34d39980' : 'none',
                    transition: 'text-shadow 0.2s',
                  }}>OK</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Per-store table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                {['Store', 'Status', 'Last Event', 'Lag'].map(h => (
                  <th key={h} style={{
                    paddingBottom: 8,
                    textAlign: h === 'Lag' ? 'right' : 'left',
                    fontSize: 10.5, fontWeight: 700, color: 'var(--text-3)',
                    letterSpacing: '0.06em', textTransform: 'uppercase',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {health.stores.map(store => {
                const isLive = store.status === 'live';
                const isHov = hoveredStore === store.store_id;
                return (
                  <tr
                    key={store.store_id}
                    className="health-row"
                    onMouseEnter={() => setHoveredStore(store.store_id)}
                    onMouseLeave={() => setHoveredStore(null)}
                    style={{
                      borderBottom: '1px solid rgba(255,255,255,0.05)',
                      background: isHov ? 'rgba(129,140,248,0.07)' : 'transparent',
                    }}
                  >
                    <td style={{
                      padding: '10px 0', fontWeight: 800, fontSize: 13,
                      color: isHov ? '#ffffff' : 'var(--text-1)',
                      textShadow: isHov ? '0 0 14px rgba(129,140,248,0.70)' : 'none',
                      transition: 'color 0.15s, text-shadow 0.15s',
                    }}>
                      {store.store_id}
                    </td>
                    <td style={{ padding: '10px 8px' }}>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: 5,
                        fontSize: 10.5, fontWeight: 700,
                        padding: '2px 8px', borderRadius: 6,
                        background: isLive
                          ? (isHov ? 'rgba(52,211,153,0.20)' : 'rgba(52,211,153,0.12)')
                          : (isHov ? 'rgba(251,191,36,0.20)' : 'rgba(251,191,36,0.12)'),
                        border: `1px solid ${isLive
                          ? (isHov ? 'rgba(52,211,153,0.55)' : 'rgba(52,211,153,0.25)')
                          : (isHov ? 'rgba(251,191,36,0.55)' : 'rgba(251,191,36,0.25)')}`,
                        color: isLive ? '#34d399' : '#fbbf24',
                        boxShadow: isHov
                          ? `0 0 14px ${isLive ? 'rgba(52,211,153,0.40)' : 'rgba(251,191,36,0.40)'}`
                          : 'none',
                        transition: 'background 0.15s, border-color 0.15s, box-shadow 0.15s',
                      }}>
                        <span style={{
                          width: 5, height: 5, borderRadius: '50%',
                          background: isLive ? '#34d399' : '#fbbf24',
                          boxShadow: `0 0 ${isHov ? '10px' : '5px'} ${isLive ? '#34d399' : '#fbbf24'}`,
                          animation: isLive ? 'pulse 2s infinite' : 'none',
                          transition: 'box-shadow 0.2s',
                        }} />
                        {isLive ? 'Live' : 'Stale'}
                      </span>
                    </td>
                    <td style={{
                      padding: '10px 0', fontSize: 11,
                      color: isHov ? 'var(--text-2)' : 'var(--text-3)',
                      transition: 'color 0.15s',
                    }}>
                      {fmtTs(store.last_event_ts)}
                    </td>
                    <td style={{
                      padding: '10px 0', textAlign: 'right',
                      fontVariantNumeric: 'tabular-nums',
                      color: isHov ? 'var(--text-1)' : 'var(--text-2)',
                      fontWeight: isHov ? 700 : 400,
                      transition: 'color 0.15s, font-weight 0.15s',
                    }}>
                      {fmtLag(store.lag_minutes)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </FrostedGlassCard>
  );
}
