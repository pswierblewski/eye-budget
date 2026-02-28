import { backendUrl } from "@/lib/proxy";

export async function POST(req: Request) {
  const formData = await req.formData();
  const res = await fetch(backendUrl("/bank-transactions/import"), {
    method: "POST",
    body: formData,
    cache: "no-store",
  });
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
