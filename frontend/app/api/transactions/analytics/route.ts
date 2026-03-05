import { proxyGet } from "@/lib/proxy";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const qs = searchParams.toString();
  return proxyGet(`/transactions/analytics${qs ? `?${qs}` : ""}`);
}
