import { proxyGet, proxyPatch, proxyDelete } from "@/lib/proxy";

export async function GET(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyGet(`/settlement-groups/${params.id}`);
}

export async function PATCH(
  req: Request,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  return proxyPatch(`/settlement-groups/${params.id}`, body);
}

export async function DELETE(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyDelete(`/settlement-groups/${params.id}`);
}
