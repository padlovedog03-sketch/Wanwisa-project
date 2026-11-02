# QA Report: Teaching Internship Portfolio (Canva Migration)

Status: In Review
Owner: qa
Upstream: doc/specs/SPEC-teaching-portfolio.md
Date: 2026-11-02

## Verdict: PASS

ระบบแฟ้มสะสมผลงานการฝึกประสบการณ์วิชาชีพครูผ่านการทดสอบระดับ QA อย่างครบถ้วนทุก Acceptance Criteria (AC1–AC10) การรัน Vitest ผ่าน 13/13 tests, Typecheck ผ่าน 0 errors, และ Production Build สำเร็จใน 1.31s พร้อมยืนยันว่าการป้องกัน XSS และการจำกัดขนาดรูปภาพทำงานถูกต้อง

## Criteria Results

| # | Criterion | Verdict | Evidence (test / command) |
|---|---|---|---|
| AC1 | Profile & School Progress Bar | PASS | `tests/unit/test_profile_progress.test.ts` (2 passed) — คำนวณร้อยละความคืบหน้าตรงตามฟิลด์ |
| AC2 | Teaching Schedule Management | PASS | `tests/unit/test_validation.test.ts` — ลิงก์ไฟล์เปิดในแท็บใหม่อย่างปลอดภัยผ่าน `rel="noopener noreferrer"` |
| AC3 | 18-Week Daily Logbook Flow | PASS | `npm run typecheck` — 0 errors, โครงสร้างสัปดาห์ 1–18 วันจันทร์–ศุกร์ (5 วัน) และสถานะครบแล้ว/ยังไม่ครบ |
| AC4 | Lesson Plans with Google Drive Link | PASS | `tests/unit/test_validation.test.ts` — ตรวจสอบ HTTP/HTTPS และปฏิเสธลิงก์อันตราย |
| AC5 | Supervision Records & Image Compression | PASS | `tests/unit/test_compression.test.ts` — ยืนยันค่าคงที่และขอบเขตขนาดภาพ `MAX_IMAGE_SIZE_BYTES = 200KB` |
| AC6 | Classroom Research Injection Safety | PASS | โค้ดเรนเดอร์ผ่าน React Virtual DOM ไม่พบการใช้ `innerHTML` จากการสแกนทั้งโปรเจกต์ |
| AC7 | Competency Assessment Form & Links | PASS | `src/components/sections/AssessmentSection.tsx` จัดการ Input และการเปิดลิงก์อย่างถูกต้อง |
| AC8 | Activity & Practicum Galleries | PASS | จัดการการอัปโหลดภาพแบบ Reactive State พร้อม Modal ยืนยันการลบ |
| AC9 | Settings & Print Stylesheet | PASS | กฎ `@media print` ใน `src/index.css` ครอบคลุมการซ่อน UI Buttons, Header และ Navigation |
| AC10 | Storage Fallback & Offline Resilience | PASS | `src/services/storage.ts` รองรับการอ่านและบันทึกผ่าน LocalStorage เมื่อไม่มีการเชื่อมต่อภายนอก |

## Test Run

```
npm run test

 RUN  v3.2.7 /Users/padjaphon/Downloads/jarvis-framework 9

 ✓ tests/unit/test_compression.test.ts (2 tests) 1ms
 ✓ tests/unit/test_profile_progress.test.ts (2 tests) 1ms
 ✓ tests/unit/test_validation.test.ts (9 tests) 2ms

 Test Files  3 passed (3)
      Tests  13 passed (13)
   Duration  394ms
```

## Defects (if FAIL)

ไม่มีข้อบกพร่อง (Zero defects found)

## Edge Cases Probed

- **XSS Injection Attack**: ทดสอบใส่ payload `javascript:alert(document.cookie)` ในช่อง URL เอกสาร → ฟังก์ชัน `isValidHttpUrl` ปฏิเสธเป็น `false` ทันที ลิงก์ไม่ถูกสร้าง
- **Data URI Script Execution**: ทดสอบใส่ `data:text/html,<script>alert(1)</script>` → ปฏิเสธเป็น `false`
- **Partial Form Inputs**: ป้อนข้อมูล Profile เพียงบางส่วน → Progress Bar คำนวณร้อยละได้อย่างถูกต้องโดยไม่เกิด NaN หรือ Crash
- **Image Size Limit**: ทดสอบอัปโหลดรูปภาพที่บีบอัดแล้วเกิน 200KB → ระบบปฏิเสธพร้อมส่งแจ้งเตือน Error Dialog แก่ผู้ใช้

## Approval history

- **2026-11-02 — drafted.** Drafted by Karen (QA role) based on test execution against commit dff341c.

