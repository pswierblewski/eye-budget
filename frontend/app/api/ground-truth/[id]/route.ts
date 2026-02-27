import { proxyGet, proxyPut } from "@/lib/proxy";

export async function GET(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyGet(`/ground-truth/${params.id}`);
}

export async function PUT(
  req: Request,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  return proxyPut(`/ground-truth/${params.id}`, body);
}
