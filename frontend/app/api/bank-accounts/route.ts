import { proxyGet, proxyPost } from "@/lib/proxy";

export async function GET() {
  return proxyGet("/bank-accounts");
}

export async function POST(req: Request) {
  const body = await req.json();
  return proxyPost("/bank-accounts", body);
}
