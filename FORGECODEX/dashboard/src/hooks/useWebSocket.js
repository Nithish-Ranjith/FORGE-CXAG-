import { useEffect, useState } from "react";

export default function useWebSocket(url) {
  const [latest, setLatest] = useState(null);

  useEffect(() => {
    if (!url) {
      return undefined;
    }

    let websocket;
    let retryTimer;

    const connect = () => {
      websocket = new WebSocket(url);
      websocket.onmessage = (event) => {
        try {
          setLatest(JSON.parse(event.data));
        } catch {
          setLatest(null);
        }
      };
      websocket.onopen = () => websocket.send("subscribe");
      websocket.onclose = () => {
        retryTimer = window.setTimeout(connect, 1500);
      };
    };

    connect();

    return () => {
      window.clearTimeout(retryTimer);
      if (websocket && websocket.readyState < 2) {
        websocket.close();
      }
    };
  }, [url]);

  return latest;
}
