import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { MetricsCard } from './components/MetricsCard';
import { FunnelChart } from './components/FunnelChart';
import { ZoneHeatmap } from './components/ZoneHeatmap';
import { AnomalyPanel } from './components/AnomalyPanel';
import { HealthTable } from './components/HealthTable';
import { useMetrics } from './hooks/useMetrics';
import { api, HealthResponse } from './api';
import { Users, Clock, TrendingUp, ShoppingBag, RefreshCw, Wifi, WifiOff, Sun, Moon } from 'lucide-react';
import { SpiralAnimation } from './components/ui/spiral-animation';

function useTheme() {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('si_theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  });
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('si_theme', theme);
  }, [theme]);
  const toggle = () => setTheme(t => t === 'dark' ? 'light' : 'dark');
  return { theme, toggle };
}

const STORE_META: Record<string, { name: string; city: string; accent: string; accents: string[] }> = {
  STR001: {
    name: 'Metro Mall',  city: 'Mumbai',
    accent: '#818cf8',
    accents: ['#818cf8', '#34d399', '#fbbf24', '#38bdf8'],
  },
  STR002: {
    name: 'Cyber City',  city: 'Delhi',
    accent: '#34d399',
    accents: ['#34d399', '#818cf8', '#fbbf24', '#f87171'],
  },
  STR003: {
    name: 'Koramangala', city: 'Bengaluru',
    accent: '#fbbf24',
    accents: ['#fbbf24', '#34d399', '#818cf8', '#c084fc'],
  },
};

