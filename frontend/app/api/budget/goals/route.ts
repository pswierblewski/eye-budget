import { proxyGet, proxyPost } from "@/lib/proxy";

export async function GET() {
  return proxyGet("/budget/goals");
}

export async function POST(req: Request) {
  const body = await req.json();
  return proxyPost("/budget/goals", body);
}
