import { neon } from '@neondatabase/serverless';

export const config = {
  runtime: 'edge',
};

function getDb() {
  const connectionString = process.env.POSTGRES_URL || process.env.DATABASE_URL;
  if (!connectionString) {
    return null;
  }
  return neon(connectionString);
}

export default async function handler(req: Request) {
  const sql = getDb();
  if (!sql) {
    return new Response(
      JSON.stringify({ error: 'DATABASE_NOT_CONFIGURED', message: 'POSTGRES_URL or DATABASE_URL environment variable is missing.' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }

  try {
    // Ensure table exists
    await sql`
      CREATE TABLE IF NOT EXISTS portfolios (
        id VARCHAR(64) PRIMARY KEY,
        data JSONB NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
      );
    `;

    if (req.method === 'GET') {
      const rows = await sql`SELECT data, updated_at FROM portfolios WHERE id = 'default' LIMIT 1;`;
      if (rows.length === 0) {
        return new Response(JSON.stringify({ found: false, data: null }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(JSON.stringify({ found: true, data: rows[0].data, updatedAt: rows[0].updated_at }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (req.method === 'POST') {
      const payload = await req.json();
      if (!payload || typeof payload !== 'object') {
        return new Response(JSON.stringify({ error: 'INVALID_PAYLOAD' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      await sql`
        INSERT INTO portfolios (id, data, updated_at)
        VALUES ('default', ${payload}, NOW())
        ON CONFLICT (id) DO UPDATE
        SET data = EXCLUDED.data, updated_at = NOW();
      `;

      return new Response(JSON.stringify({ success: true, updatedAt: new Date().toISOString() }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({ error: 'METHOD_NOT_ALLOWED' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    console.error('API Error:', err);
    return new Response(
      JSON.stringify({ error: 'INTERNAL_SERVER_ERROR', message: err.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

