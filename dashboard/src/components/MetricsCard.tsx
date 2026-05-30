import React, { useState } from 'react';
import { LucideIcon } from 'lucide-react';
import { FrostedGlassCard } from './ui/interactive-frosted-glass-card';

interface MetricsCardProps {
  title: string;
  value: string | number;
  sub: string;
  icon: LucideIcon;
  accent?: string;
  pulse?: boolean;
}

export function MetricsCard({
  title, value, sub, icon: Icon, accent = '#818cf8', pulse = false,
}: MetricsCardProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <FrostedGlassCard
      glowColor={`${accent}70`}
      style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 16 }}
    >
      <div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{ display: 'contents' }}
      >
        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{
            fontSize: 11, fontWeight: 700, color: 'var(--text-3)',
            letterSpacing: '0.08em', textTransform: 'uppercase',
            transition: 'color 0.2s',
            ...(hovered ? { color: 'var(--text-2)' } : {}),
          }}>
            {title}
          </span>

          {/* Icon box — spins on hover */}
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: hovered ? `${accent}30` : `${accent}18`,
            border: `1px solid ${hovered ? accent + '70' : accent + '28'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: hovered ? `0 0 20px ${accent}55, 0 0 40px ${accent}22` : 'none',
            transition: 'background 0.2s, border-color 0.2s, box-shadow 0.2s, transform 0.2s',
            transform: hovered ? 'scale(1.18) rotate(8deg)' : 'scale(1) rotate(0deg)',
          }}>
            <Icon style={{
              width: 16, height: 16, color: accent,
              filter: hovered ? `drop-shadow(0 0 6px ${accent})` : 'none',
              transition: 'filter 0.2s',
            }} />
          </div>
        </div>

        {/* Value */}
        <div>
          <div style={{
            fontSize: 32, fontWeight: 800, lineHeight: 1, letterSpacing: '-0.03em',
            color: hovered ? '#ffffff' : 'var(--text-1)',
            fontVariantNumeric: 'tabular-nums',
            display: 'flex', alignItems: 'center', gap: 9,
            textShadow: hovered ? `0 0 30px ${accent}90` : 'none',
            transition: 'color 0.2s, text-shadow 0.2s',
          }}>
            {value}
            {pulse && (
              <span style={{
                width: 8, height: 8, borderRadius: '50%',
                background: accent, display: 'inline-block',
                boxShadow: `0 0 ${hovered ? '16px' : '8px'} ${accent}`,
                animation: 'pulse 1.4s cubic-bezier(0.4,0,0.6,1) infinite',
                transition: 'box-shadow 0.2s',
              }} />
            )}
          </div>
          <div style={{
            fontSize: 11.5, marginTop: 6,
            color: hovered ? 'var(--text-2)' : 'var(--text-3)',
            transition: 'color 0.2s',
          }}>
            {sub}
          </div>
        </div>

        {/* Accent gradient bar */}
        <div style={{
          height: hovered ? 3 : 2, borderRadius: 2, marginTop: -4,
          background: `linear-gradient(90deg, ${accent} 0%, ${accent}40 60%, transparent 100%)`,
          boxShadow: hovered ? `0 0 12px ${accent}80` : 'none',
          transition: 'height 0.2s, box-shadow 0.2s',
        }} />
      </div>
    </FrostedGlassCard>
  );
}
