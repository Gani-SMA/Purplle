import React, { useState } from 'react';
import { HeatmapResponse, ZoneHeatmapItem } from '../api';
import { FrostedGlassCard } from './ui/interactive-frosted-glass-card';

interface ZoneHeatmapProps { data: HeatmapResponse | null; }
interface LayoutZone { id: string; label: string; x: number; y: number; w: number; h: number; }

function intensityToColor(v: number): string {
  const t = v / 100;
  const h = Math.round(240 - t * 85);
  const s = Math.round(55 + t * 35);
  const l = Math.round(18 + t * 28);
  return `hsl(${h},${s}%,${l}%)`;
}
function intensityAlpha(v: number): number {
  return 0.18 + (v / 100) * 0.65;
}

const BASE_LAYOUT: LayoutZone[] = [
  { id: 'ZONE_ENTRY',     label: 'Entry',     x: 10,  y: 20, w: 70,  h: 160 },
  { id: 'ZONE_SKINCARE',  label: 'Skincare',  x: 95,  y: 20, w: 95,  h: 75  },
  { id: 'ZONE_HAIRCARE',  label: 'Haircare',  x: 95,  y: 105,w: 95,  h: 75  },
  { id: 'ZONE_MAKEUP',    label: 'Makeup',    x: 205, y: 20, w: 100, h: 160 },
  { id: 'ZONE_FRAGRANCE', label: 'Fragrance', x: 95,  y: 105,w: 95,  h: 75  },
  { id: 'ZONE_WELLNESS',  label: 'Wellness',  x: 95,  y: 105,w: 95,  h: 75  },
  { id: 'ZONE_BILLING',   label: 'Billing',   x: 320, y: 20, w: 70,  h: 160 },
];

