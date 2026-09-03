import { useEffect, useState } from "react";

const PHONE_QUERY = "(max-width: 767px)";

export function useMobileViewport() {
  const [isMobile, setIsMobile] = useState(() => typeof window !== "undefined" && window.matchMedia(PHONE_QUERY).matches);

  useEffect(() => {
    const media = window.matchMedia(PHONE_QUERY);
    const sync = () => setIsMobile(media.matches);
    sync();
    media.addEventListener?.("change", sync);
    return () => media.removeEventListener?.("change", sync);
  }, []);

  return isMobile;
}
