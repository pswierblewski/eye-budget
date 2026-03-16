import { proxyGet, proxyPut } from "@/lib/proxy";

export async function GET() {
  return proxyGet("/budget/financial-focus");
}

export async function PUT(req: Request) {
  const body = await req.json();
  return proxyPut("/budget/financial-focus", body);
}
