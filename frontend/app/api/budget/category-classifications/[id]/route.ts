import { proxyPut } from "@/lib/proxy";

export async function PUT(
  req: Request,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  return proxyPut(`/budget/category-classifications/${params.id}`, body);
}
