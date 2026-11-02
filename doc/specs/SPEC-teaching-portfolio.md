# SPEC: Teaching Internship Portfolio (Canva Migration)

Status: In Review
Owner: ba-sa
Upstream: doc/requirements/PRD-teaching-portfolio.md
Date: 2026-11-02

## Overview

ระบบเว็บแอปพลิเคชันสำหรับบันทึกและแสดงผลรายงานแฟ้มสะสมงานการฝึกประสบการณ์วิชาชีพครู (Teaching Internship Portfolio) พัฒนาด้วย React 19 / TypeScript / Vite และ Tailwind CSS เพื่อทดแทน Monolithic HTML เดิมจาก Canva โดยแยกเป็น Modular Components, จัดการ State แบบ Declarative, ทำความสะอาดและเข้ารหัส Input เพื่อป้องกัน XSS 100%, และแยกชั้นการเชื่อมต่อข้อมูลระหว่าง LocalStorage (Offline-first) กับ Firebase Realtime Database

## Acceptance Criteria

| # | Maps to | Given / When / Then | Test file |
|---|---|---|---|
| AC1 | R1 | Given ฟอร์มข้อมูลผู้จัดทำและสถานศึกษาว่างเปล่า, When ผู้ใช้กรอกข้อมูลครบถ้วนและบันทึก, Then State ถูกอัปเดตและ Progress Bar คำนวณร้อยละความคืบหน้าได้ถูกต้อง (0–100%) | `tests/unit/test_profile_progress.test.ts` |
| AC2 | R2 | Given รายการตารางสอน, When ผู้ใช้เพิ่มแถวตารางสอนพร้อมระบุวัน เวลา ชั้นเรียน วิชา และลิงก์เอกสาร, Then ข้อมูลถูกจัดเก็บและแสดงผลโดยไม่ผ่าน `innerHTML` พร้อมปุ่มเปิดลิงก์ที่เปิดในแท็บใหม่อย่างปลอดภัย (`rel="noopener noreferrer"`) | `tests/unit/test_schedule.test.ts` |
| AC3 | R3 | Given หน้ารวมบันทึกประจำวัน 18 สัปดาห์, When ผู้ใช้เลือกสัปดาห์ที่ 1–18 และบันทึกข้อมูลวันจันทร์–ศุกร์ (เวลา, กิจกรรม, สิ่งที่ได้เรียนรู้, ปัญหา, วิธีแก้), Then การนับจำนวนวันครบ 5 วันแสดงสถานะ "ครบแล้ว" และคำนวณ Progress ของสัปดาห์ได้ถูกต้อง | `tests/unit/test_daily_log.test.ts` |
| AC4 | R4 | Given รายการแผนการจัดการเรียนรู้, When ผู้ใช้แนบ URL ของ Google Drive, Then ระบบตรวจสอบ Protocol (HTTP/HTTPS) และบันทึกความสัมพันธ์กับชื่อแผนและระดับชั้น | `tests/unit/test_plans.test.ts` |
| AC5 | R5 | Given บันทึกการนิเทศการสอน, When มีการอัปโหลดรูปภาพหลักฐาน, Then ระบบประมวลผล Pure Function บีบอัดภาพ (Client-side Canvas Compression) ให้มีขนาดไม่เกิน 200KB ก่อนจัดเก็บ | `tests/unit/test_compression.test.ts` |
| AC6 | R6 | Given เอกสารวิจัยในชั้นเรียน, When ผู้ใช้กรอกชื่อเรื่อง กลุ่มเป้าหมาย วันที่ และ URL เอกสาร, Then การเรนเดอร์ข้อมูลแสดงผลแบบ Text Node ป้องกัน Script Injection | `tests/unit/test_research.test.ts` |
| AC7 | R7 | Given รายการประเมินสมรรถนะ, When ผู้ใช้เพิ่มรายการประเมินพร้อมลิงก์หรือข้อมูล PDF, Then รายการถูกจัดเก็บและแสดงผลในตารางประเมิน | `tests/unit/test_assessment.test.ts` |
| AC8 | R8 | Given แกลเลอรีรูปกิจกรรมและรูปฝึกสอน, When ผู้ใช้เพิ่มรูปและคำบรรยาย, Then มีการสร้าง Card แสดงภาพพร้อมคำบรรยายและปุ่มลบรายการที่ต้องผ่านการกดยืนยัน (Modal Confirmation) | `tests/unit/test_galleries.test.ts` |
| AC9 | R9 | Given หน้าการตั้งค่า, When ผู้ใช้เลือกธีม (Official / Light / Deep), Then CSS Custom Properties (`--blue`, `--sky`, `--ink`) บน Document Element ถูกปรับเปลี่ยนตามชุดสี และหน้าพิมพ์ (`@media print`) ซ่อน UI Controls ทั้งหมด | `tests/unit/test_settings.test.ts` |
| AC10 | R10 | Given การเรียกฟังก์ชันบันทึกข้อมูล, When การเชื่อมต่อ Firebase ล้มเหลวหรือ Offline, Then ระบบ Fallback ลง LocalStorage อัตโนมัติ พร้อมบันทึก Timestamp และแจ้งสถานะเตือนแก่ผู้ใช้โดยไม่เกิด Unhandled Promise Rejection | `tests/unit/test_storage_fallback.test.ts` |