export function ZoneHeatmap({ data }: ZoneHeatmapProps) {
  const [hovered, setHovered] = useState<ZoneHeatmapItem | null>(null);

  if (!data?.zones?.length) {
    return (
      <FrostedGlassCard noTilt style={{
        padding: 24, height: 300,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--text-3)', fontSize: 13,
      }}>
        No heatmap data
      </FrostedGlassCard>
    );
  }

  const isSTR001 = data.store_id === 'STR001';
  const isSTR002 = data.store_id === 'STR002';

  const layout = BASE_LAYOUT.filter(z => {
    if (z.id === 'ZONE_HAIRCARE')  return isSTR001;
    if (z.id === 'ZONE_FRAGRANCE') return isSTR002;
    if (z.id === 'ZONE_WELLNESS')  return !isSTR001 && !isSTR002;
    return true;
  });

  const adjustedLayout = layout.map(z =>
    z.id === 'ZONE_SKINCARE' && !isSTR001 ? { ...z, h: 160 } : z
  );

  const getMetric = (id: string): ZoneHeatmapItem =>
    data.zones.find(z => z.zone_name === id) ?? { zone_name: id, checkins: 0, normalized_intensity: 0 };

  return (
    <FrostedGlassCard noTilt style={{ padding: '22px 22px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-1)', letterSpacing: '-0.01em' }}>
            Zone Traffic Map
          </div>
          <div style={{ fontSize: 11.5, color: 'var(--text-3)', marginTop: 3 }}>
            Real-time occupancy heat by zone
          </div>
        </div>
        <span style={{
          fontSize: 10.5, color: 'var(--text-3)',
          background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)',
          padding: '3px 9px', borderRadius: 6, fontWeight: 500,
        }}>
          {data.data_confidence}% conf.
        </span>
      </div>

      <svg viewBox="0 0 410 200" style={{ width: '100%', maxHeight: 180, overflow: 'visible' }}>
        {/* Glow defs */}
        <defs>
          {adjustedLayout.map(cell => {
            const m = getMetric(cell.id);
            const base = intensityToColor(m.normalized_intensity);
            return (
              <filter key={`filter-${cell.id}`} id={`glow-${cell.id}`} x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation={hovered?.zone_name === cell.id ? '5' : '2'} result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            );
          })}
        </defs>

        {/* Store outline */}
        <rect x="3" y="3" width="404" height="194" rx="10"
          fill="rgba(255,255,255,0.02)"
          stroke="rgba(129,140,248,0.20)" strokeWidth="1.5" strokeDasharray="5 4" />

        {adjustedLayout.map(cell => {
          const m = getMetric(cell.id);
          const base = intensityToColor(m.normalized_intensity);
          const alpha = intensityAlpha(m.normalized_intensity);
          const isHov = hovered?.zone_name === cell.id;
          const textLight = m.normalized_intensity > 40 || isHov;

          // On hover: expand the cell slightly from center
          const scaleX = isHov ? 1.04 : 1;
          const scaleY = isHov ? 1.04 : 1;
          const tx = isHov ? -(cell.w * 0.02) : 0;
          const ty = isHov ? -(cell.h * 0.02) : 0;

          return (
            <g
              key={cell.id}
              onMouseEnter={() => setHovered(m)}
              onMouseLeave={() => setHovered(null)}
              style={{ cursor: 'default' }}
              transform={`translate(${cell.x + tx}, ${cell.y + ty}) scale(${scaleX}, ${scaleY})`}
              // SVG doesn't support CSS transitions natively — use style for the transform
            >
              {/* Outer glow ring on hover */}
              {isHov && (
                <rect
                  x={-4} y={-4}
                  width={cell.w + 8} height={cell.h + 8}
                  rx="12" fill="none"
                  stroke={base} strokeWidth="2" opacity="0.60"
                  filter={`url(#glow-${cell.id})`}
                />
              )}
              {/* Zone fill */}
              <rect
                x={0} y={0}
                width={cell.w} height={cell.h}
                rx="8"
                fill={base}
                fillOpacity={isHov ? Math.min(alpha + 0.30, 1.0) : alpha}
                stroke={isHov ? 'rgba(255,255,255,0.60)' : 'rgba(255,255,255,0.08)'}
                strokeWidth={isHov ? 1.8 : 0.8}
                filter={isHov ? `url(#glow-${cell.id})` : undefined}
              />
              {/* Labels */}
              <text
                x={cell.w / 2} y={cell.h / 2 - 7}
                textAnchor="middle" fontSize={isHov ? '10' : '8.5'}
                fontWeight="700"
                fill={textLight ? '#ffffff' : 'rgba(200,200,230,0.8)'}
                style={{ pointerEvents: 'none', userSelect: 'none' }}
              >
                {cell.label}
              </text>
              <text
                x={cell.w / 2} y={cell.h / 2 + 10}
                textAnchor="middle" fontSize={isHov ? '10' : '8.5'}
                fontWeight="600"
                fill={textLight ? 'rgba(255,255,255,0.90)' : 'rgba(170,170,200,0.7)'}
                style={{ pointerEvents: 'none', userSelect: 'none' }}
              >
                {Math.round(m.normalized_intensity)}%
              </text>
              {/* Visit count on hover */}
              {isHov && (
                <text
                  x={cell.w / 2} y={cell.h / 2 + 26}
                  textAnchor="middle" fontSize="8"
                  fontWeight="500"
                  fill="rgba(255,255,255,0.65)"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  {m.checkins} visits
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Footer */}
      <div style={{
        marginTop: 12, paddingTop: 12,
        borderTop: '1px solid rgba(255,255,255,0.07)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        fontSize: 11, color: 'var(--text-3)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <span>Low</span>
          <div style={{
            width: 64, height: 5, borderRadius: 3,
            background: 'linear-gradient(to right, hsl(240,55%,22%), hsl(155,90%,32%))',
          }} />
          <span>High</span>
        </div>
        {hovered ? (
          <span style={{ color: 'var(--text-1)', fontWeight: 700, fontSize: 12 }}>
            {hovered.zone_name.replace('ZONE_', '')}
            <span style={{ color: 'var(--text-3)', fontWeight: 400 }}> — {hovered.checkins.toLocaleString()} visits</span>
          </span>
        ) : (
          <span>Hover zone for details</span>
        )}
      </div>
    </FrostedGlassCard>
  );
}
