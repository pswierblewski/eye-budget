import { proxyPost, proxyDelete } from "@/lib/proxy";

export async function POST(
  req: Request,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  return proxyPost(`/settlement-groups/${params.id}/members`, body);
}

export async function DELETE(req: Request, { params }: { params: { id: string } }) {
  const { searchParams } = new URL(req.url);
  const qs = searchParams.toString();
  return proxyDelete(
    `/settlement-groups/${params.id}/members${qs ? `?${qs}` : ""}`
  );
}