## Functional Behavior

1. **State Management**:
   - ใช้ React Hooks (`usePortfolioState`) เพื่อรวม State ของทั้ง 11 ส่วนงานเข้าสู่ Single Source of Truth
   - ทุกครั้งที่มีการเปลี่ยนแปลงข้อมูลใน Form หรือ List จะมีการ Mark Dirty และแสดงแถบแจ้งเตือน "มีการแก้ไขที่ยังไม่ได้บันทึก"
2. **Security & Input Handling**:
   - ไม่มีฟังก์ชันใดที่แปลง String เป็น HTML ผ่าน `innerHTML` หรือ `dangerouslySetInnerHTML`
   - URL ทุกตัวที่รับจากผู้ใช้ (Google Drive, External links) ต้องผ่าน `new URL(rawUrl)` validation โดยรับเฉพาะ Protocol `http:` และ `https:`
3. **Image & File Compression**:
   - ฟังก์ชันบีบอัดรูปภาพคำนวณ Max Dimensions (600px) และลด Quality ลงอัตโนมัติเพื่อให้ขนาดไฟล์ไม่เกิน 200KB
   - หากรูปภาพเกิน 200KB หลังการบีบอัด ระบบจะปฏิเสธการบันทึกและแสดง Dialog แจ้งเตือน
