import { NextResponse } from 'next/server';
import { serverData } from '@/lib/serverData';

export async function POST(req: Request) {
  try {
    const { username, text, use_ai } = await req.json();
    if (!text || typeof text !== 'string') {
      return NextResponse.json({ detail: 'Valid Sanskrit text is required' }, { status: 400 });
    }
    const result = serverData.checkGrammar(username || 'demo', text, Boolean(use_ai));
    return NextResponse.json(result);
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || 'Grammar check failed' }, { status: 500 });
  }
}
