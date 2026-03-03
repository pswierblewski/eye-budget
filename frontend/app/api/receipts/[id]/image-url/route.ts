import { backendUrl } from "@/lib/proxy";

/**
 * Proxy the presigned-URL request to the backend and forward the JSON response.
 * The result is cached for 1 h (matching the presigned-URL TTL and the
 * image proxy Cache-Control header).
 */
export async function GET(
  _req: Request,
  { params }: { params: { id: string } }
) {
  const res = await fetch(backendUrl(`/receipts/${params.id}/image-url`), {
    next: { revalidate: 3600 },
  });
  if (!res.ok) {
    return new Response("Image URL not found", { status: res.status });
  }
  const data = await res.json();
  return Response.json(data, {
    headers: {
      "Cache-Control": "public, max-age=3600",
    },
  });
}
