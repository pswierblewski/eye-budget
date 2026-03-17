import { proxyPost } from "@/lib/proxy";

export async function POST(req: Request) {
  const body = await req.json();
  return proxyPost("/budget/emergency-advisor", body);
}
