import React, { useRef, useEffect, useState } from 'react';
import { RecentEvent, VisitorJourneyResponse, api } from '../api';
import { Activity, User, X, Clock, Camera } from 'lucide-react';

const EVENT_COLORS: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  ENTRY:                 { bg: 'rgba(52,211,153,0.08)',  border: 'rgba(52,211,153,0.25)',  text: '#34d399', dot: '#34d399' },
  EXIT:                  { bg: 'rgba(248,113,113,0.08)', border: 'rgba(248,113,113,0.25)', text: '#f87171', dot: '#f87171' },
  ZONE_ENTER:            { bg: 'rgba(96,165,250,0.08)',  border: 'rgba(96,165,250,0.22)',  text: '#60a5fa', dot: '#60a5fa' },
  ZONE_EXIT:             { bg: 'rgba(148,163,184,0.06)', border: 'rgba(148,163,184,0.15)', text: '#94a3b8', dot: '#94a3b8' },
  ZONE_DWELL:            { bg: 'rgba(167,139,250,0.08)', border: 'rgba(167,139,250,0.22)', text: '#a78bfa', dot: '#a78bfa' },
  BILLING_QUEUE_JOIN:    { bg: 'rgba(251,191,36,0.08)',  border: 'rgba(251,191,36,0.25)',  text: '#fbbf24', dot: '#fbbf24' },
  BILLING_QUEUE_ABANDON: { bg: 'rgba(249,115,22,0.08)',  border: 'rgba(249,115,22,0.22)',  text: '#f97316', dot: '#f97316' },
  REENTRY:               { bg: 'rgba(232,121,249,0.08)', border: 'rgba(232,121,249,0.22)', text: '#e879f9', dot: '#e879f9' },
};

function fmt(ts: string) {
  try { return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }); }
  catch { return ts; }
}

function fmtZone(z: string | null) {
  if (!z) return '';
  return z.replace('ZONE_', '').replace(/_/g, ' ').toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase());
}

