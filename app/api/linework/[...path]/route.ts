import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const resource = path.join("/");
  if (
    !/^(health|documents(?:\/[a-f0-9-]+(?:\/(?:analysis|export|workspace|original))?)?)$/.test(
      resource,
    )
  ) {
    return Response.json(
      { detail: "Unknown engine resource." },
      { status: 404 },
    );
  }
  if (Number(request.headers.get("content-length")) > 41 * 1024 * 1024) {
    return Response.json(
      { detail: "PDFs up to 40 MB are supported." },
      { status: 413 },
    );
  }
  try {
    const upstream = await fetch(
      `${process.env.PATTERN_ENGINE_URL ?? "http://127.0.0.1:8000"}/api/${resource}`,
      {
        method: request.method,
        headers: {
          "Content-Type":
            request.headers.get("content-type") ?? "application/json",
        },
        body:
          request.method === "GET" ? undefined : await request.arrayBuffer(),
        cache: "no-store",
        signal: request.signal,
      },
    );
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type":
          upstream.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return Response.json(
      {
        detail:
          "The local linework engine is unavailable. Start the app with the desktop launcher or yarn dev.",
      },
      { status: 503 },
    );
  }
}

export { proxy as GET, proxy as POST, proxy as PUT };
