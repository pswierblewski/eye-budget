import Pusher from "pusher-js";

let pusherInstance: Pusher | null = null;

/**
 * Returns a shared Pusher singleton connected to the self-hosted Soketi instance.
 * Configuration is read from NEXT_PUBLIC_* env vars so the values are available
 * client-side in the browser.
 */
export function getPusher(): Pusher {
  if (pusherInstance) return pusherInstance;

  pusherInstance = new Pusher(
    process.env.NEXT_PUBLIC_PUSHER_KEY ?? "eye-budget-key",
    {
      wsHost: process.env.NEXT_PUBLIC_PUSHER_WS_HOST ?? "localhost",
      wsPort: parseInt(process.env.NEXT_PUBLIC_PUSHER_WS_PORT ?? "6001", 10),
      forceTLS: false,
      disableStats: true,
      enabledTransports: ["ws", "wss"],
      // Soketi ignores cluster but pusher-js requires it
      cluster: "mt1",
    }
  );

  return pusherInstance;
}
