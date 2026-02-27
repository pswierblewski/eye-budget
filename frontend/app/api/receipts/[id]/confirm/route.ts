import { proxyPost } from "@/lib/proxy";

export async function POST(
  req: Request,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  return proxyPost(`/receipts/${params.id}/confirm`, body);
}
