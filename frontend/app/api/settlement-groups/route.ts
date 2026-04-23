import { proxyGet, proxyPost } from "@/lib/proxy";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const qs = searchParams.toString();
  return proxyGet(`/settlement-groups${qs ? `?${qs}` : ""}`);
}

export async function POST(req: Request) {
  const body = await req.json();
  return proxyPost("/settlement-groups", body);
}
