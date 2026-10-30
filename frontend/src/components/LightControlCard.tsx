import { HomeIcon, type HomeIconName } from "@/components/icons/HomeIcons";
import type { LightCommandState } from "@/hooks/useLights";
import { normalizeLocation } from "@/lib/lights";
import { cn } from "@/lib/utils";
import type { LightState } from "@/types/smart-home";

interface LightControlCardProps {
  lights: LightState[];
  commands: Record<string, LightCommandState>;
  onLightAction: (action: "on" | "off", location?: string) => void;
}

const rooms: Array<{ id: string; name: string; gpio: number; icon: HomeIconName; caption: string; className: string }> = [
  { id: "living-room", name: "Phòng khách", gpio: 16, icon: "sofa", caption: "Không gian sinh hoạt", className: "room-space--living" },
  { id: "bedroom", name: "Phòng ngủ", gpio: 17, icon: "bed", caption: "Ánh sáng nghỉ ngơi", className: "room-space--bedroom" },
  { id: "kitchen", name: "Nhà bếp", gpio: 18, icon: "cooking", caption: "Khu vực nấu ăn", className: "room-space--kitchen" },
  { id: "balcony", name: "Ban công", gpio: 19, icon: "balcony", caption: "Khoảng thở ngoài trời", className: "room-space--balcony" }
];

function findLight(lights: LightState[], id: string, name: string) {
  return lights.find((light) => {
    const location = normalizeLocation(light.location);
    return location === id || location === normalizeLocation(name);
  });
}

export function LightControlCard({ lights, commands, onLightAction }: LightControlCardProps) {
  return (
    <section id="rooms" className="home-section" aria-labelledby="rooms-title">
      <div className="section-heading">
        <div><p className="eyebrow">Bốn không gian · một nhịp sống</p><h2 id="rooms-title">Ánh sáng trong nhà</h2></div>
        <p className="section-note">Trạng thái chỉ đổi sau khi ESP32 xác nhận qua MQTT.</p>
      </div>

      <div className="room-plan">
        {rooms.map((room, index) => {
          const light = findLight(lights, room.id, room.name);
          const command = commands[normalizeLocation(light?.location ?? room.name)] ?? commands[room.id];
          const isOn = Boolean(light?.is_on);
          const isOnline = Boolean(light?.device_online);
          const isPending = command?.phase === "pending";
          const status = !light ? "Đang chờ dữ liệu" : !isOnline ? "ESP32 offline" : command?.phase === "error" ? "Lệnh chưa được xác nhận" : isPending ? `Đang chờ xác nhận ${command.action === "on" ? "bật" : "tắt"}` : isOn ? "Đèn đang bật" : "Đèn đang tắt";

          return (
            <article key={room.id} className={cn("room-space", room.className, isOn && isOnline && "is-lit", !isOnline && "is-offline", isPending && "is-pending")} style={{ "--room-index": index } as React.CSSProperties}>
              <div className="room-architecture" aria-hidden="true"><span /><span /><span /></div>
              <div className="room-topline">
                <span className="room-number">0{index + 1}</span>
                <span className={cn("room-status", isOnline && "is-online", command?.phase === "error" && "is-error")}><span className="status-dot" />{status}</span>
              </div>
              <div className="room-visual" aria-hidden="true"><span className="light-wash" /><HomeIcon name={room.icon} /></div>
              <div className="room-copy">
                <p>{room.caption}</p><h3>{room.name}</h3><span>{room.id} · GPIO {room.gpio} · active-LOW</span>
              </div>
              <button type="button" className="room-switch" role="switch" aria-checked={isOn} aria-label={`${isOn ? "Tắt" : "Bật"} đèn ${room.name}`} disabled={!light || !isOnline || isPending} onClick={() => onLightAction(isOn ? "off" : "on", room.name)}>
                <span>{isPending ? "Đang gửi" : isOn ? "Tắt đèn" : "Bật đèn"}</span><span className="switch-track"><span /></span>
              </button>
              {command?.phase === "error" && command.message ? <p className="room-error" role="alert">{command.message}</p> : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
