import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const type = searchParams.get('type');
    
    if (!type || !['vowels', 'consonants'].includes(type)) {
        return NextResponse.json({ error: 'Invalid type (must be vowels or consonants)' }, { status: 400 });
    }

    const dirPath = path.join(process.cwd(), 'public', 'images', 'alphabet', type);
    
    try {
        if (!fs.existsSync(dirPath)) {
            return NextResponse.json({ images: [] });
        }
        
        const files = fs.readdirSync(dirPath);
        const images = files.filter(file => /\.(png|jpe?g|gif|webp)$/i.test(file))
                            .map(file => `/images/alphabet/${type}/${file}`);
                            
        return NextResponse.json({ images });
    } catch (error) {
        return NextResponse.json({ error: 'Failed to read directory' }, { status: 500 });
    }
}
