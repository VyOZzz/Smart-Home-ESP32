import type { SVGProps } from "react";

export type HomeIconName =
  | "home" | "sofa" | "bed" | "cooking" | "balcony" | "bulb" | "power"
  | "wifi" | "server" | "camera" | "shield" | "spark" | "music" | "mic"
  | "message" | "image" | "send" | "thermometer" | "droplet" | "leaf"
  | "sun" | "moon" | "clock" | "chevron" | "alert" | "volume";

const paths: Record<HomeIconName, React.ReactNode> = {
  home: <><path d="m3 11 9-8 9 8"/><path d="M5.5 9.5V21h13V9.5"/><path d="M9 21v-7h6v7"/></>,
  sofa: <><path d="M5 12V9a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v3"/><path d="M4 11a2 2 0 0 0-2 2v5h20v-5a2 2 0 0 0-4 0v2H6v-2a2 2 0 0 0-2-2Z"/><path d="M5 18v2m14-2v2"/></>,
  bed: <><path d="M3 5v16M3 15h18v6M7 15V9h10a4 4 0 0 1 4 4v2"/><path d="M7 9H5a2 2 0 0 0-2 2v4"/></>,
  cooking: <><path d="M5 11h14l-1 10H6L5 11Z"/><path d="M8 7c-1-1-1-2 0-3m4 3c-1-1-1-3 0-4m4 4c-1-1-1-2 0-3"/><path d="M3 11h18"/></>,
  balcony: <><path d="M4 21V4h16v17M8 21V9m8 12V9M4 13h16M2 21h20"/></>,
  bulb: <><path d="M9 18h6m-5 3h4"/><path d="M8.4 15.5A7 7 0 1 1 15.6 15.5c-.6.5-.6 1.2-.6 2.5H9c0-1.3 0-2-.6-2.5Z"/></>,
  power: <><path d="M12 2v10"/><path d="M6.3 5.7a8 8 0 1 0 11.4 0"/></>,
  wifi: <><path d="M2.5 8.5a15 15 0 0 1 19 0M5.5 12a10 10 0 0 1 13 0M9 15.5a5 5 0 0 1 6 0"/><circle cx="12" cy="19" r="1" fill="currentColor" stroke="none"/></>,
  server: <><rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 7h.01M7 17h.01M11 7h7M11 17h7"/></>,
  camera: <><rect x="3" y="6" width="18" height="14" rx="3"/><path d="m8 6 1.5-3h5L16 6"/><circle cx="12" cy="13" r="4"/></>,
  shield: <path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/>,
  spark: <path d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3Zm7 13 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z"/>,
  music: <><path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/></>,
  mic: <><rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v4m-4 0h8"/></>,
  message: <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v8Z"/>,
  image: <><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/></>,
  send: <><path d="m22 2-7 20-4-9-9-4 20-7Z"/><path d="M22 2 11 13"/></>,
  thermometer: <><path d="M14 14.8V5a4 4 0 0 0-8 0v9.8a6 6 0 1 0 8 0Z"/><path d="M10 4v12"/></>,
  droplet: <path d="M12 2s7 7.4 7 13a7 7 0 0 1-14 0c0-5.6 7-13 7-13Z"/>,
  leaf: <><path d="M20 3C11 3 5 7 5 13c0 4 3 7 7 7 6 0 8-8 8-17Z"/><path d="M4 21c3-5 7-8 12-11"/></>,
  sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></>,
  moon: <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"/>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  chevron: <path d="m9 18 6-6-6-6"/>,
  alert: <><path d="M10.3 3.5 2.4 18a2 2 0 0 0 1.8 3h15.6a2 2 0 0 0 1.8-3L13.7 3.5a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4m0 4h.01"/></>,
  volume: <><path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="M15 9a4 4 0 0 1 0 6m3-9a8 8 0 0 1 0 12"/></>
};

export function HomeIcon({ name, ...props }: SVGProps<SVGSVGElement> & { name: HomeIconName }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      {paths[name]}
    </svg>
  );
}
