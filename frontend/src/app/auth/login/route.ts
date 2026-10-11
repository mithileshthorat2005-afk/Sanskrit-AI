import { NextResponse } from 'next/server';
import { serverData } from '@/lib/serverData';

export async function POST(req: Request) {
  try {
    const { username, password } = await req.json();
    if (!username) {
      return NextResponse.json({ detail: 'Username is required' }, { status: 400 });
    }
    const user = serverData.authenticateUser(username, password || 'demo');
    return NextResponse.json(user);
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || 'Login failed' }, { status: 400 });
  }
}