export default function App() {
  const [currentStoreId, setCurrentStoreId] = useState('STR001');
  const [health, setHealth]           = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [apiHealthStatus, setApiHealthStatus] = useState<'healthy' | 'stale' | 'offline'>('healthy');

  const { theme, toggle: toggleTheme } = useTheme();

  const {
    metrics, funnel, heatmap, anomalies,
    loading, error, isConnected, lastUpdated, pulseMetrics, refetch,
  } = useMetrics(currentStoreId);

  const fetchHealth = async () => {
    try {
      setHealthLoading(true);
      const d = await api.getHealth();
      setHealth(d);
      setApiHealthStatus(d.status === 'healthy' ? 'healthy' : 'stale');
    } catch {
      setApiHealthStatus('offline');
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const t = setInterval(fetchHealth, 30_000);
    return () => clearInterval(t);
  }, []);

  const meta    = STORE_META[currentStoreId] ?? STORE_META.STR001;
  const accents = meta.accents;

  return (
    <div style={{
      display: 'flex', height: '100vh',
      background: theme === 'dark' ? 'rgb(6,6,10)' : 'var(--surface-0)',
      overflow: 'hidden', position: 'relative',
    }}>
      {/* ── GSAP Spiral (dark only) ── */}
      {theme === 'dark' && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none' }}>
          <SpiralAnimation />
        </div>
      )}

      {/* ── Radial vignette ── */}
      {theme === 'dark' && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 1, pointerEvents: 'none',
          background: 'radial-gradient(ellipse at center, transparent 35%, rgba(3,3,8,0.60) 100%)',
        }} />
      )}

      <Sidebar
        currentStoreId={currentStoreId}
        onStoreChange={setCurrentStoreId}
        apiHealth={apiHealthStatus}
        onRefreshHealth={fetchHealth}
      />

      <main style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        overflow: 'hidden', position: 'relative', zIndex: 2,
      }}>
        {/* ═══ Header ═══ */}
        <header style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 28px', height: 54,
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          background: 'rgba(8,8,14,0.50)',
          backdropFilter: 'blur(24px) saturate(160%)',
          WebkitBackdropFilter: 'blur(24px) saturate(160%)',
          flexShrink: 0,
        }}>
          {/* Store title */}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{
              fontWeight: 800, fontSize: 15, color: 'var(--text-1)',
              letterSpacing: '-0.02em',
            }}>
              {meta.name}
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-3)', fontWeight: 400 }}>
              {meta.city}
            </span>
            <span style={{
              fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
              padding: '2px 8px', borderRadius: 5,
              background: `${meta.accent}18`,
              border: `1px solid ${meta.accent}35`,
              color: meta.accent,
            }}>
              {currentStoreId}
            </span>
          </div>

          {/* Right controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {/* Live indicator */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: 12, fontWeight: 700,
              padding: '4px 10px', borderRadius: 20,
              background: isConnected ? 'rgba(52,211,153,0.10)' : 'rgba(248,113,113,0.10)',
              border: `1px solid ${isConnected ? 'rgba(52,211,153,0.28)' : 'rgba(248,113,113,0.28)'}`,
              color: isConnected ? '#34d399' : '#f87171',
              transition: 'all 0.3s',
            }}>
              {isConnected
                ? <Wifi    style={{ width: 12, height: 12 }} />
                : <WifiOff style={{ width: 12, height: 12 }} />}
              <span>{isConnected ? 'Live' : 'Offline'}</span>
              {isConnected && (
                <span style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: '#34d399',
                  boxShadow: '0 0 8px #34d399',
                  animation: 'pulse 1.8s ease-in-out infinite',
                }} />
              )}
            </div>

            <div style={{ width: 1, height: 20, background: 'rgba(255,255,255,0.08)' }} />

            {/* Theme toggle */}
            <button
              id="theme-toggle"
              className="icon-btn"
              onClick={toggleTheme}
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark'
                ? <Sun  style={{ width: 13, height: 13 }} />
                : <Moon style={{ width: 13, height: 13 }} />}
            </button>

            {/* Refresh */}
            <button
              id="refresh-btn"
              className="icon-btn"
              onClick={() => { refetch(); fetchHealth(); }}
              title="Refresh data"
            >
              <RefreshCw style={{
                width: 13, height: 13,
                animation: loading ? 'spin 0.8s linear infinite' : 'none',
                transition: 'animation 0.1s',
              }} />
            </button>
          </div>
        </header>

        {/* ═══ Scrollable Content ═══ */}
        <div style={{
          flex: 1, overflowY: 'auto',
          padding: '22px 26px',
          display: 'flex', flexDirection: 'column', gap: 18,
        }}>
          {/* Error banner */}
          {error && (
            <div style={{
              padding: '10px 16px', borderRadius: 10,
              background: 'rgba(248,113,113,0.10)',
              border: '1px solid rgba(248,113,113,0.28)',
              backdropFilter: 'blur(12px)',
              color: '#fca5a5', fontSize: 13,
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              boxShadow: '0 0 20px rgba(248,113,113,0.12)',
            }}>
              <span>{error}</span>
              <button
                onClick={refetch}
                style={{
                  padding: '4px 12px', borderRadius: 7, border: 'none',
                  background: 'rgba(248,113,113,0.20)', color: '#fca5a5',
                  fontSize: 12, cursor: 'pointer', fontWeight: 700,
                  transition: 'background 0.15s, transform 0.15s',
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.background = 'rgba(248,113,113,0.35)';
                  (e.currentTarget as HTMLElement).style.transform = 'scale(1.05)';
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.background = 'rgba(248,113,113,0.20)';
                  (e.currentTarget as HTMLElement).style.transform = '';
                }}
              >
                Retry
              </button>
            </div>
          )}

          {/* ── KPI row ── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
            <MetricsCard
              title="Unique Visitors"
              value={metrics?.unique_visitors ?? '—'}
              sub="today"
              icon={Users}
              accent={accents[0]}
              pulse={pulseMetrics.unique_visitors}
            />
            <MetricsCard
              title="Conversion"
              value={metrics ? `${Math.round(metrics.conversion_rate * 100)}%` : '—'}
              sub="sessions → purchase"
              icon={TrendingUp}
              accent={accents[1]}
              pulse={pulseMetrics.conversion_rate}
            />
            <MetricsCard
              title="Avg Dwell"
              value={metrics ? `${Math.round(metrics.avg_dwell_time_seconds)}s` : '—'}
              sub="per visit"
              icon={Clock}
              accent={accents[2]}
            />
            <MetricsCard
              title="Queue Depth"
              value={metrics?.current_queue_size ?? '—'}
              sub="billing counter"
              icon={ShoppingBag}
              accent={accents[3]}
              pulse={pulseMetrics.current_queue_size}
            />
          </div>

          {/* ── Charts row ── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <FunnelChart data={funnel} />
            <ZoneHeatmap data={heatmap} />
          </div>

          {/* ── Bottom row ── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 14 }}>
            <AnomalyPanel data={anomalies} />
            <HealthTable health={health} loading={healthLoading} />
          </div>
        </div>

        {/* ═══ Footer ═══ */}
        <footer style={{
          height: 36, padding: '0 28px',
          borderTop: '1px solid rgba(255,255,255,0.06)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          fontSize: 11, color: 'var(--text-3)',
          background: 'rgba(8,8,14,0.50)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          flexShrink: 0,
        }}>
          <span style={{ fontWeight: 500 }}>Purplle Store Intelligence</span>
          <span>Last updated {lastUpdated.toLocaleTimeString()}</span>
        </footer>
      </main>
    </div>
  );
}
