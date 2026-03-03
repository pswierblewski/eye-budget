import { proxyPatch, proxyDelete } from "@/lib/proxy";

export async function PATCH(
  req: Request,
  { params }: { params: { itemId: string } }
) {
  const body = await req.json();
  return proxyPatch(`/receipts/items/${params.itemId}`, body);
}

export async function DELETE(
  _req: Request,
  { params }: { params: { itemId: string } }
) {
  return proxyDelete(`/receipts/items/${params.itemId}`);
}
