import { backendUrl, proxyGet } from "@/lib/proxy";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const qs = searchParams.toString();
  return proxyGet(`/ground-truth${qs ? `?${qs}` : ""}`);
}

export async function POST(req: Request) {
  const formData = await req.formData();
  const res = await fetch(backendUrl("/ground-truth"), {
    method: "POST",
    body: formData,
    cache: "no-store",
  });
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