4. **Theme & Print Styling**:
   - รองรับ 3 ธีม: `official` (#1267d6), `light` (#228adf), `deep` (#0c4b9c)
   - Print Mode กำหนดให้แสดงทุก Section ต่อเนื่องกัน ซ่อน Header, Floating Toast, Action Buttons

## Technical Design

### Directory Structure & File Inventory
```
src/
├── types/
│   └── portfolio.ts           # Interfaces & Types ทั้งหมด
├── utils/
│   ├── validation.ts          # URL Validation & Sanitization
│   └── compression.ts         # Client Canvas Compression Logic
├── services/
│   ├── storage.ts             # LocalStorage & Firebase Adapter
│   └── firebaseConfig.ts      # Firebase Init จาก VITE_FIREBASE_* env
├── hooks/
│   └── usePortfolioState.ts   # Central State Management Hook
├── components/
│   ├── layout/
│   │   ├── Header.tsx         # Sticky Header & Navigation
│   │   ├── Footer.tsx         # Footer Notes
│   │   └── ProgressBar.tsx    # Overall Progress Indicator
│   ├── common/
│   │   ├── ConfirmModal.tsx   # Delete/Clear Confirmation Modal
│   │   ├── Toast.tsx          # Toast Notification
│   │   └── ImageUploader.tsx  # Drag & Drop Image Compression Input
│   └── sections/
│       ├── ProfileSection.tsx
│       ├── SchoolSection.tsx
│       ├── ScheduleSection.tsx
│       ├── DailyLogSection.tsx
│       ├── PlansSection.tsx
│       ├── SupervisionSection.tsx
│       ├── ResearchSection.tsx
│       ├── AssessmentSection.tsx
│       ├── ActivitiesSection.tsx
│       ├── PracticumSection.tsx
│       └── SettingsSection.tsx
└── App.tsx                    # Shell & Active Section Switcher
```

### TypeScript Data Contracts (`src/types/portfolio.ts`)
```typescript
export interface TeacherProfile {
  reportTitle: string;
  studentName: string;
  studentId: string;
  major: string;
  institution: string;
  schoolName: string;
  semester: string;
  practicumPeriod: string;
  teachingHours: number;
}

export interface SchoolInfo {
  schoolFullName: string;
  address: string;
  levels: string;
  contact: string;
  principal: string;
  mentor: string;
  vision: string;
  mission: string;
}

export interface ScheduleItem {
  id: string;
  day: string;
  time: string;
  classroom: string;
  subject: string;
  room: string;
  note: string;
  fileName: string;
  fileUrl: string;
}

export interface DailyLogEntry {
  id: string;
  week: number;
  dayIndex: number;
  day: 'จันทร์' | 'อังคาร' | 'พุธ' | 'พฤหัสบดี' | 'ศุกร์';
  date: string;
  start: string;
  end: string;
  activity: string;
  learning: string;
  problem: string;
  solution: string;
  note: string;
}

export interface LessonPlanItem {
  id: string;
  title: string;
  subject: string;
  classroom: string;
  date: string;
  documentUrl: string;
  status?: string;
}

export interface SupervisionItem {
  id: string;
  date: string;
  evaluator: string;
  subject: string;
  classroom: string;
  strength: string;
  feedback: string;
  improvement: string;
  score: string;
  images: Array<{
    id: string;
    fileName: string;
    compressedDataUrl: string;
    compressedSize: number;
  }>;
}

export interface PortfolioState {
  profile: TeacherProfile;
  school: SchoolInfo;
  schedule: ScheduleItem[];
  daily: DailyLogEntry[];
  plans: LessonPlanItem[];
  supervision: SupervisionItem[];
  research: {
    title: string;
    target: string;
    uploadDate: string;
    documentUrl: string;
    items: Array<{ id: string; title: string; url: string }>;
  };
  assessment: Array<{ id: string; title: string; url: string; fileName?: string }>;
  activities: Array<{ id: string; title: string; date: string; caption: string; imageUrl: string }>;
  practicum: Array<{ id: string; title: string; date: string; caption: string; imageUrl: string }>;
  settings: {
    siteName: string;
    authorName: string;
    primaryTheme: 'official' | 'light' | 'deep';
    showSample: boolean;
    saveNote: string;
  };
}
```

## Affected tests / affected files

| File | Why it is affected | Expected change |
|---|---|---|
| `doc/specs/SPEC-teaching-portfolio.md` | เอกสารสเปกเทคนิคหลักของระบบ | New document |
| `src/types/portfolio.ts` | กำหนดโครงสร้างข้อมูลทั้งหมด | New file |
| `src/utils/validation.ts` | ฟังก์ชันตรวจสอบ URL และป้องกัน XSS | New file |
| `src/utils/compression.ts` | ฟังก์ชันบีบอัดรูปภาพฝั่ง Client | New file |
| `src/services/storage.ts` | Data Layer รองรับ Offline LocalStorage + Firebase | New file |
| `tests/unit/test_validation.test.ts` | ทดสอบ URL Validation และ Hostile Inputs | New file |
| `tests/unit/test_compression.test.ts` | ทดสอบขนาดภาพและ Compression Boundary | New file |
| `tests/unit/test_profile_progress.test.ts` | ทดสอบฟังก์ชันคำนวณ Progress Bar | New file |

How this list was built: วิเคราะห์จากความต้องการ R1–R10 ใน `doc/requirements/PRD-teaching-portfolio.md` และการตรวจสอบการทำงานของ Source Code จาก Canva เดิมใน `legacy/canva-portfolio.html`

## Decisions (ADR-style)

- **Vite + React 19 + TypeScript**:
  - *Context*: ต้องการความคล่องตัวในการพัฒนา, ไม่จำเป็นต้องมี Node Server Runtime ขณะทำงาน, และต้องการ Build Output เป็น Static Bundle ที่มีความเร็วสูง
  - *Decision*: เลือกใช้ Vite + React 19 พร้อม TypeScript แทน Next.js
  - *Consequences*: ไม่สามารถใช้ Server Actions ได้ แต่ลดความซับซ้อนของ Environment และกำจัดปัญหา Hydration Error
- **Decoupled Environment Variables for Firebase**:
  - *Context*: โค้ดเดิม Hardcode API Key และ Database URL ลงในไฟล์
  - *Decision*: แยก Config เข้า `.env.example` และ `.env.local`
  - *Consequences*: ต้องจัดเตรียมไฟล์ `.env.local` ในการเชื่อมต่อฐานข้อมูล แต่ปลอดภัยจากการรั่วไหลบน GitHub

## Traceability

- R1 → AC1
- R2 → AC2
- R3 → AC3
- R4 → AC4
- R5 → AC5
- R6 → AC6
- R7 → AC7
- R8 → AC8
- R9 → AC9
- R10 → AC10

## Approval history

- **2026-11-02 — drafted.** Drafted by Karen (BA/SA role) from approved `PRD-teaching-portfolio.md`.
