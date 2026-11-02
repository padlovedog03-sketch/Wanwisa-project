#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { neon } from '@neondatabase/serverless';

const fileArg = process.argv[2];
if (!fileArg) {
  console.error("Usage: node scripts/migrate_firebase_to_postgres.mjs <firebase_export.json> [POSTGRES_URL]");
  console.error("Example: node scripts/migrate_firebase_to_postgres.mjs ./teaching-internship-export.json");
  process.exit(1);
}

const connectionString = process.argv[3] || process.env.POSTGRES_URL || process.env.DATABASE_URL;
if (!connectionString) {
  console.error("Error: POSTGRES_URL or DATABASE_URL not set in environment or arguments.");
  process.exit(1);
}

if (!fs.existsSync(fileArg)) {
  console.error(`Error: File not found at '${fileArg}'`);
  process.exit(1);
}

try {
  const rawData = JSON.parse(fs.readFileSync(fileArg, 'utf-8'));
  console.log("Read Firebase JSON dump successfully.");

  // Extract relevant portfolio data node
  let portfolioData = rawData;
  if (rawData.teachingPracticeReport && rawData.teachingPracticeReport.data) {
    portfolioData = rawData.teachingPracticeReport.data;
    if (rawData.teaching_internship && rawData.teaching_internship.research) {
      portfolioData.research = {
        ...portfolioData.research,
        ...rawData.teaching_internship.research
      };
    }
  } else if (rawData.data) {
    portfolioData = rawData.data;
  }

  console.log("Connecting to PostgreSQL...");
  const sql = neon(connectionString);

  console.log("Ensuring table 'portfolios' exists...");
  await sql`
    CREATE TABLE IF NOT EXISTS portfolios (
      id VARCHAR(64) PRIMARY KEY,
      data JSONB NOT NULL,
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
  `;

  console.log("Migrating data into PostgreSQL (id: 'default')...");
  await sql`
    INSERT INTO portfolios (id, data, updated_at)
    VALUES ('default', ${portfolioData}, NOW())
    ON CONFLICT (id) DO UPDATE
    SET data = EXCLUDED.data, updated_at = NOW();
  `;

  console.log("SUCCESS: Firebase data successfully migrated and dumped into PostgreSQL!");
  process.exit(0);
} catch (err) {
  console.error("Migration failed:", err);
  process.exit(1);
}
