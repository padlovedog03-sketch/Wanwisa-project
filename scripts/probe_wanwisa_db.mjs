import { initializeApp, cert } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import { getDatabase } from 'firebase-admin/database';
import fs from 'fs';

const keyFile = 'teaching-internship-db-firebase-adminsdk-fbsvc-0eef124f34.json';
const key = JSON.parse(fs.readFileSync(keyFile, 'utf-8'));

console.log(`Connecting to project: ${key.project_id}...`);

const app = initializeApp({
  credential: cert(key),
  databaseURL: `https://${key.project_id}-default-rtdb.firebaseio.com`
}, 'wanwisa_probe');

async function probeFirestore() {
  console.log("\n--- Checking Firestore (default) ---");
  try {
    const db = getFirestore(app);
    const collections = await db.listCollections();
    console.log(`Firestore root collections count: ${collections.length}`);
    for (const col of collections) {
      console.log(`- Collection: ${col.id}`);
      const snapshot = await col.limit(5).get();
      console.log(`  Sample documents (${snapshot.size}):`);
      snapshot.forEach(doc => {
        console.log(`    doc id: ${doc.id}, data:`, JSON.stringify(doc.data()).slice(0, 100));
      });
    }
  } catch (err) {
    console.log("Firestore (default) error:", err.message);
  }
}

async function probeRTDB() {
  console.log("\n--- Checking Realtime Database ---");
  const urls = [
    `https://${key.project_id}-default-rtdb.firebaseio.com`,
    `https://${key.project_id}-default-rtdb.asia-southeast1.firebasedatabase.app`,
    `https://${key.project_id}.firebaseio.com`,
    `https://teaching-internship-db-8d686-default-rtdb.firebaseio.com`
  ];

  for (const url of urls) {
    console.log(`Probing RTDB URL: ${url}`);
    try {
      const rtdbApp = initializeApp({
        credential: cert(key),
        databaseURL: url
      }, `rtdb_${Math.random()}`);
      const db = getDatabase(rtdbApp);
      const snapshot = await db.ref('/').once('value');
      if (snapshot.exists()) {
        const val = snapshot.val();
        console.log(`SUCCESS on ${url}!`);
        console.log(`Keys:`, Object.keys(val));
        fs.writeFileSync('wanwisa-rtdb-dump.json', JSON.stringify(val, null, 2), 'utf-8');
        return val;
      } else {
        console.log(`Connected to ${url} but snapshot is empty/null.`);
      }
    } catch (err) {
      console.log(`Failed on ${url}:`, err.message);
    }
  }
}

async function main() {
  await probeFirestore();
  await probeRTDB();
  process.exit(0);
}

main().catch(err => {
  console.error("Fatal:", err);
  process.exit(1);
});
