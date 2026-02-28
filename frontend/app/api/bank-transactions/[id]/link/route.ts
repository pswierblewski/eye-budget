import { proxyPost, proxyDelete } from "@/lib/proxy";

export async function POST(
  req: Request,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  return proxyPost(`/bank-transactions/${params.id}/link`, body);
}

export async function DELETE(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyDelete(`/bank-transactions/${params.id}/link`);
}
