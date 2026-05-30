import React, { useState } from 'react';
import { AlertTriangle, OctagonAlert, Info, ShieldCheck } from 'lucide-react';
import { AnomalyResponse, AnomalyItem } from '../api';
import { FrostedGlassCard } from './ui/interactive-frosted-glass-card';

interface AnomalyPanelProps { data: AnomalyResponse | null; }

const SEV: Record<string, { icon: any; color: string; glowColor: string; label: string }> = {
  high:   { icon: OctagonAlert,  color: '#f87171', glowColor: 'rgba(248,113,113,0.14)', label: 'Critical' },
  medium: { icon: AlertTriangle, color: '#fbbf24', glowColor: 'rgba(251,191,36,0.12)',  label: 'Warning'  },
  low:    { icon: Info,          color: '#818cf8', glowColor: 'rgba(129,140,248,0.12)', label: 'Info'     },
};

export function AnomalyPanel({ data }: AnomalyPanelProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!data?.anomalies?.length) {
    return (
      <FrostedGlassCard noTilt style={{
        padding: 24, minHeight: 190,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        gap: 12, textAlign: 'center',
      }}>
        <div style={{
          width: 48, height: 48, borderRadius: '50%',
          background: 'rgba(52,211,153,0.12)',
          border: '1px solid rgba(52,211,153,0.28)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          animation: 'glow-pulse 2.5s ease-in-out infinite',
        }}>
          <ShieldCheck style={{ width: 22, height: 22, color: '#34d399' }} />
        </div>
        <div>
          <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-1)' }}>All Clear</div>
          <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 4 }}>No active anomalies detected</div>
        </div>
      </FrostedGlassCard>
    );
  }

  const fmtTime = (iso: string) => {
    try { return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
    catch { return ''; }
  };

  return (
    <FrostedGlassCard noTilt style={{ padding: '22px 22px 18px', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-1)', letterSpacing: '-0.01em' }}>
            Anomalies
          </div>
          <span style={{
            fontSize: 10.5, fontWeight: 700,
            color: '#f87171',
            background: 'rgba(248,113,113,0.12)',
            border: '1px solid rgba(248,113,113,0.28)',
            padding: '2px 8px', borderRadius: 6,
          }}>
            {data.anomalies.length} active
          </span>
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--text-3)', marginTop: 3 }}>
          Active alerts and operational flags
        </div>
      </div>

      {/* Alert list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1, overflowY: 'auto', maxHeight: 260 }}>
        {data.anomalies.map((a, i) => {
          const s = SEV[a.severity] ?? SEV.low;
          const Icon = s.icon;
          const isHov = hoveredIdx === i;
          return (
            <div
              key={i}
              className="anomaly-row"
              onMouseEnter={() => setHoveredIdx(i)}
              onMouseLeave={() => setHoveredIdx(null)}
              style={{
                display: 'flex', gap: 11,
                padding: '11px 14px', borderRadius: 10,
                background: isHov ? `${s.color}20` : s.glowColor,
                border: `1px solid ${isHov ? s.color + '55' : s.color + '22'}`,
                borderLeft: `3px solid ${s.color}`,
                backdropFilter: 'blur(8px)',
                boxShadow: isHov
                  ? `0 6px 24px rgba(0,0,0,0.25), 0 0 0 1px ${s.color}40, 0 0 20px ${s.color}30`
                  : 'none',
              }}
            >
              <div style={{
                width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: isHov ? `${s.color}28` : 'transparent',
                boxShadow: isHov ? `0 0 12px ${s.color}60` : 'none',
                transition: 'background 0.2s, box-shadow 0.2s',
              }}>
                <Icon style={{
                  width: 14, height: 14, color: s.color,
                  filter: isHov ? `drop-shadow(0 0 5px ${s.color})` : 'none',
                  transform: isHov ? 'scale(1.25)' : 'scale(1)',
                  transition: 'filter 0.2s, transform 0.2s',
                }} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                  <span style={{
                    fontSize: 10.5, fontWeight: 800, color: s.color,
                    textTransform: 'uppercase', letterSpacing: '0.05em',
                    textShadow: isHov ? `0 0 10px ${s.color}80` : 'none',
                    transition: 'text-shadow 0.2s',
                  }}>
                    {a.type.replace(/_/g, ' ')}
                  </span>
                  <span style={{ fontSize: 10, color: 'var(--text-3)', flexShrink: 0 }}>
                    {fmtTime(a.timestamp)}
                  </span>
                </div>
                <p style={{
                  fontSize: 12, marginTop: 3, lineHeight: 1.45,
                  color: isHov ? 'var(--text-1)' : 'var(--text-2)',
                  transition: 'color 0.2s',
                }}>
                  {a.message}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{
        paddingTop: 12, marginTop: 10,
        borderTop: '1px solid rgba(255,255,255,0.07)',
        fontSize: 11, color: 'var(--text-3)',
        display: 'flex', justifyContent: 'space-between',
      }}>
        <span>{data.anomalies.length} alert{data.anomalies.length !== 1 ? 's' : ''}</span>
        <span>All severities</span>
      </div>
    </FrostedGlassCard>
  );
}
