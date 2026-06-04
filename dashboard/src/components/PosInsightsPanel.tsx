import React from 'react';
import { PosSummaryResponse } from '../api';
import { IndianRupee, ShoppingCart, TrendingUp, BarChart2 } from 'lucide-react';

function fmt(n: number) {
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  if (n >= 1000)   return `₹${(n / 1000).toFixed(1)}K`;
  return `₹${n.toFixed(0)}`;
}

interface Props {
  data: PosSummaryResponse | null;
  accentColor?: string;
}

export function PosInsightsPanel({ data, accentColor = '#34d399' }: Props) {
  const maxRev = data ? Math.max(...data.hourly_revenue.map(h => h.revenue), 1) : 1;

  return (
    <div style={{
      background: 'rgba(8,8,14,0.55)',
      border: '1px solid rgba(129,140,248,0.14)',
      borderRadius: 14,
      backdropFilter: 'blur(20px)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '13px 16px 11px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', gap: 9,
      }}>
        <IndianRupee style={{ width: 14, height: 14, color: accentColor }} />
        <span style={{ fontSize: 12.5, fontWeight: 700, color: '#e2e4f0', letterSpacing: '-0.01em' }}>
          POS Revenue
        </span>
        <span style={{ fontSize: 10, color: 'rgba(148,163,184,0.4)', marginLeft: 'auto' }}>Today</span>
      </div>

      <div style={{ padding: '14px 16px' }}>
        {!data ? (
          <div style={{ textAlign: 'center', padding: '24px 0', color: 'rgba(148,163,184,0.4)', fontSize: 12 }}>
            No POS data yet — upload transactions to see revenue
          </div>
        ) : (
          <>
            {/* KPI row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 16 }}>
              {[
                { label: 'Revenue',      value: fmt(data.total_revenue_inr),             icon: IndianRupee, accent: accentColor },
                { label: 'Transactions', value: data.total_transactions.toString(),       icon: ShoppingCart, accent: '#818cf8' },
                { label: 'Avg Basket',   value: fmt(data.avg_basket_inr),                icon: BarChart2,   accent: '#fbbf24' },
                { label: '₹/Visitor',    value: fmt(data.revenue_per_visitor),            icon: TrendingUp,  accent: '#38bdf8' },
              ].map(k => (
                <div key={k.label} style={{
                  padding: '10px 12px', borderRadius: 10,
                  background: `${k.accent}0d`,
                  border: `1px solid ${k.accent}22`,
                }}>
                  <k.icon style={{ width: 12, height: 12, color: k.accent, marginBottom: 5 }} />
                  <div style={{ fontSize: 18, fontWeight: 800, color: k.accent, lineHeight: 1 }}>{k.value}</div>
                  <div style={{ fontSize: 9.5, color: 'rgba(148,163,184,0.5)', marginTop: 3 }}>{k.label}</div>
                </div>
              ))}
            </div>

            {/* Hourly revenue bar chart (SVG sparkline) */}
            {data.hourly_revenue.length > 0 && (
              <div>
                <div style={{ fontSize: 10, color: 'rgba(148,163,184,0.5)', marginBottom: 8, fontWeight: 600 }}>
                  HOURLY REVENUE
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 60 }}>
                  {/* Fill hours 8–22 */}
                  {Array.from({ length: 15 }, (_, i) => i + 8).map(hr => {
                    const entry = data.hourly_revenue.find(h => h.hour === hr);
                    const rev   = entry?.revenue ?? 0;
                    const pct   = rev / maxRev;
                    const height = Math.max(2, Math.round(pct * 52));
                    const hasData = rev > 0;
                    return (
                      <div key={hr} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                        <div
                          title={`${hr}:00 — ${fmt(rev)} (${entry?.transactions ?? 0} txns)`}
                          style={{
                            width: '100%', height: `${height}px`,
                            background: hasData
                              ? `linear-gradient(180deg, ${accentColor} 0%, ${accentColor}55 100%)`
                              : 'rgba(255,255,255,0.05)',
                            borderRadius: '3px 3px 0 0',
                            boxShadow: hasData ? `0 0 8px ${accentColor}40` : 'none',
                            transition: 'height 0.4s cubic-bezier(0.22,1,0.36,1)',
                            cursor: hasData ? 'pointer' : 'default',
                          }}
                        />
                        <span style={{
                          fontSize: 7.5, color: 'rgba(100,110,140,0.5)',
                          fontFamily: 'monospace',
                        }}>
                          {hr}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
