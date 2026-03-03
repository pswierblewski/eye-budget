import { proxyPost } from "@/lib/proxy";

export async function POST(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyPost(`/cash-transactions/${params.id}/reopen`);
}
