import fs from 'fs';
import path from 'path';
import { initializeApp, cert } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

const serviceAccountPath = path.resolve('teaching-internship-firebase-adminsdk-fbsvc-8a0ccdc95a.json');
if (!fs.existsSync(serviceAccountPath)) {
  console.error("Service account file not found at:", serviceAccountPath);
  process.exit(1);
}

const serviceAccount = JSON.parse(fs.readFileSync(serviceAccountPath, 'utf-8'));

const app = initializeApp({
  credential: cert(serviceAccount)
});

const DATABASE_ID = 'ai-studio-teacherpracticum-4d67fcce-e872-48c8-a088-60b220fa3aab';
const db = getFirestore(app, DATABASE_ID);

async function dumpCollection(collectionRef) {
  const snapshot = await collectionRef.get();
  const result = {};

  for (const doc of snapshot.docs) {
    const data = doc.data();
    // Recursively check for subcollections
    const subcollections = await doc.ref.listCollections();
    const subData = {};
    for (const subcol of subcollections) {
      subData[subcol.id] = await dumpCollection(subcol);
    }
    result[doc.id] = {
      ...data,
      ...(Object.keys(subData).length > 0 ? { _subcollections: subData } : {})
    };
  }

  return result;
}

async function main() {
  console.log("Connecting to Firestore with Admin SDK...");
  const collections = await db.listCollections();
  console.log(`Found ${collections.length} top-level collections:`, collections.map(c => c.id));

  const fullDump = {};
  for (const col of collections) {
    console.log(`Dumping collection: ${col.id}...`);
    fullDump[col.id] = await dumpCollection(col);
  }

  const outputPath = path.resolve('firebase-firestore-dump.json');
  fs.writeFileSync(outputPath, JSON.stringify(fullDump, null, 2), 'utf-8');
  console.log(`\nSUCCESS: Full Firestore database dumped to: ${outputPath}`);

  if (fullDump.users) {
    console.log("\nUsers in database:", Object.keys(fullDump.users));
  }
}

main().catch(err => {
  console.error("Dump failed:", err);
  process.exit(1);
});
