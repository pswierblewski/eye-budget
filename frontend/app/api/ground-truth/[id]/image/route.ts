import { backendUrl } from "@/lib/proxy";

export async function GET(
  _req: Request,
  { params }: { params: { id: string } }
) {
  const res = await fetch(backendUrl(`/ground-truth/${params.id}/image`), {
    cache: "no-store",
  });
  if (!res.ok) {
    return new Response("Image not found", { status: res.status });
  }
  const buffer = await res.arrayBuffer();
  return new Response(buffer, {
    status: 200,
    headers: {
      "Content-Type": res.headers.get("Content-Type") ?? "image/png",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
