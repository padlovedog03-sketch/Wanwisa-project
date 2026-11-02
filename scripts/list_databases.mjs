import fs from 'fs';
import { GoogleAuth } from 'google-auth-library';

const keyFile = 'teaching-internship-db-firebase-adminsdk-fbsvc-0eef124f34.json';

async function main() {
  const auth = new GoogleAuth({
    keyFile,
    scopes: ['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/firebase.database']
  });

  const client = await auth.getClient();
  const token = await client.getAccessToken();
  const projectId = JSON.parse(fs.readFileSync(keyFile)).project_id;
  console.log(`OAuth Token obtained for project: ${projectId}`);

  // 1. Check Firestore Databases list
  console.log("\n1. Listing Firestore databases via REST API...");
  try {
    const res = await fetch(`https://firestore.googleapis.com/v1/projects/${projectId}/databases`, {
      headers: { Authorization: `Bearer ${token.token}` }
    });
    const data = await res.json();
    console.log("Firestore databases response:", JSON.stringify(data, null, 2));
  } catch (e) {
    console.log("Firestore databases list error:", e.message);
  }

  // 2. Check Realtime Database Instances
  console.log("\n2. Checking Firebase Management API for RTDB instances...");
  try {
    const res = await fetch(`https://firebasedatabase.googleapis.com/v1beta/projects/${projectId}/locations/-/instances`, {
      headers: { Authorization: `Bearer ${token.token}` }
    });
    const data = await res.json();
    console.log("RTDB instances response:", JSON.stringify(data, null, 2));
  } catch (e) {
    console.log("RTDB instances list error:", e.message);
  }
}

main().catch(err => console.error("Error:", err));
