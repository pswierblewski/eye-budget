import { proxyPost } from "@/lib/proxy";

export async function POST(
  _req: Request,
  { params }: { params: { scan_id: string } }
) {
  return proxyPost(`/cash-transactions/from-receipt/${params.scan_id}`);
}
