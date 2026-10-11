import { NextResponse } from 'next/server';
import { serverData } from '@/lib/serverData';

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const prefix = searchParams.get('prefix') || '';
  const limit = Number(searchParams.get('limit') || 6);
  return NextResponse.json(serverData.getSuggestions(prefix, limit));
}
