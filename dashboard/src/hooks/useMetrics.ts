import { useState, useEffect, useCallback } from 'react';
import { api, StoreMetric, FunnelResponse, HeatmapResponse, AnomalyResponse } from '../api';
import { useWebSocket } from './useWebSocket';

export function useMetrics(storeId: string) {
  const [metrics, setMetrics] = useState<StoreMetric | null>(null);
  const [funnel, setFunnel] = useState<FunnelResponse | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyResponse | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [pulseMetrics, setPulseMetrics] = useState<Record<string, boolean>>({});

  const fetchData = useCallback(async (isWebSocketTrigger = false) => {
    try {
      if (!isWebSocketTrigger) {
        setLoading(true);
      }
      setError(null);

      const [metricsData, funnelData, heatmapData, anomaliesData] = await Promise.all([
        api.getMetrics(storeId),
        api.getFunnel(storeId),
        api.getHeatmap(storeId),
        api.getAnomalies(storeId),
      ]);

      if (isWebSocketTrigger && metrics) {
        // Find which metrics increased to trigger pulse animations
        const newPulse: Record<string, boolean> = {};
        if (metricsData.unique_visitors > metrics.unique_visitors) newPulse.unique_visitors = true;
        if (metricsData.conversion_rate > metrics.conversion_rate) newPulse.conversion_rate = true;
        if (metricsData.current_queue_size !== metrics.current_queue_size) newPulse.current_queue_size = true;
        
        setPulseMetrics(newPulse);
        // Clear pulse after 1.5 seconds
        setTimeout(() => setPulseMetrics({}), 1500);
      }

      setMetrics(metricsData);
      setFunnel(funnelData);
      setHeatmap(heatmapData);
      setAnomalies(anomaliesData);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Failed to fetch store data:', err);
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }, [storeId, metrics]);

  // Initial load
  useEffect(() => {
    fetchData(false);
  }, [storeId]);

  // Listen for WebSocket live updates
  const { isConnected, wsEventCount } = useWebSocket(
    storeId,
    useCallback(() => {
      console.log(`WebSocket event triggered refresh for store: ${storeId}`);
      fetchData(true);
    }, [fetchData, storeId])
  );

  return {
    metrics,
    funnel,
    heatmap,
    anomalies,
    loading,
    error,
    isConnected,
    wsEventCount,
    lastUpdated,
    pulseMetrics,
    refetch: () => fetchData(false),
  };
}
