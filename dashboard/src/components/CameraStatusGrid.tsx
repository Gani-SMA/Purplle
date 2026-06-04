import React from 'react';
import { CameraStatus } from '../api';
import { Camera, Wifi, WifiOff, HelpCircle } from 'lucide-react';

const STATUS_STYLE: Record<string, { color: string; bg: string; border: string; label: string; icon: React.ElementType }> = {
  live:    { color: '#34d399', bg: 'rgba(52,211,153,0.10)',  border: 'rgba(52,211,153,0.25)',  label: 'Live',    icon: Wifi },
  stale:   { color: '#fbbf24', bg: 'rgba(251,191,36,0.10)',  border: 'rgba(251,191,36,0.25)',  label: 'Stale',   icon: WifiOff },
  unknown: { color: '#94a3b8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.18)', label: 'Unknown', icon: HelpCircle },
};

function fmtLag(sec: number | null): string {
  if (sec === null) return '—';
  if (sec < 60)   return `${Math.round(sec)}s ago`;
  if (sec < 3600) return `${(sec / 60).toFixed(1)}m ago`;
  return `${(sec / 3600).toFixed(1)}h ago`;
}

function fmtTs(ts: string | null): string {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch { return ts; }
}

interface Props {
  cameras: CameraStatus[];
}

export function CameraStatusGrid({ cameras }: Props) {
  // If no cameras from Redis yet, show placeholder tiles for known cameras
  const displayCams: CameraStatus[] = cameras.length > 0 ? cameras : [
    'CAM001', 'CAM002', 'CAM003', 'CAM004', 'CAM005',
  ].map(id => ({
    camera_id: id, last_seen_ts: null,
    event_count_today: 0, lag_seconds: null, status: 'unknown' as const,
  }));

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
        <Camera style={{ width: 14, height: 14, color: '#818cf8' }} />
        <span style={{ fontSize: 12.5, fontWeight: 700, color: '#e2e4f0', letterSpacing: '-0.01em' }}>
          Camera Status
        </span>
        <div style={{
          marginLeft: 'auto', fontSize: 10, color: 'rgba(148,163,184,0.4)',
        }}>
          {cameras.filter(c => c.status === 'live').length}/{displayCams.length} live
        </div>
      </div>

      {/* Camera grid */}
      <div style={{
        padding: '12px 14px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
        gap: 10,
      }}>
        {displayCams.map(cam => {
          const s = STATUS_STYLE[cam.status] ?? STATUS_STYLE.unknown;
          const StatusIcon = s.icon;
          return (
            <div key={cam.camera_id} style={{
              padding: '11px 13px', borderRadius: 10,
              background: s.bg,
              border: `1px solid ${s.border}`,
              transition: 'transform 0.2s, box-shadow 0.2s',
              cursor: 'default',
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
              (e.currentTarget as HTMLElement).style.boxShadow = `0 8px 24px rgba(0,0,0,0.3), 0 0 0 1px ${s.border}`;
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.transform = '';
              (e.currentTarget as HTMLElement).style.boxShadow = '';
            }}>
              {/* Top row: camera id + status */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: '#e2e4f0', fontFamily: 'monospace' }}>
                  {cam.camera_id}
                </span>
                <span style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  fontSize: 9.5, fontWeight: 700,
                  padding: '2px 7px', borderRadius: 20,
                  background: `${s.color}18`, border: `1px solid ${s.color}40`,
                  color: s.color,
                }}>
                  {cam.status === 'live' && (
                    <span style={{
                      width: 5, height: 5, borderRadius: '50%',
                      background: s.color, boxShadow: `0 0 6px ${s.color}`,
                      animation: 'pulse 1.8s ease-in-out infinite',
                      display: 'inline-block',
                    }} />
                  )}
                  <StatusIcon style={{ width: 9, height: 9 }} />
                  {s.label}
                </span>
              </div>

              {/* Event count */}
              <div style={{ fontSize: 22, fontWeight: 800, color: s.color, lineHeight: 1, marginBottom: 4 }}>
                {cam.event_count_today.toLocaleString()}
              </div>
              <div style={{ fontSize: 9.5, color: 'rgba(148,163,184,0.5)', marginBottom: 6 }}>events today</div>

              {/* Last seen */}
              <div style={{ fontSize: 10, color: 'rgba(148,163,184,0.5)', display: 'flex', justifyContent: 'space-between' }}>
                <span>Last seen</span>
                <span style={{ fontFamily: 'monospace', color: 'rgba(200,210,240,0.55)' }}>
                  {cam.lag_seconds !== null ? fmtLag(cam.lag_seconds) : fmtTs(cam.last_seen_ts)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
