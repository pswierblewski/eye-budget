import { proxyPost } from "@/lib/proxy";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  return proxyPost("/receipts/evaluate", body);
}
