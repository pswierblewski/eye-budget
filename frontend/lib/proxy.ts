/**
 * Proxy a request to the FastAPI backend.
 * BACKEND_URL is only available server-side.
 */
export function backendUrl(path: string): string {
  const base = process.env.BACKEND_URL ?? "http://localhost:8080";
  return `${base}${path}`;
}

/** 204/205/304 must use a null body; `new Response("", { status: 204 })` throws. */
function forwardUpstreamResponse(res: Response, bodyText: string): Response {
  const s = res.status;
  if (s === 204 || s === 205 || s === 304) {
    return new Response(null, { status: s });
  }
  return new Response(bodyText, {
    status: s,
    headers: { "Content-Type": res.headers.get("Content-Type") ?? "application/json" },
  });
}

export async function proxyGet(path: string): Promise<Response> {
  const res = await fetch(backendUrl(path), { cache: "no-store" });
  const body = await res.text();
  return forwardUpstreamResponse(res, body);
}

export async function proxyPost(path: string, body?: unknown): Promise<Response> {
  const res = await fetch(backendUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  const text = await res.text();
  return forwardUpstreamResponse(res, text);
}

export async function proxyPut(path: string, body?: unknown): Promise<Response> {
  const res = await fetch(backendUrl(path), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  const text = await res.text();
  return forwardUpstreamResponse(res, text);
}

export async function proxyDelete(path: string): Promise<Response> {
  const res = await fetch(backendUrl(path), {
    method: "DELETE",
    cache: "no-store",
  });
  const text = await res.text();
  return forwardUpstreamResponse(res, text);
}

export async function proxyPatch(path: string, body?: unknown): Promise<Response> {
  const res = await fetch(backendUrl(path), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  const text = await res.text();
  return forwardUpstreamResponse(res, text);
}
