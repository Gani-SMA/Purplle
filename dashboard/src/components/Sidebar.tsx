import React, { useState } from 'react';
import { Store, Key, RefreshCw, Activity, MapPin } from 'lucide-react';
import { getApiKey, setApiKey } from '../api';

interface SidebarProps {
  currentStoreId: string;
  onStoreChange: (id: string) => void;
  apiHealth: 'healthy' | 'stale' | 'offline';
  onRefreshHealth: () => void;
}

const STORES = [
  { id: 'STR001', name: 'Metro Mall',  city: 'Mumbai',    color: '#818cf8' },
  { id: 'STR002', name: 'Cyber City',  city: 'Delhi',     color: '#34d399' },
  { id: 'STR003', name: 'Koramangala', city: 'Bengaluru', color: '#fbbf24' },
];

const HEALTH_COLOR: Record<string, string> = {
  healthy: '#34d399',
  stale:   '#fbbf24',
  offline: '#f87171',
};

export function Sidebar({ currentStoreId, onStoreChange, apiHealth, onRefreshHealth }: SidebarProps) {
  const [showKey, setShowKey] = useState(false);
  const [keyInput, setKeyInput] = useState(getApiKey());

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setApiKey(keyInput);
    setShowKey(false);
    window.location.reload();
  };

  return (
    <aside style={{
      width: 224, flexShrink: 0,
      background: 'rgba(10, 10, 16, 0.50)',
      backdropFilter: 'blur(28px) saturate(160%)',
      WebkitBackdropFilter: 'blur(28px) saturate(160%)',
      borderRight: '1px solid rgba(129,140,248,0.14)',
      display: 'flex', flexDirection: 'column',
      height: '100vh',
      position: 'relative', zIndex: 10,
    }}>
      {/* ── Brand ── */}
      <div style={{
        padding: '18px 20px 16px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', gap: 11,
      }}>
        {/* Logo mark */}
        <div style={{
          width: 34, height: 34, borderRadius: 10,
          background: 'linear-gradient(135deg, #6366f1 0%, #818cf8 100%)',
          boxShadow: '0 0 16px rgba(129,140,248,0.35)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <Store style={{ width: 16, height: 16, color: '#fff' }} />
        </div>
        <div>
          <div style={{ fontSize: 13.5, fontWeight: 700, color: '#f0f0f8', letterSpacing: '-0.01em' }}>
            Purplle
          </div>
          <div style={{ fontSize: 10.5, color: 'rgba(129,140,248,0.7)', fontWeight: 500, letterSpacing: '0.03em' }}>
            Store Intelligence
          </div>
        </div>
      </div>

      {/* ── Store list ── */}
      <div style={{ flex: 1, padding: '14px 12px', overflowY: 'auto' }}>
        <div style={{
          fontSize: 9.5, fontWeight: 700, letterSpacing: '0.10em',
          textTransform: 'uppercase', color: 'rgba(148,148,180,0.6)',
          padding: '0 6px', marginBottom: 10,
        }}>
          Locations
        </div>

        {STORES.map(store => {
          const active = store.id === currentStoreId;
          return (
            <button
              key={store.id}
              onClick={() => onStoreChange(store.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                width: '100%', padding: '9px 10px', borderRadius: 9,
                background: active
                  ? `rgba(${store.id === 'STR001' ? '129,140,248' : store.id === 'STR002' ? '52,211,153' : '251,191,36'},0.10)`
                  : 'transparent',
                border: `1px solid ${active ? `${store.color}35` : 'transparent'}`,
                color: active ? '#f0f0f8' : 'rgba(148,148,180,0.7)',
                cursor: 'pointer', textAlign: 'left',
                marginBottom: 3,
                transition: 'background 0.15s, color 0.15s, border-color 0.15s, transform 0.2s cubic-bezier(0.22,1,0.36,1), box-shadow 0.2s',
              }}
              onMouseEnter={e => {
                if (!active) {
                  const el = e.currentTarget as HTMLElement;
                  el.style.background = 'rgba(255,255,255,0.08)';
                  el.style.color = '#f0f0f8';
                  el.style.transform = 'translateX(4px) scale(1.03)';
                  el.style.boxShadow = '0 4px 16px rgba(0,0,0,0.25), 0 0 0 1px rgba(255,255,255,0.08)';
                  el.style.borderColor = 'rgba(255,255,255,0.12)';
                }
              }}
              onMouseLeave={e => {
                if (!active) {
                  const el = e.currentTarget as HTMLElement;
                  el.style.background = 'transparent';
                  el.style.color = 'rgba(148,148,180,0.7)';
                  el.style.transform = '';
                  el.style.boxShadow = 'none';
                  el.style.borderColor = 'transparent';
                }
              }}
            >
              {/* Color dot */}
              <div style={{
                width: 8, height: 8, borderRadius: '50%',
                background: active ? store.color : 'rgba(255,255,255,0.15)',
                boxShadow: active ? `0 0 8px ${store.color}80` : 'none',
                flexShrink: 0,
                transition: 'background 0.2s, box-shadow 0.2s',
              }} />

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12.5, fontWeight: 600, lineHeight: 1.3 }}>{store.name}</div>
                <div style={{
                  fontSize: 10.5, marginTop: 1,
                  color: active ? 'rgba(200,200,230,0.6)' : 'rgba(120,120,150,0.6)',
                  display: 'flex', alignItems: 'center', gap: 3,
                }}>
                  <MapPin style={{ width: 9, height: 9 }} />
                  {store.city} · {store.id}
                </div>
              </div>

              {active && (
                <div style={{
                  width: 5, height: 5, borderRadius: '50%',
                  background: store.color,
                  boxShadow: `0 0 6px ${store.color}`,
                  animation: 'pulse 2s infinite',
                  flexShrink: 0,
                }} />
              )}
            </button>
          );
        })}
      </div>

      {/* ── Bottom controls ── */}
      <div style={{
        padding: '12px 12px 16px',
        borderTop: '1px solid rgba(255,255,255,0.06)',
      }}>
        {/* API health pill */}
        <button
          onClick={onRefreshHealth}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            width: '100%', padding: '9px 12px', borderRadius: 9,
            background: 'rgba(255,255,255,0.04)',
            border: `1px solid rgba(${apiHealth === 'healthy' ? '52,211,153' : apiHealth === 'stale' ? '251,191,36' : '248,113,113'},0.22)`,
            cursor: 'pointer', marginBottom: 7,
            transition: 'background 0.2s, box-shadow 0.2s, transform 0.2s, border-color 0.2s, filter 0.2s',
          }}
          onMouseEnter={e => {
            const hc = HEALTH_COLOR[apiHealth];
            const el = e.currentTarget as HTMLElement;
            el.style.background = `rgba(${apiHealth === 'healthy' ? '52,211,153' : apiHealth === 'stale' ? '251,191,36' : '248,113,113'},0.12)`;
            el.style.boxShadow = `0 6px 20px rgba(0,0,0,0.25), 0 0 0 1px ${hc}50, 0 0 18px ${hc}35`;
            el.style.transform = 'scale(1.03) translateY(-1px)';
            el.style.borderColor = `${hc}55`;
            el.style.filter = 'brightness(1.15)';
          }}
          onMouseLeave={e => {
            const el = e.currentTarget as HTMLElement;
            el.style.background = 'rgba(255,255,255,0.04)';
            el.style.boxShadow = 'none';
            el.style.transform = '';
            el.style.borderColor = '';
            el.style.filter = '';
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <Activity style={{ width: 12, height: 12, color: HEALTH_COLOR[apiHealth] }} />
            <span style={{ fontSize: 12, color: 'rgba(200,200,230,0.75)', fontWeight: 600 }}>API Status</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: HEALTH_COLOR[apiHealth],
              boxShadow: `0 0 8px ${HEALTH_COLOR[apiHealth]}`,
              display: 'inline-block',
              animation: apiHealth === 'healthy' ? 'pulse 1.8s infinite' : 'none',
            }} />
            <span style={{
              fontSize: 11, color: HEALTH_COLOR[apiHealth], fontWeight: 700,
              textTransform: 'capitalize',
            }}>
              {apiHealth}
            </span>
            <RefreshCw style={{ width: 10, height: 10, color: 'rgba(148,148,180,0.4)', marginLeft: 2 }} />
          </div>
        </button>

        {/* API Key */}
        <button
          onClick={() => setShowKey(v => !v)}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            width: '100%', padding: '9px 12px', borderRadius: 9,
            background: 'transparent',
            border: '1px solid rgba(129,140,248,0.15)',
            color: 'rgba(148,148,180,0.6)', cursor: 'pointer', fontSize: 12,
            fontWeight: 500,
            transition: 'background 0.2s, color 0.2s, box-shadow 0.2s, transform 0.2s, border-color 0.2s',
          }}
          onMouseEnter={e => {
            const el = e.currentTarget as HTMLElement;
            el.style.background = 'rgba(129,140,248,0.10)';
            el.style.color = '#c4c9ff';
            el.style.borderColor = 'rgba(129,140,248,0.40)';
            el.style.boxShadow = '0 4px 16px rgba(0,0,0,0.2), 0 0 0 1px rgba(129,140,248,0.25), 0 0 14px rgba(129,140,248,0.22)';
            el.style.transform = 'scale(1.03) translateY(-1px)';
          }}
          onMouseLeave={e => {
            const el = e.currentTarget as HTMLElement;
            el.style.background = 'transparent';
            el.style.color = 'rgba(148,148,180,0.6)';
            el.style.borderColor = 'rgba(129,140,248,0.15)';
            el.style.boxShadow = 'none';
            el.style.transform = '';
          }}
        >
          <Key style={{ width: 12, height: 12 }} />
          API Key
        </button>

        {showKey && (
          <form onSubmit={handleSave} style={{ marginTop: 9 }}>
            <input
              type="password"
              value={keyInput}
              onChange={e => setKeyInput(e.target.value)}
              placeholder="x-api-key"
              style={{
                width: '100%', padding: '7px 10px', borderRadius: 7,
                background: 'rgba(0,0,0,0.35)',
                border: '1px solid rgba(129,140,248,0.25)',
                color: '#f0f0f8', fontSize: 12, marginBottom: 7,
                outline: 'none',
              }}
            />
            <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
              <button type="button" onClick={() => setShowKey(false)} style={{
                fontSize: 11, color: 'var(--text-3)',
                background: 'none', border: 'none', cursor: 'pointer',
              }}>Cancel</button>
              <button type="submit" style={{
                padding: '4px 12px', borderRadius: 6,
                fontSize: 11, fontWeight: 600,
                background: 'linear-gradient(135deg, #6366f1, #818cf8)',
                color: '#fff', border: 'none', cursor: 'pointer',
                boxShadow: '0 2px 8px rgba(99,102,241,0.35)',
              }}>Save</button>
            </div>
          </form>
        )}
      </div>
    </aside>
  );
}
