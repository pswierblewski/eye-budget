import { proxyPatch } from "@/lib/proxy";

export async function PATCH(
  req: Request,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  return proxyPatch(`/cash-transactions/${params.id}/category`, body);
}
