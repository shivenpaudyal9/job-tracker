import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function handler(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/')
  const url = `${BACKEND}/${path}${req.nextUrl.search}`

  const forwardHeaders: Record<string, string> = {}
  const auth = req.headers.get('authorization')
  if (auth) forwardHeaders['authorization'] = auth

  let body: BodyInit | undefined
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    const ct = req.headers.get('content-type') ?? ''
    if (ct.includes('multipart/form-data')) {
      body = await req.formData()
      // Let fetch set the correct multipart boundary — don't forward content-type
    } else {
      forwardHeaders['content-type'] = ct || 'application/json'
      body = await req.text()
    }
  }

  const upstream = await fetch(url, {
    method: req.method,
    headers: forwardHeaders,
    body,
  })

  const data = await upstream.arrayBuffer()
  return new NextResponse(data, {
    status: upstream.status,
    headers: {
      'content-type': upstream.headers.get('content-type') || 'application/json',
    },
  })
}

export const maxDuration = 120 // seconds — needed for embedding generation on cold start

export const GET = handler
export const POST = handler
export const PUT = handler
export const DELETE = handler
export const PATCH = handler
