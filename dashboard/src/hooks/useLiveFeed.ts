import { useState, useEffect, useCallback } from 'react';
import { api, RecentEvent, CameraStatus, PosSummaryResponse } from '../api';

export function useLiveFeed(storeId: string, wsTriggered: number) {
  const [recentEvents, setRecentEvents] = useState<RecentEvent[]>([]);
  const [cameraStatus, setCameraStatus] = useState<CameraStatus[]>([]);
  const [posSummary, setPosSummary]     = useState<PosSummaryResponse | null>(null);
  const [newEventIds, setNewEventIds]   = useState<Set<string>>(new Set());
  const [feedLoading, setFeedLoading]   = useState(true);
  const [isOffline, setIsOffline]       = useState(false);

  const fetchFeed = useCallback(async (highlight = false) => {
    try {
      const [eventsRes, camRes, posRes] = await Promise.allSettled([
        api.getRecentEvents(storeId, 60),
        api.getCameraStatus(storeId),
        api.getPosSummary(storeId),
      ]);

      const allFailed =
        eventsRes.status === 'rejected' &&
        camRes.status    === 'rejected' &&
        posRes.status    === 'rejected';
      setIsOffline(allFailed);

      if (eventsRes.status === 'fulfilled') {
        const incoming = eventsRes.value.events;
        if (highlight) {
          // Identify truly new event IDs to flash
          setRecentEvents(prev => {
            const prevIds = new Set(prev.map(e => e.event_id));
            const ids = new Set(
              incoming.filter(e => !prevIds.has(e.event_id)).map(e => e.event_id)
            );
            if (ids.size > 0) {
              setNewEventIds(ids);
              setTimeout(() => setNewEventIds(new Set()), 1800);
            }
            return incoming;
          });
        } else {
          setRecentEvents(incoming);
        }
      }

      if (camRes.status === 'fulfilled') {
        setCameraStatus(camRes.value.cameras);
      }

      if (posRes.status === 'fulfilled') {
        setPosSummary(posRes.value);
      }
    } catch (err) {
      console.error('useLiveFeed fetch error:', err);
    } finally {
      setFeedLoading(false);
    }
  }, [storeId]);

  // Initial load
  useEffect(() => {
    setFeedLoading(true);
    fetchFeed(false);
  }, [storeId]);

  // Re-fetch when WebSocket fires (wsTriggered increments)
  useEffect(() => {
    if (wsTriggered > 0) fetchFeed(true);
  }, [wsTriggered]);

  return { recentEvents, cameraStatus, posSummary, newEventIds, feedLoading, isOffline };
}
