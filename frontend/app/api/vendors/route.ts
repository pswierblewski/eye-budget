import { proxyGet, proxyPost } from "@/lib/proxy";
import { NextRequest } from "next/server";

export async function GET() {
  return proxyGet("/vendors");
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  return proxyPost("/vendors", body);
}
