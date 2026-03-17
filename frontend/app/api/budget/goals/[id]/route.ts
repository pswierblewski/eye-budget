import { proxyPut, proxyDelete } from "@/lib/proxy";

export async function PUT(
  req: Request,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  return proxyPut(`/budget/goals/${params.id}`, body);
}

export async function DELETE(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyDelete(`/budget/goals/${params.id}`);
}
