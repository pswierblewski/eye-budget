import { proxyGet } from "@/lib/proxy";

export async function GET(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyGet(`/receipts/${params.id}`);
}
