import { proxyGet } from "@/lib/proxy";

export async function GET(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyGet(`/bank-transactions/${params.id}/receipt-candidates`);
}
