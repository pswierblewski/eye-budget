import { proxyGet, proxyDelete } from "@/lib/proxy";

export async function GET(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyGet(`/budget/simulations/${params.id}`);
}

export async function DELETE(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyDelete(`/budget/simulations/${params.id}`);
}
