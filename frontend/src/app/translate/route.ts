import { NextResponse } from 'next/server';
import { serverData } from '@/lib/serverData';

export async function POST(req: Request) {
  try {
    const { text, direction } = await req.json();
    if (!text) {
      return NextResponse.json({ detail: 'Text is required' }, { status: 400 });
    }
    const result = serverData.translate(text, direction || 'en_to_sa');
    return NextResponse.json(result);
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || 'Translation failed' }, { status: 500 });
  }
}
