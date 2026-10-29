import { useMemo } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { EnvironmentHistoryPoint, EnvironmentState } from "@/types/smart-home";

const STALE_AFTER_MS = 30_000;
const CHART_WIDTH = 720;
const CHART_HEIGHT = 180;
const CHART_PADDING = 18;

interface EnvironmentCardProps {
  environment: EnvironmentState;
  history: EnvironmentHistoryPoint[];
  isLoading: boolean;
  connectionError: string | null;
}

function observedTime(value: EnvironmentState["observed_at"]): number | null {
  if (value === null) return null;
  const timestamp = typeof value === "number" && value < 10_000_000_000 ? value * 1000 : new Date(value).getTime();
  return Number.isFinite(timestamp) ? timestamp : null;
}

function formatObservedAt(value: EnvironmentState["observed_at"]): string {
  const timestamp = observedTime(value);
  if (timestamp === null) return "Chưa có dữ liệu";
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    day: "2-digit",
    month: "2-digit"
  }).format(timestamp);
}

function formatReading(value: number | null, suffix: string): string {
  return value === null ? "--" : `${value.toFixed(1)}${suffix}`;
}

function createPath(values: Array<number | null>, min: number, max: number): string {
  const range = Math.max(max - min, 1);
  const usableWidth = CHART_WIDTH - CHART_PADDING * 2;
  const usableHeight = CHART_HEIGHT - CHART_PADDING * 2;
  let path = "";

  values.forEach((value, index) => {
    if (value === null) return;
    const x = CHART_PADDING + (values.length === 1 ? usableWidth / 2 : (index / (values.length - 1)) * usableWidth);
    const y = CHART_PADDING + ((max - value) / range) * usableHeight;
    path += `${path ? " L" : "M"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  });
  return path;
}

export function EnvironmentCard({ environment, history, isLoading, connectionError }: EnvironmentCardProps) {
  const timestamp = observedTime(environment.observed_at);
  const isStale = environment.online && timestamp !== null && Date.now() - timestamp > STALE_AFTER_MS;
  const status = !environment.online ? "offline" : isStale ? "stale" : "online";
  const statusLabel = status === "online" ? "Đang online" : status === "stale" ? "Dữ liệu cũ" : "Đang offline";
  const visibleError = environment.last_error || connectionError;

  const chart = useMemo(() => {
    const points = history.slice(-60);
    const temperatures = points.map((point) => point.temperature_c);
    const humidities = points.map((point) => point.humidity_percent);
    const allValues = [...temperatures, ...humidities].filter((value): value is number => value !== null);
    if (allValues.length < 2) return null;
    const min = Math.floor(Math.min(...allValues) - 2);
    const max = Math.ceil(Math.max(...allValues) + 2);
    return {
      temperaturePath: createPath(temperatures, min, max),
      humidityPath: createPath(humidities, min, max),
      first: formatObservedAt(points[0]?.observed_at ?? null),
      last: formatObservedAt(points.at(-1)?.observed_at ?? null),
      min,
      max
    };
  }, [history]);

  return (
    <Card>
      <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between sm:space-y-0">
        <div className="space-y-1.5">
          <CardTitle>Môi trường trong nhà</CardTitle>
          <CardDescription>Nhiệt độ và độ ẩm Phòng 1 từ ESP32 + DHT11 qua MQTT.</CardDescription>
        </div>
        <div
          className={cn(
            "inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold",
            status === "online" && "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
            status === "stale" && "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
            status === "offline" && "border-slate-500/30 bg-slate-500/10 text-slate-600 dark:text-slate-300"
          )}
          role="status"
        >
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              status === "online" && "bg-emerald-500",
              status === "stale" && "bg-amber-500",
              status === "offline" && "bg-slate-400"
            )}
            aria-hidden="true"
          />
          {isLoading ? "Đang tải…" : statusLabel}
        </div>
      </CardHeader>

      <CardContent className="grid gap-6 lg:grid-cols-[minmax(260px,0.75fr)_minmax(0,1.6fr)]">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-2xl border border-orange-500/20 bg-gradient-to-br from-orange-500/10 to-amber-500/5 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">Nhiệt độ</p>
              <p className="mt-2 text-3xl font-bold tabular-nums text-orange-600 dark:text-orange-300">
                {formatReading(environment.temperature_c, "°C")}
              </p>
            </div>
            <div className="rounded-2xl border border-sky-500/20 bg-gradient-to-br from-sky-500/10 to-cyan-500/5 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">Độ ẩm</p>
              <p className="mt-2 text-3xl font-bold tabular-nums text-sky-600 dark:text-sky-300">
                {formatReading(environment.humidity_percent, "%")}
              </p>
            </div>
          </div>

          <dl className="space-y-2 rounded-xl bg-muted/50 p-4 text-sm">
            <div className="flex items-center justify-between gap-4">
              <dt className="text-muted-foreground">Thiết bị</dt>
              <dd className="truncate font-medium" title={environment.device_id}>{environment.device_id}</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-muted-foreground">Cập nhật cuối</dt>
              <dd className="font-medium tabular-nums">{formatObservedAt(environment.observed_at)}</dd>
            </div>
          </dl>

          {visibleError && (
            <p className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive" role="alert">
              {visibleError}
            </p>
          )}
        </div>

        <div className="min-w-0 rounded-2xl border bg-muted/20 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold">Lịch sử gần đây</p>
            <div className="flex gap-4 text-xs text-muted-foreground" aria-hidden="true">
              <span className="flex items-center gap-1.5"><span className="h-0.5 w-4 bg-orange-500" />Nhiệt độ</span>
              <span className="flex items-center gap-1.5"><span className="h-0.5 w-4 bg-sky-500" />Độ ẩm</span>
            </div>
          </div>

          {chart ? (
            <figure>
              <svg
                className="h-44 w-full overflow-visible"
                viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
                role="img"
                aria-labelledby="environment-chart-title environment-chart-description"
                preserveAspectRatio="none"
              >
                <title id="environment-chart-title">Biểu đồ nhiệt độ và độ ẩm gần đây</title>
                <desc id="environment-chart-description">
                  {history.length} mẫu. Nhiệt độ mới nhất {formatReading(environment.temperature_c, " độ C")}, độ ẩm mới nhất {formatReading(environment.humidity_percent, " phần trăm")}.
                </desc>
                {[0, 0.5, 1].map((ratio) => (
                  <line
                    key={ratio}
                    x1={CHART_PADDING}
                    x2={CHART_WIDTH - CHART_PADDING}
                    y1={CHART_PADDING + ratio * (CHART_HEIGHT - CHART_PADDING * 2)}
                    y2={CHART_PADDING + ratio * (CHART_HEIGHT - CHART_PADDING * 2)}
                    stroke="currentColor"
                    className="text-border"
                    vectorEffect="non-scaling-stroke"
                  />
                ))}
                <path d={chart.temperaturePath} fill="none" stroke="#f97316" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
                <path d={chart.humidityPath} fill="none" stroke="#0ea5e9" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
              </svg>
              <figcaption className="mt-2 flex justify-between gap-3 text-xs text-muted-foreground">
                <span>{chart.first}</span>
                <span>{chart.last}</span>
              </figcaption>
              <span className="sr-only">Thang dữ liệu từ {chart.min} đến {chart.max}.</span>
            </figure>
          ) : (
            <div className="flex h-44 items-center justify-center rounded-xl border border-dashed text-center text-sm text-muted-foreground">
              Chưa đủ dữ liệu để vẽ biểu đồ
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
