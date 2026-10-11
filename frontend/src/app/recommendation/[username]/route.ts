import { NextResponse } from 'next/server';
import { serverData } from '@/lib/serverData';

export async function GET(req: Request, { params }: { params: Promise<{ username: string }> }) {
  const { username } = await params;
  return NextResponse.json(serverData.getRecommendation(username));
}
