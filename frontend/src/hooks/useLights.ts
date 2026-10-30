import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { normalizeLocation, sortLights } from "@/lib/lights";
import type { LightState } from "@/types/smart-home";

export type LightConnectionState = "connecting" | "connected" | "reconnecting";

export interface LightCommandState {
  action: "on" | "off";
  phase: "pending" | "error";
  message?: string;
}

interface UseLightsOptions {
  showFeedback: (message: string, isError?: boolean) => void;
}

export const useLights = ({ showFeedback }: UseLightsOptions) => {
  const [lights, setLights] = useState<LightState[]>([]);
  const [lightLocation, setLightLocation] = useState<string>("");
  const [connectionState, setConnectionState] = useState<LightConnectionState>("connecting");
  const [backendOnline, setBackendOnline] = useState(true);
  const [commands, setCommands] = useState<Record<string, LightCommandState>>({});
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number | null>(null);

  const applyLightSnapshot = useCallback((snapshot: LightState[]) => {
    const validLights = snapshot
      .filter((light): light is LightState => Boolean(light && light.location))
      .map((light) => ({
        location: light.location,
        is_on: Boolean(light.is_on),
        device_online: Boolean(light.device_online)
      }));
    const unique = new Map(validLights.map((light) => [normalizeLocation(light.location), light]));
    setLights(sortLights(Array.from(unique.values())));
  }, []);

  const applyLightUpdate = useCallback((light: LightState) => {
    if (!light?.location) return;
    setLights((previous) => {
      const map = new Map(previous.map((item) => [normalizeLocation(item.location), item]));
      map.set(normalizeLocation(light.location), {
        location: light.location,
        is_on: Boolean(light.is_on),
        device_online: Boolean(light.device_online)
      });
      return sortLights(Array.from(map.values()));
    });
  }, []);

  const refreshLights = useCallback(async () => {
    try {
      const data = await apiClient<LightState[]>("/smart-home/lights");
      applyLightSnapshot(data);
      setBackendOnline(true);
    } catch (error) {
      setBackendOnline(false);
      if (error instanceof Error) {
        showFeedback(error.message, true);
      }
    }
  }, [applyLightSnapshot, showFeedback]);

  const handleLightAction = useCallback(
    async (action: "on" | "off", requestedLocation?: string) => {
      const location = (requestedLocation ?? lightLocation).trim();
      if (!location) {
        showFeedback("Vui lòng nhập vị trí đèn", true);
        return;
      }

      const key = normalizeLocation(location);
      setCommands((previous) => ({ ...previous, [key]: { action, phase: "pending" } }));

      try {
        const endpoint = action === "on" ? "/smart-home/lights/on" : "/smart-home/lights/off";
        const result = await apiClient<LightState>(endpoint, {
          method: "POST",
          body: JSON.stringify({ location })
        });
        applyLightUpdate(result);
        setBackendOnline(true);
        setCommands((previous) => {
          const next = { ...previous };
          delete next[key];
          return next;
        });
        showFeedback(`ESP32 đã xác nhận: ${result.location} ${result.is_on ? "đã bật" : "đã tắt"}.`);
        if (!requestedLocation) setLightLocation("");
        void refreshLights();
      } catch (error) {
        if (error instanceof Error) {
          setCommands((previous) => ({
            ...previous,
            [key]: { action, phase: "error", message: error.message }
          }));
          showFeedback(error.message, true);
        }
      }
    },
    [applyLightUpdate, lightLocation, refreshLights, showFeedback]
  );

  useEffect(() => {
    refreshLights();
  }, [refreshLights]);

  useEffect(() => {
    let isMounted = true;

    const connect = () => {
      if (!isMounted || socketRef.current) {
        return;
      }
      try {
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        const socket = new WebSocket(`${protocol}://${window.location.host}/smart-home/lights/stream`);
        socketRef.current = socket;

        socket.addEventListener("open", () => {
          setConnectionState("connected");
          setBackendOnline(true);
          void refreshLights();
        });

        socket.addEventListener("message", (event) => {
          try {
            const payload = JSON.parse(event.data);
            if (payload.type === "snapshot" && Array.isArray(payload.lights)) {
              applyLightSnapshot(payload.lights);
              setCommands({});
            } else if (payload.type === "update" && payload.light) {
              applyLightUpdate(payload.light as LightState);
            } else if (payload.type === "device_status") {
              setLights((previous) =>
                previous.map((light) => ({ ...light, device_online: Boolean(payload.online) }))
              );
            }
          } catch (error) {
            console.error("Không thể phân tích dữ liệu websocket", error);
          }
        });

        socket.addEventListener("close", () => {
          if (socketRef.current === socket) {
            socketRef.current = null;
            if (isMounted) {
              setConnectionState("reconnecting");
              reconnectTimer.current = window.setTimeout(connect, 3000);
            }
          }
        });

        socket.addEventListener("error", () => {
          socket.close();
        });
      } catch (error) {
        setConnectionState("reconnecting");
        console.error("Không thể kết nối websocket", error);
      }
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimer.current) {
        window.clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [applyLightSnapshot, applyLightUpdate, refreshLights]);

  return {
    lights,
    lightLocation,
    setLightLocation,
    handleLightAction,
    applyLightUpdate,
    refreshLights,
    commands,
    connectionState,
    backendOnline
  };
};
