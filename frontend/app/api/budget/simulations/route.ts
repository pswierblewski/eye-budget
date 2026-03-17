import { proxyGet, proxyPost } from "@/lib/proxy";

export async function GET() {
  return proxyGet("/budget/simulations");
}

export async function POST(req: Request) {
  const body = await req.json();
  return proxyPost("/budget/simulations", body);
}
