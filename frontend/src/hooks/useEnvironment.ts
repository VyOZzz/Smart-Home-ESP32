import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "@/lib/api-client";
import type { EnvironmentHistoryPoint, EnvironmentState } from "@/types/smart-home";

const RECONNECT_DELAY_MS = 3_000;
const REFRESH_INTERVAL_MS = 15_000;
const HISTORY_LIMIT = 120;

const EMPTY_ENVIRONMENT: EnvironmentState = {
  device_id: "esp32-sensor",
  online: false,
  temperature_c: null,
  humidity_percent: null,
  observed_at: null,
  last_error: null
};

function finiteNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function observationTimestamp(value: string | number): number {
  if (typeof value === "number") return value < 10_000_000_000 ? value * 1000 : value;
  const parsed = new Date(value).getTime();
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalizeEnvironment(value: unknown, fallback = EMPTY_ENVIRONMENT): EnvironmentState {
  if (!value || typeof value !== "object") return fallback;
  const candidate = value as Partial<EnvironmentState>;
  return {
    device_id:
      typeof candidate.device_id === "string" && candidate.device_id.trim()
        ? candidate.device_id
        : fallback.device_id,
    online: typeof candidate.online === "boolean" ? candidate.online : fallback.online,
    temperature_c: finiteNumber(candidate.temperature_c),
    humidity_percent: finiteNumber(candidate.humidity_percent),
    observed_at:
      typeof candidate.observed_at === "string" || typeof candidate.observed_at === "number"
        ? candidate.observed_at
        : fallback.observed_at,
    last_error:
      typeof candidate.last_error === "string" && candidate.last_error.trim()
        ? candidate.last_error
        : null
  };
}

function normalizeHistory(value: unknown): EnvironmentHistoryPoint[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item): EnvironmentHistoryPoint | null => {
      if (!item || typeof item !== "object") return null;
      const point = item as Partial<EnvironmentHistoryPoint>;
      if (typeof point.observed_at !== "string" && typeof point.observed_at !== "number") return null;
      const temperature = finiteNumber(point.temperature_c);
      const humidity = finiteNumber(point.humidity_percent);
      if (temperature === null && humidity === null) return null;
      return {
        temperature_c: temperature,
        humidity_percent: humidity,
        observed_at: point.observed_at
      };
    })
    .filter((point): point is EnvironmentHistoryPoint => point !== null)
    .sort((left, right) => observationTimestamp(left.observed_at) - observationTimestamp(right.observed_at));
}

function sameObservation(left: string | number, right: string | number): boolean {
  return String(left) === String(right);
}

export function useEnvironment() {
  const [environment, setEnvironment] = useState<EnvironmentState>(EMPTY_ENVIRONMENT);
  const [history, setHistory] = useState<EnvironmentHistoryPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [currentResult, historyResult] = await Promise.allSettled([
        apiClient<EnvironmentState>("/smart-home/environment"),
        apiClient<EnvironmentHistoryPoint[]>(`/smart-home/environment/history?limit=${HISTORY_LIMIT}`)
      ]);

      if (currentResult.status === "fulfilled") {
        setEnvironment((previous) => normalizeEnvironment(currentResult.value, previous));
        setConnectionError(null);
      } else {
        setConnectionError(
          currentResult.reason instanceof Error
            ? currentResult.reason.message
            : "Không thể tải trạng thái cảm biến"
        );
      }

      if (historyResult.status === "fulfilled") {
        setHistory(normalizeHistory(historyResult.value));
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(), REFRESH_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    let isMounted = true;

    const connect = () => {
      if (!isMounted || socketRef.current) return;
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${protocol}://${window.location.host}/smart-home/environment/updates`);
      socketRef.current = socket;

      socket.addEventListener("open", () => setConnectionError(null));
      socket.addEventListener("message", (event) => {
        try {
          const payload = JSON.parse(event.data) as Record<string, unknown>;
          const candidate = payload.type === "environment_update" ? payload.environment : payload;

          if (payload.type === "device_status") {
            setEnvironment((previous) => ({
              ...previous,
              online: Boolean(payload.online),
              last_error:
                typeof payload.last_error === "string" && payload.last_error.trim()
                  ? payload.last_error
                  : previous.last_error
            }));
            return;
          }

          setEnvironment((previous) => normalizeEnvironment(candidate, previous));
          const observation = normalizeEnvironment(candidate);
          if (observation.observed_at !== null) {
            const point: EnvironmentHistoryPoint = {
              temperature_c: observation.temperature_c,
              humidity_percent: observation.humidity_percent,
              observed_at: observation.observed_at
            };
            setHistory((items) =>
              items.some((item) => sameObservation(item.observed_at, point.observed_at))
                ? items
                : normalizeHistory([...items, point]).slice(-HISTORY_LIMIT)
            );
          }
        } catch (error) {
          console.error("Không thể phân tích dữ liệu cảm biến", error);
        }
      });

      socket.addEventListener("close", () => {
        if (socketRef.current !== socket) return;
        socketRef.current = null;
        if (isMounted) {
          setConnectionError("Mất kết nối cập nhật trực tiếp, đang kết nối lại…");
          reconnectTimerRef.current = window.setTimeout(connect, RECONNECT_DELAY_MS);
        }
      });
      socket.addEventListener("error", () => socket.close());
    };

    connect();
    return () => {
      isMounted = false;
      if (reconnectTimerRef.current !== null) window.clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);

  return { environment, history, isLoading, connectionError, refresh };
}
