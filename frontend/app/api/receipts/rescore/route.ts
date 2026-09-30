import { proxyPost } from "@/lib/proxy";

export async function POST(req: Request) {
  const { searchParams } = new URL(req.url);
  const qs = searchParams.toString();
  return proxyPost(`/receipts/rescore${qs ? `?${qs}` : ""}`);
}
