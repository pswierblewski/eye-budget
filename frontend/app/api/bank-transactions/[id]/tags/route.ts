import { proxyPatch } from "@/lib/proxy";

export async function PATCH(
  req: Request,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  return proxyPatch(`/bank-transactions/${params.id}/tags`, body);
}
