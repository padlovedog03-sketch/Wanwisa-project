# PRD: Teaching Internship Portfolio (Canva Migration)

Status: In Review
Owner: pm
Upstream: User Request — Canva Export Source Code Migration
Date: 2026-11-02

## Problem

ระบบรายงานและแฟ้มสะสมผลงานการฝึกประสบการณ์วิชาชีพครูปัจจุบันถูก Export มาจาก Canva ในรูปแบบ Monolithic HTML ไฟล์เดียว (800+ บรรทัด) ซึ่งฝัง API Credentials ของ Firebase Realtime Database ไว้ในโค้ดฝั่ง Client โดยตรง, มีช่องโหว่ Cross-Site Scripting (XSS) จากการใช้ `innerHTML` กับ Input ของผู้ใช้, มี Dependency ภายในของ Canva ที่ใช้งานไม่ได้นอกระบบ (`canva://` image URI และ Canva Proprietary SDK scripts), และนำไฟล์ Base64 (รูปภาพ/PDF) บันทึกลงในฐานข้อมูล Realtime Database ซึ่งขัดต่อหลัก Best Practices ส่งผลให้ระบบไม่ปลอดภัย ขยายฟีเจอร์ต่อไม่ได้ และไม่สามารถทำ Automated Testing ได้

## Goal & Success Metrics

- **Clean Architecture & Separation of Concerns**: สลาย Monolith ออกเป็น Modular Components (React/Vite หรือ Next.js + TypeScript + Tailwind CSS)
- **Zero Insecure DOM Operations**: กำจัด `innerHTML` string concatenation 100% แทนที่ด้วย declarative Virtual DOM rendering เพื่อป้องกัน XSS
- **Decoupled Configuration**: นำ Credentials ของ Firebase ออกจาก Source Code ไปยัง Environment Variables (`.env.local`)
- **100% Feature Parity with Canva Original**: ผู้ใช้งานสามารถบันทึกและจัดการข้อมูลได้ครบถ้วนทั้ง 11 ส่วนงานเดิม โดยไม่สูญเสียฟังก์ชันใด ๆ

## Requirements (must-have)

| # | Requirement | Rationale |
|---|---|---|
| R1 | **Profile & School Management**: แบบฟอร์มบันทึกและแสดงผลข้อมูลนักศึกษาฝึกสอน และข้อมูลบริบทสถานศึกษา พร้อมคำนวณ Progress Bar ความคืบหน้า | ตอบสนองข้อมูลส่วนหัวและสรุปภาพรวมของรายงาน |
| R2 | **Teaching Schedule (ตารางสอน)**: แสดง เพิ่ม แก้ไข ลบรายการตารางสอน พร้อมรองรับการแนบลิงก์ไฟล์ภายนอก (Google Drive / URL) | แฟ้มสะสมงานต้องมีตารางสอนประจำสัปดาห์ |
| R3 | **18-Week Daily Logbook (บันทึกรายวัน 18 สัปดาห์)**: หน้ารวมสัปดาห์ 1-18 (5 วันทำการ/สัปดาห์) พร้อมตัวนับวันครบ/ไม่ครบ และฟอร์มบันทึกรายละเอียดกิจกรรม, สิ่งที่ได้เรียนรู้, ปัญหา และแนวทางแก้ไข | เป็นฟังก์ชันหลักในการฝึกสอนที่ต้องลงบันทึกรายวันตลอดภาคเรียน |
| R4 | **Lesson Plans (แผนการจัดการเรียนรู้)**: รายการแผนการสอน พร้อมบันทึกวันที่สอน กลุ่มเป้าหมาย และการเชื่อมโยงเอกสาร Google Drive | ครูพี่เลี้ยงและอาจารย์นิเทศก์ต้องตรวจสอบแผนการสอน |
| R5 | **Supervision Records (นิเทศการสอน)**: บันทึกผลการนิเทศ (จุดเด่น, ข้อเสนอแนะ, แผนปรับปรุง, คะแนน) พร้อม Gallery รูปภาพประกอบที่มี Client-side Compression (จำกัดรูปละไม่เกิน 200KB) | ใช้เป็นหลักฐานการประเมินจากครูพี่เลี้ยง |
| R6 | **Classroom Research (วิจัยในชั้นเรียน)**: บันทึกข้อมูลวิจัย กลุ่มเป้าหมาย ลิงก์เอกสาร และรายการไฟล์แนบ PDF | เอกสารประกอบวิจัยในชั้นเรียนสำหรับจบการฝึกสอน |
| R7 | **Competency Assessment (แบบประเมินสมรรถนะ)**: จัดการรายการประเมินสมรรถนะวิชาชีพครู รองรับทั้งลิงก์ภายนอกและไฟล์ PDF | แฟ้มรวบรวมเกณฑ์และผลการประเมินวิชาชีพ |
| R8 | **Activities & Practicum Galleries (รูปภาพกิจกรรมและฝึกสอน)**: แกลเลอรีรูปภาพแยก 2 หมวด พร้อมระบบย่อรูปภาพอัตโนมัติก่อนบันทึก | ลดภาระขนาดข้อมูลและแสดงผลรวดเร็ว |
| R9 | **Settings & Print/PDF Export**: หน้าตั้งค่าธีมสี (Official / Light / Deep), ชื่อเว็บไซต์, และปุ่ม Print/PDF Export แบบ Clean Layout (ซ่อนปุ่มและ Navbar อัตโนมัติเมื่อสั่งพิมพ์) | สำหรับจัดทำรูปเล่มรายงานส่งสถาบันการศึกษา |
| R10 | **Data Persistence & Fallback**: รองรับการอ่านและบันทึกข้อมูลกับ Firebase Realtime Database โดยมี LocalStorage เป็น Fallback ฉบับร่างกรณี Offline | ป้องกันข้อมูลสูญหายระหว่างการกรอก |

## Nice-to-have (explicitly deferred)

- **Authentication System (RBAC)**: ระบบ Login บัญชีผู้ใช้งานรายบุคคลเพื่อแยกระเบียนรายงานระหว่างนักศึกษา (ในเฟสแรกคงสถาปัตยกรรมแบบ Single-portfolio ตามต้นฉบับ Canva)
- **Direct Cloud Object Storage Integration**: อัปโหลดรูปภาพตรงเข้า Firebase Storage / AWS S3 แทนการบีบอัด Base64 (จะทำในเฟสถัดไปหลังเสร็จสิ้นการวาง Component Core)

## Out of Scope

- Canva Proprietary SDKs (`/_sdk/*`, `window.__codeletBootstrap__`, telemetry scripts) — ตัดทิ้งทั้งหมด
- Real-time Multi-user Collaborative Editing พร้อมกันในเวลาเดียว

## Assumptions

- ผู้ใช้งานมี Firebase Realtime Database ของตนเองพร้อมกำหนด Security Rules ที่อนุญาตให้ Client ที่ระบุอ่าน-เขียนได้
- เบราว์เซอร์ของผู้ใช้รองรับ Web Canvas API สำหรับการย่อขนาดภาพฝั่ง Client

## Open Questions

- ท่านปัด ต้องการให้สร้างโครงสร้าง Frontend เป็น React + Vite หรือ Next.js (App Router)?

## Approval history

- **2026-11-02 — drafted.** Drafted by Karen (PM role) based on user's Canva legacy codebase.