function fmtMs(ms: number) {
  if (ms <= 0) return '';
  if (ms < 60000) return `${(ms / 1000).toFixed(0)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

// ── Visitor Journey Modal ────────────────────────────────────────────────────
function JourneyModal({ storeId, visitorId, onClose }: {
  storeId: string; visitorId: string; onClose: () => void;
}) {
  const [journey, setJourney] = useState<VisitorJourneyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    api.getVisitorJourney(storeId, visitorId)
      .then(d => { setJourney(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [storeId, visitorId]);

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.72)', backdropFilter: 'blur(8px)',
    }} onClick={onClose}>
      <div style={{
        width: 520, maxHeight: '80vh',
        background: 'rgba(12,12,20,0.96)',
        border: '1px solid rgba(129,140,248,0.25)',
        borderRadius: 16, overflow: 'hidden',
        boxShadow: '0 24px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(129,140,248,0.15)',
        display: 'flex', flexDirection: 'column',
      }} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'rgba(99,102,241,0.08)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <User style={{ width: 16, height: 16, color: '#818cf8' }} />
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f0f0f8' }}>
                Visitor Journey
              </div>
              <div style={{ fontSize: 11, color: 'rgba(129,140,248,0.7)', fontFamily: 'monospace' }}>
                {visitorId}
              </div>
            </div>
          </div>
          <button onClick={onClose} style={{
            background: 'rgba(255,255,255,0.06)', border: 'none',
            borderRadius: 8, padding: 6, cursor: 'pointer', color: '#94a3b8',
          }}>
            <X style={{ width: 14, height: 14 }} />
          </button>
        </div>

        {/* Summary pills */}
        {journey && (
          <div style={{ padding: '12px 20px', display: 'flex', gap: 8, flexWrap: 'wrap', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            {journey.is_staff && (
              <span style={{ fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 20, background: 'rgba(251,191,36,0.12)', border: '1px solid rgba(251,191,36,0.3)', color: '#fbbf24' }}>
                STAFF
              </span>
            )}
            <span style={{ fontSize: 10, fontWeight: 600, padding: '3px 8px', borderRadius: 20, background: 'rgba(96,165,250,0.10)', border: '1px solid rgba(96,165,250,0.22)', color: '#60a5fa' }}>
              {journey.events.length} events
            </span>
            {journey.total_dwell_ms > 0 && (
              <span style={{ fontSize: 10, fontWeight: 600, padding: '3px 8px', borderRadius: 20, background: 'rgba(167,139,250,0.10)', border: '1px solid rgba(167,139,250,0.22)', color: '#a78bfa' }}>
                {fmtMs(journey.total_dwell_ms)} total dwell
              </span>
            )}
            {journey.zones_visited.map(z => (
              <span key={z} style={{ fontSize: 10, fontWeight: 600, padding: '3px 8px', borderRadius: 20, background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.2)', color: '#34d399' }}>
                {fmtZone(z)}
              </span>
            ))}
          </div>
        )}

        {/* Timeline */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '14px 20px' }}>
          {loading && <p style={{ color: '#94a3b8', fontSize: 13, textAlign: 'center', marginTop: 24 }}>Loading journey…</p>}
          {error   && <p style={{ color: '#f87171', fontSize: 13, textAlign: 'center', marginTop: 24 }}>{error}</p>}
          {journey && journey.events.map((ev, i) => {
            const c = EVENT_COLORS[ev.event_type] ?? EVENT_COLORS.ZONE_EXIT;
            return (
              <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 10, alignItems: 'flex-start' }}>
                {/* Timeline spine */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: c.dot, boxShadow: `0 0 8px ${c.dot}70`, marginTop: 3 }} />
                  {i < journey.events.length - 1 && (
                    <div style={{ width: 1, flex: 1, background: 'rgba(255,255,255,0.06)', marginTop: 4, minHeight: 16 }} />
                  )}
                </div>
                {/* Event card */}
                <div style={{
                  flex: 1, padding: '8px 12px', borderRadius: 9, marginBottom: 2,
                  background: c.bg, border: `1px solid ${c.border}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 11.5, fontWeight: 700, color: c.text }}>
                      {ev.event_type.replace(/_/g, ' ')}
                    </span>
                    <span style={{ fontSize: 10, color: 'rgba(148,163,184,0.6)', fontFamily: 'monospace' }}>
                      {fmt(ev.timestamp)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 10, marginTop: 3 }}>
                    {ev.zone_id && (
                      <span style={{ fontSize: 10.5, color: 'rgba(200,210,240,0.7)' }}>{fmtZone(ev.zone_id)}</span>
                    )}
                    {ev.dwell_ms > 0 && (
                      <span style={{ fontSize: 10, color: 'rgba(148,163,184,0.5)', display: 'flex', alignItems: 'center', gap: 3 }}>
                        <Clock style={{ width: 9, height: 9 }} />{fmtMs(ev.dwell_ms)}
                      </span>
                    )}
                    <span style={{ fontSize: 10, color: 'rgba(148,163,184,0.45)', display: 'flex', alignItems: 'center', gap: 3, marginLeft: 'auto' }}>
                      <Camera style={{ width: 9, height: 9 }} />{ev.camera_id}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Main LiveEventsFeed component ────────────────────────────────────────────
interface Props {
  storeId:     string;
  events:      RecentEvent[];
  newEventIds: Set<string>;
  isOffline?:  boolean;
}

