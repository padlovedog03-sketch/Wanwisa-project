# ระบบรายงานการฝึกประสบการณ์วิชาชีพครู (Teaching Internship Portfolio)

เว็บแอปพลิเคชันสำหรับจัดเก็บ รวบรวม ตรวจสอบ และนำเสนอข้อมูลแฟ้มสะสมผลงานการฝึกประสบการณ์วิชาชีพครู (ครบถ้วน 10 หมวดหมู่งาน) พร้อมฟังก์ชันการพิมพ์รายงานมาตรฐาน (Print-Ready Layout), การคำนวณร้อยละความคืบหน้าแบบ Reactive, ระบบบีบอัดภาพถ่ายก่อนบันทึก, และการเชื่อมต่อ Cloud Database (Neon Postgres / Vercel Serverless)

---

## ฟังก์ชันการทำงานหลัก (Features)

1. **หน้าแรกและข้อมูลผู้จัดทำ (Profile & Cover Image):**
   - แสดงแบนเนอร์ชื่อรายงาน พร้อมช่องอัปโหลดรูปภาพหน้าปกแบบ Full-bleed
   - ข้อมูลส่วนตัวผู้จัดทำและรูปถ่ายผู้จัดทำ (Circular Avatar Slot) พร้อมระบบบีบอัดภาพอัตโนมัติ
   - แถบแสดงความคืบหน้าการกรอกข้อมูลรวม (Real-time Progress Bar)
2. **ข้อมูลสถานศึกษา (School Information):**
   - การ์ดแสดงตราสัญลักษณ์ประจำวิทยาลัย/โรงเรียน
   - ข้อมูลพื้นฐาน, ข้อมูลติดต่อ, ผู้บริหารสถานศึกษา, ครูพี่เลี้ยง, วิสัยทัศน์ และพันธกิจ
3. **ตารางสอน (Teaching Schedule):**
   - จัดการตารางสอนประจำสัปดาห์ (วัน, เวลา, ระดับชั้น, วิชา, ห้องเรียน)
   - สรุปจำนวนชั่วโมงสอนและแนบไฟล์ตารางสอน
4. **บันทึกรายวัน (18-Week Daily Logbook):**
   - บันทึกการปฏิบัติงานรายวันครบ 18 สัปดาห์ (90 วันทำงาน)
   - บันทึกกิจกรรม, สิ่งที่ได้เรียนรู้, ปัญหาที่พบ และแนวทางแก้ไข
5. **แผนการจัดการเรียนรู้ (Lesson Plans):**
   - รวบรวมแผนการสอนรายวิชา พร้อมแนบลิงก์เอกสาร Google Drive ที่ตรวจสอบความปลอดภัย (OWASP URL Protection)
6. **การนิเทศการสอน (Supervision Records):**
   - บันทึกผลการนิเทศจากอาจารย์นิเทศก์และครูพี่เลี้ยง
   - รองรับการแนบภาพถ่ายประกอบการนิเทศ พร้อมระบบบีบอัดขนาดภาพให้อยู่ในเกณฑ์มาตรฐาน (ต่ำกว่า 200KB)
7. **วิจัยในชั้นเรียน (Classroom Research):**
   - บันทึกหัวข้องานวิจัย กลุ่มเป้าหมาย และเอกสารงานวิจัย
8. **แบบประเมินสมรรถนะ (Competency Assessment):**
   - รายการประเมินสมรรถนะวิชาชีพครูตามมาตรฐานคุรุสภา
9. **แกลเลอรีภาพกิจกรรมและภาพการฝึกสอน (Galleries):**
   - รวบรวมภาพถ่ายกิจกรรมและภาพบรรยากาศการจัดการเรียนรู้ในห้องเรียน
10. **การตั้งค่าและระบบพิมพ์ (Settings & Print):**
    - สำรองข้อมูล (Backup) และนำเข้า/ส่งออกข้อมูลในรูปแบบ JSON
    - เลย์เอาต์รองรับการสั่งพิมพ์เป็นเอกสารกระดาษหรือบันทึกเป็น PDF (`@media print`) โดยซ่อนปุ่มและ Navbar อัตโนมัติ

---

## เทคโนโลยีที่ใช้ (Tech Stack)

- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS
- **Icons:** Lucide React
- **Serverless API:** Vercel Edge Runtime (`api/portfolio.ts`)
- **Database:** Neon Serverless PostgreSQL (`@neondatabase/serverless`) / Firebase Realtime Database
- **Client Storage:** LocalStorage (Offline-First Architecture)

---

## การติดตั้งและการเริ่มพัฒนา (Getting Started)

### 1. ติดตั้ง Dependencies
```bash
npm install
```

### 2. รันในโหมดพัฒนา (Development Server)
```bash
npm run dev
```

### 3. ตรวจสอบ Type และรัน Unit Tests
```bash
npm run typecheck
npm test
```

### 4. Build สำหรับ Production
```bash
npm run build
```

---

## การ Deploy บน Vercel (Deployment)

1. นำ Repository นี้เชื่อมต่อกับ **Vercel**
2. Vercel จะตรวจจับการตั้งค่า Vite จาก `vercel.json` โดยอัตโนมัติ
3. (ทางเลือก) หากต้องการใช้ระบบ Cloud Database ให้เชื่อมต่อ **Vercel Postgres (Neon)** ในแดชบอร์ด Vercel ตัวแปร `POSTGRES_URL` จะถูกผูกเข้ากับระบบอัตโนมัติ
4. กด **Deploy** เพื่อเริ่มให้บริการ
