import { proxyGet } from "@/lib/proxy";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const status = searchParams.get("status");
  const path = status
    ? `/bank-transactions?status=${encodeURIComponent(status)}`
    : "/bank-transactions";
  return proxyGet(path);
}
