// API Client for Purplle Store Intelligence API

const API_BASE = '/api';

export interface StoreMetric {
  unique_visitors: number;
  conversion_rate: number;
  avg_dwell_time_seconds: number;
  current_queue_size: number;
  cart_abandonment_rate: number;
}

export interface FunnelStage {
  stage: string;
  count: number;
  percentage: number;
}

export interface FunnelResponse {
  store_id: string;
  funnel: FunnelStage[];
}

export interface ZoneHeatmapItem {
  zone_name: string;
  checkins: number;
  normalized_intensity: number;
}

export interface HeatmapResponse {
  store_id: string;
  zones: ZoneHeatmapItem[];
  data_confidence: number;
}

export interface AnomalyItem {
  type: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
  timestamp: string;
}

export interface AnomalyResponse {
  store_id: string;
  anomalies: AnomalyItem[];
}

export interface StoreHealthItem {
  store_id: string;
  last_event_ts: string | null;
  lag_minutes: number | null;
  status: 'live' | 'stale';
}

export interface HealthResponse {
  status: 'healthy' | 'stale';
  stores: StoreHealthItem[];
}

// Get stored API key or default to test_key_1
export function getApiKey(): string {
  return localStorage.getItem('purplle_api_key') || 'test_key_1';
}

export function setApiKey(key: string) {
  localStorage.setItem('purplle_api_key', key);
}

// Backend API response shapes
interface BackendZoneDwell {
  zone_id: string;
  avg_dwell_ms: number;
}

interface BackendMetricsResponse {
  store_id: string;
  unique_visitors: number;
  conversion_rate: number;
  avg_dwell_by_zone: BackendZoneDwell[];
  queue_depth: number;
  abandonment_rate: number;
}

interface BackendFunnelStage {
  stage: string;
  count: number;
  drop_off_pct: number;
}

interface BackendFunnelResponse {
  store_id: string;
  stages: BackendFunnelStage[];
}

interface BackendHeatmapZone {
  zone_id: string;
  visit_count: number;
  avg_dwell_ms: number;
  normalised_score: number;
}

interface BackendHeatmapResponse {
  store_id: string;
  zones: BackendHeatmapZone[];
  data_confidence: boolean;
}

interface BackendAnomalyItem {
  anomaly_type: string;
  severity: 'INFO' | 'WARN' | 'CRITICAL';
  message: string;
  suggested_action: string;
  detected_at: string;
}

interface BackendAnomalyResponse {
  store_id: string;
  anomalies: BackendAnomalyItem[];
}

async function request<T>(path: string): Promise<T> {
  const headers: HeadersInit = {
    'x-api-key': getApiKey(),
    'Content-Type': 'application/json',
  };

  const response = await fetch(`${API_BASE}${path}`, { headers });
  
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Unauthorized API Key');
    }
    throw new Error(`API Error: ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getMetrics: async (storeId: string): Promise<StoreMetric> => {
    const data = await request<BackendMetricsResponse>(`/stores/${storeId}/metrics`);
    const zones = data.avg_dwell_by_zone || [];
    const avgDwellSeconds = zones.length > 0
      ? (zones.reduce((sum, zone) => sum + zone.avg_dwell_ms, 0) / zones.length) / 1000
      : 0;
    return {
      unique_visitors: data.unique_visitors,
      conversion_rate: data.conversion_rate,
      avg_dwell_time_seconds: avgDwellSeconds,
      current_queue_size: data.queue_depth,
      cart_abandonment_rate: data.abandonment_rate,
    };
  },
  getFunnel: async (storeId: string): Promise<FunnelResponse> => {
    const data = await request<BackendFunnelResponse>(`/stores/${storeId}/funnel`);
    const entryCount = data.stages[0]?.count || 0;
    const mappedStages = data.stages.map(stage => {
      let stageName = stage.stage;
      if (stageName === 'entry') stageName = 'stage_1_entry';
      else if (stageName === 'zone_visit') stageName = 'stage_2_browse';
      else if (stageName === 'billing_queue') stageName = 'stage_3_checkout';
      else if (stageName === 'purchase') stageName = 'stage_4_purchase';
      
      return {
        stage: stageName,
        count: stage.count,
        percentage: entryCount > 0 ? stage.count / entryCount : 0
      };
    });
    return {
      store_id: data.store_id,
      funnel: mappedStages,
    };
  },
  getHeatmap: async (storeId: string): Promise<HeatmapResponse> => {
    const data = await request<BackendHeatmapResponse>(`/stores/${storeId}/heatmap`);
    const mappedZones = (data.zones || []).map(z => ({
      zone_name: z.zone_id,
      checkins: z.visit_count,
      normalized_intensity: z.normalised_score,
    }));
    return {
      store_id: data.store_id,
      zones: mappedZones,
      data_confidence: data.data_confidence ? 100 : 50,
    };
  },
  getAnomalies: async (storeId: string): Promise<AnomalyResponse> => {
    const data = await request<BackendAnomalyResponse>(`/stores/${storeId}/anomalies`);
    const severityMap: Record<string, 'low' | 'medium' | 'high'> = {
      INFO: 'low',
      WARN: 'medium',
      CRITICAL: 'high',
    };
    const mappedAnomalies = (data.anomalies || []).map(a => ({
      type: a.anomaly_type,
      severity: severityMap[a.severity] || 'low',
      message: a.message,
      timestamp: a.detected_at,
    }));
    return {
      store_id: data.store_id,
      anomalies: mappedAnomalies,
    };
  },
  getHealth: () => request<HealthResponse>('/health'),
};