export function LiveEventsFeed({ storeId, events, newEventIds, isOffline }: Props) {
  const listRef               = useRef<HTMLDivElement>(null);
  const [journey, setJourney] = useState<string | null>(null);

  // Auto-scroll to top when new events arrive
  useEffect(() => {
    if (newEventIds.size > 0 && listRef.current) {
      listRef.current.scrollTop = 0;
    }
  }, [newEventIds]);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      background: 'rgba(8,8,14,0.55)',
      border: '1px solid rgba(129,140,248,0.14)',
      borderRadius: 14,
      backdropFilter: 'blur(20px)',
      overflow: 'hidden',
      height: '100%',
    }}>
      {/* Header */}
      <div style={{
        padding: '13px 16px 11px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', gap: 9,
        flexShrink: 0,
      }}>
        <Activity style={{ width: 14, height: 14, color: '#818cf8' }} />
        <span style={{ fontSize: 12.5, fontWeight: 700, color: '#e2e4f0', letterSpacing: '-0.01em' }}>
          Live Event Feed
        </span>
        <div style={{
          marginLeft: 'auto',
          fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
          background: 'rgba(52,211,153,0.10)', border: '1px solid rgba(52,211,153,0.25)',
          color: '#34d399',
        }}>
          {events.length} events
        </div>
        <span style={{ fontSize: 10, color: 'rgba(148,163,184,0.45)' }}>Click visitor to see journey</span>
      </div>

      {/* Event list */}
      <div ref={listRef} style={{ flex: 1, overflowY: 'auto', padding: '8px 10px' }}>
        {events.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px 16px', color: 'rgba(148,163,184,0.4)', fontSize: 12 }}>
            {isOffline ? (
              <>
                <div style={{ fontSize: 28, marginBottom: 10 }}>🔌</div>
                <div style={{ fontWeight: 600, color: 'rgba(251,191,36,0.6)', marginBottom: 4 }}>Backend offline</div>
                <div>Start Docker Desktop and run<br />
                  <code style={{ fontFamily: 'monospace', fontSize: 11, color: 'rgba(148,163,184,0.55)' }}>docker compose up -d</code>
                </div>
              </>
            ) : (
              <>
                <div style={{ fontSize: 28, marginBottom: 10 }}>📡</div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>No events yet</div>
                <div>Run the pipeline to populate the feed</div>
              </>
            )}
          </div>
        ) : events.map(ev => {
          const c = EVENT_COLORS[ev.event_type] ?? EVENT_COLORS.ZONE_EXIT;
          const isNew = newEventIds.has(ev.event_id);
          return (
            <div
              key={ev.event_id}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 9px', borderRadius: 8, marginBottom: 3,
                background: isNew ? `${c.bg}` : 'rgba(255,255,255,0.02)',
                border: `1px solid ${isNew ? c.border : 'rgba(255,255,255,0.04)'}`,
                transition: 'background 0.6s, border-color 0.6s',
                animation: isNew ? 'slideIn 0.3s ease' : 'none',
                cursor: 'pointer',
              }}
              onClick={() => setJourney(ev.visitor_id)}
              title={`Click to view ${ev.visitor_id} journey`}
            >
              {/* Type dot */}
              <div style={{
                width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
                background: c.dot,
                boxShadow: isNew ? `0 0 8px ${c.dot}` : 'none',
              }} />

              {/* Event type badge */}
              <span style={{
                fontSize: 9.5, fontWeight: 700, letterSpacing: '0.04em',
                color: c.text, minWidth: 90, flexShrink: 0,
              }}>
                {ev.event_type.replace(/_/g, ' ')}
              </span>

              {/* Visitor ID */}
              <span style={{
                fontSize: 10.5, fontFamily: 'monospace',
                color: 'rgba(200,210,240,0.7)', flex: 1, minWidth: 0,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {ev.visitor_id}
                {ev.is_staff && (
                  <span style={{ marginLeft: 4, fontSize: 8.5, fontWeight: 700, color: '#fbbf24', verticalAlign: 'middle' }}>STAFF</span>
                )}
              </span>

              {/* Zone */}
              {ev.zone_id && (
                <span style={{
                  fontSize: 9.5, color: 'rgba(148,163,184,0.55)',
                  flexShrink: 0,
                }}>
                  {fmtZone(ev.zone_id)}
                </span>
              )}

              {/* Camera */}
              <span style={{
                fontSize: 9, color: 'rgba(100,110,140,0.5)',
                fontFamily: 'monospace', flexShrink: 0,
              }}>
                {ev.camera_id}
              </span>

              {/* Timestamp */}
              <span style={{
                fontSize: 9, color: 'rgba(100,110,140,0.45)',
                fontFamily: 'monospace', flexShrink: 0, minWidth: 64, textAlign: 'right',
              }}>
                {fmt(ev.timestamp)}
              </span>
            </div>
          );
        })}
      </div>

      {/* Journey modal */}
      {journey && (
        <JourneyModal
          storeId={storeId}
          visitorId={journey}
          onClose={() => setJourney(null)}
        />
      )}
    </div>
  );
}
