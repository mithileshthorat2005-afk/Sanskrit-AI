import { NextResponse } from 'next/server';
import { serverData } from '@/lib/serverData';

export async function GET() {
  return NextResponse.json(serverData.getVerbs());
}
