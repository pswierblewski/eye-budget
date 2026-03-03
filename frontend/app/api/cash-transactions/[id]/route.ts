import { proxyGet, proxyPut, proxyDelete } from "@/lib/proxy";

export async function GET(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyGet(`/cash-transactions/${params.id}`);
}

export async function PUT(
  req: Request,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  return proxyPut(`/cash-transactions/${params.id}`, body);
}

export async function DELETE(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyDelete(`/cash-transactions/${params.id}`);
}
