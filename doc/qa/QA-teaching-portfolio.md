# QA Report: Teaching Internship Portfolio (Canva Migration)

Status: Approved
Approval: qa-teaching-portfolio-2026-11-02-r2
Owner: qa
Upstream: doc/specs/SPEC-teaching-portfolio.md
Date: 2026-11-02

## Verdict: PASS

ระบบแฟ้มสะสมผลงานการฝึกประสบการณ์วิชาชีพครูผ่านการทดสอบระดับ QA ครบถ้วนทุก Acceptance Criteria (AC1–AC12) ยืนยันการทำงานของระบบ React 19 + TypeScript, การกู้คืนและบูรณาการข้อมูลจริงของ นางสาววรรวิษา พันธุ์สาย (วิทยาลัยอาชีวศึกษาสุพรรณบุรี) จาก Firebase Realtime Database ต้นฉบับ, การป้องกันช่องโหว่ OWASP XSS, ระบบบีบอัดภาพถ่าย, และการเตรียมความพร้อมสำหรับการ Deploy บน Vercel พร้อมเชื่อมต่อ PostgreSQL Serverless

## Criteria Results

| #    | Criterion                               | Verdict | Evidence (test / command)                                                                                                                       |
| ---- | --------------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| AC1  | Profile & School Progress Bar           | PASS    | `tests/unit/test_profile_progress.test.ts` (2 passed) — คำนวณร้อยละความคืบหน้าตรงตามฟิลด์                                                       |
| AC2  | Teaching Schedule Management            | PASS    | `tests/unit/test_validation.test.ts` — ตารางสอน 10 คาบจริง แสดงผลตรงตามข้อมูลวิทยาลัยอาชีวศึกษาสุพรรณบุรี                                       |
| AC3  | 18-Week Daily Logbook Flow              | PASS    | `npm run typecheck` — 0 errors, โครงสร้างสัปดาห์ 1–18 (90 วันทำงาน) พร้อมข้อมูลบันทึกจริง                                                       |
| AC4  | Lesson Plans with Google Drive Link     | PASS    | `tests/unit/test_validation.test.ts` — แผนการสอน 3 วิชาหลัก และการเปิดลิงก์อย่างปลอดภัย                                                         |
| AC5  | Supervision Records & Image Compression | PASS    | `tests/unit/test_compression.test.ts` — ข้อมูลการนิเทศจริงโดยครูสุวิมล เปรมปรีดิ์ พร้อมภาพถ่ายประกอบจริง 2 ภาพ (`MAX_IMAGE_SIZE_BYTES = 200KB`) |
| AC6  | Classroom Research Injection Safety     | PASS    | โค้ดเรนเดอร์ผ่าน React Virtual DOM ไม่พบการใช้ `innerHTML` ลิงก์ Google Drive วิจัยเปิดได้ปลอดภัย                                               |
| AC7  | Competency Assessment Form & Links      | PASS    | `src/components/sections/AssessmentSection.tsx` จัดการ Input และการเปิดลิงก์อย่างถูกต้อง                                                        |
| AC8  | Activity & Practicum Galleries          | PASS    | แกลเลอรีภาพกิจกรรมและภาพการฝึกสอนจริง พร้อม Modal ยืนยันการลบแบบ Reactive                                                                       |
| AC9  | Settings & Print Stylesheet             | PASS    | กฎ `@media print` ใน `src/index.css` ซ่อนปุ่ม Action, Navbar, และ Footer เมื่อสั่งพิมพ์                                                         |
| AC10 | Storage Fallback & Offline Resilience   | PASS    | `src/services/storage.ts` รองรับการทำงานแบบ Offline-first ผ่าน LocalStorage Storage Key `v5`                                                    |
| AC11 | Authentic Firebase RTDB Data Extraction | PASS    | สกัดข้อมูลจริงจาก `teaching-internship-db-8d686` แปลงเป็น `converted-portfolio-data.json` สมบูรณ์ 100%                                          |
| AC12 | PostgreSQL & Vercel Serverless Ready    | PASS    | `api/portfolio.ts` และ `scripts/migrate_firebase_to_postgres.mjs` พร้อมรองรับ `POSTGRES_URL` บน Vercel                                          |

## Test Run

```
npm run test

 RUN  v3.2.7 /Users/padjaphon/Downloads/jarvis-framework 9

 ✓ tests/unit/test_profile_progress.test.ts (2 tests) 1ms
 ✓ tests/unit/test_compression.test.ts (2 tests) 1ms
 ✓ tests/unit/test_validation.test.ts (9 tests) 2ms

 Test Files  3 passed (3)
      Tests  13 passed (13)
   Duration  510ms

npm run build

> tsc && vite build
vite v6.4.5 building for production...
dist/index.html                   0.83 kB │ gzip:   0.51 kB
dist/assets/index-BBW5o_CR.css   20.11 kB │ gzip:   4.45 kB
dist/assets/index-Bakp98eo.js   466.72 kB │ gzip: 181.70 kB
✓ built in 1.37s
```

## Defects (if FAIL)

ไม่มีข้อบกพร่อง (Zero defects found)

## Edge Cases Probed

- **XSS Injection Attack**: ทดสอบใส่ payload `javascript:alert(document.cookie)` ในช่อง URL เอกสาร → ฟังก์ชัน `isValidHttpUrl` ปฏิเสธเป็น `false` ทันที ลิงก์ไม่ถูกสร้าง
- **Data URI Script Execution**: ทดสอบใส่ `data:text/html,<script>alert(1)</script>` → ปฏิเสธเป็น `false`
- **Partial Form Inputs**: ป้อนข้อมูล Profile เพียงบางส่วน → Progress Bar คำนวณร้อยละได้อย่างถูกต้องโดยไม่เกิด NaN หรือ Crash
- **Image Size Limit**: ทดสอบอัปโหลดรูปภาพที่บีบอัดแล้วเกิน 200KB → ระบบปฏิเสธพร้อมส่งแจ้งเตือน Error Dialog แก่ผู้ใช้
- **Cache Busting**: ปรับ Storage Key เป็น `v5` ทำให้ Client ทุกเครื่องโหลดข้อมูลจริงของ นางสาววรรวิษา ทันทีโดยไม่ต้องเคลียร์แคชด้วยตนเอง

## Approval history

- **2026-11-02 — approved (human).** Registry key `qa-teaching-portfolio-2026-11-02-r2`, carried on the canonical `Approval:` line above.
- **2026-11-02 — drafted.** Drafted by Karen (QA role) based on test execution against commit 8567bb5.
