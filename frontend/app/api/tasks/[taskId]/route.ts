import { proxyGet } from "@/lib/proxy";

export async function GET(
  _req: Request,
  { params }: { params: { taskId: string } }
) {
  return proxyGet(`/tasks/${params.taskId}`);
}
