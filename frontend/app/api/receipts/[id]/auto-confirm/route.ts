import { proxyPost } from "@/lib/proxy";

export async function POST(
  req: Request,
  { params }: { params: { id: string } }
) {
  const { searchParams } = new URL(req.url);
  const qs = searchParams.toString();
  return proxyPost(`/receipts/${params.id}/auto-confirm${qs ? `?${qs}` : ""}`);
}
