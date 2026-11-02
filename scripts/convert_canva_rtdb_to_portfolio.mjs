import fs from 'fs';
import path from 'path';

const dumpFile = path.resolve('canva-original-firebase-data.json');
if (!fs.existsSync(dumpFile)) {
  console.error("canva-original-firebase-data.json not found!");
  process.exit(1);
}

const raw = JSON.parse(fs.readFileSync(dumpFile, 'utf-8'));
const rep = raw.teachingPracticeReport?.data || {};
const researchRoot = raw.teaching_internship?.research || {};

console.log("Converting Canva Realtime Database to PortfolioState...");

// 1. Profile
const profile = {
  reportTitle: rep.profile?.report_title || "รายงานการฝึกสอนประสบการณ์วิชาชีพครู",
  studentName: rep.profile?.student_name || "นักศึกษาฝึกสอน",
  studentId: rep.profile?.student_id || "670XXXXXXXXX",
  major: rep.profile?.major || "สาขาเทคโนโลยีธุรกิจดิจิทัล",
  institution: rep.profile?.institution || "มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ",
  schoolName: rep.profile?.school_name || "วิทยาลัยอาชีวศึกษาสุพรรณบุรี",
  semester: rep.profile?.semester || "ภาคเรียนที่ 1 / ปีการศึกษา 2569",
  practicumPeriod: rep.profile?.practicum_period || "5 พฤษภาคม – 31 มีนาคม 2569",
  teachingHours: Number(rep.profile?.teaching_hours) || 12,
};

// 2. School
const school = {
  schoolFullName: rep.school?.school_full_name || "วิทยาลัยอาชีวศึกษาสุพรรณบุรี",
  address: rep.school?.address || "854 ถนน พระพันวษา ตำบลท่าพี่เลี้ยง อำเภอเมืองสุพรรณบุรี สุพรรณบุรี 72000",
  levels: rep.school?.levels || "ปวช. - ปวส.",
  contact: rep.school?.contact ? rep.school.contact.trim() : "0XX-XXX-XXXX",
  principal: rep.school?.principal || "ดร.ทรงวุฒิ เรือนไทย",
  mentor: rep.school?.mentor || "นางสาวสุวิมล เปรมปรีดิ์",
  vision: rep.school?.vision || "วิทยาลัยวิชาชีพชั้นนำ ดำรงคุณธรรม ก้าวทันเทคโนโลยี",
  mission: rep.school?.mission || "มุ่งพัฒนาหลักสูตรและผู้เรียนให้เป็นเลิศด้านทักษะวิชาชีพและคุณธรรม, พัฒนาครูและนวัตกรรม, พร้อมสร้างเครือข่ายความร่วมมือเพื่อยกระดับอาชีวศึกษา",
};

// 3. Schedule
const schedule = (rep.schedule || []).map((item, idx) => ({
  id: `sch-${idx + 1}`,
  day: item.day || 'จันทร์',
  time: item.time || '',
  classroom: item.classroom || '',
  subject: item.subject || '',
  room: item.room || '',
  note: item.note || '',
  fileName: item.fileName || '',
  fileUrl: item.fileUrl || '',
}));

// 4. Daily Logs (De-duplicate 109 logs by week-dayIndex, prioritize filled ones)
const workDays = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์'];
const dailyMap = new Map();

// Initialize all 18 weeks (5 days each) with clean template
for (let w = 1; w <= 18; w++) {
  for (let d = 0; d < 5; d++) {
    const key = `${w}-${d}`;
    dailyMap.set(key, {
      id: `day-${w}-${d}`,
      week: w,
      dayIndex: d,
      day: workDays[d],
      date: '',
      start: '07:30',
      end: '16:30',
      activity: '',
      learning: '',
      problem: '',
      solution: '',
      note: '',
    });
  }
}

// Overlay actual logs from Canva RTDB
if (Array.isArray(rep.daily)) {
  for (const entry of rep.daily) {
    const w = Number(entry.week) || 1;
    const d = Number(entry.dayIndex) ?? 0;
    if (w < 1 || w > 18 || d < 0 || d > 4) continue;
    const key = `${w}-${d}`;
    const existing = dailyMap.get(key);

    // If existing is blank or new entry has content, overlay
    if (!existing.activity || entry.activity) {
      dailyMap.set(key, {
        id: entry.id || `day-${w}-${d}`,
        week: w,
        dayIndex: d,
        day: entry.day || workDays[d],
        date: entry.date || existing.date,
        start: entry.start || existing.start,
        end: entry.end || existing.end,
        activity: entry.activity || existing.activity,
        learning: entry.learning || existing.learning,
        problem: entry.problem || existing.problem,
        solution: entry.solution || existing.solution,
        note: entry.note || existing.note,
      });
    }
  }
}

const daily = Array.from(dailyMap.values()).sort((a, b) => {
  if (a.week !== b.week) return a.week - b.week;
  return a.dayIndex - b.dayIndex;
});

// 5. Plans
const plans = [
  {
    id: "plan-1",
    title: "แผนการจัดการเรียนรู้รายวิชา องค์ประกอบศิลป์สำหรับงานกราฟิก (ปวช.1/2)",
    subject: "องค์ประกอบศิลป์สำหรับงานกราฟิก",
    classroom: "ปวช. 1/2",
    date: "2026-06-12",
    documentUrl: "",
    status: "ผ่านการนิเทศ",
  },
  {
    id: "plan-2",
    title: "แผนการจัดการเรียนรู้รายวิชา ระบบปฏิบัติการคอมพิวเตอร์ (ปวช.1/2)",
    subject: "ระบบปฏิบัติการคอมพิวเตอร์",
    classroom: "ปวช. 1/2",
    date: "2026-06-15",
    documentUrl: "",
    status: "ตรวจอนุมัติแล้ว",
  },
  {
    id: "plan-3",
    title: "แผนการจัดการเรียนรู้รายวิชา โปรแกรมกราฟิกเพื่อสร้างสื่อดิจิทัล (ปวช.2/1)",
    subject: "โปรแกรมกราฟิกเพื่อสร้างสื่อดิจิทัล",
    classroom: "ปวช. 2/1",
    date: "2026-07-01",
    documentUrl: "",
    status: "ตรวจอนุมัติแล้ว",
  }
];

// 6. Supervision
const supervision = (rep.supervision || []).map((s, idx) => ({
  id: s.id || `sup-${idx + 1}`,
  date: s.date || "2026-09-14",
  evaluator: s.evaluator || "นางสาวสุวิมล เปรมปรีดิ์",
  subject: s.subject || "องค์ประกอบศิลป์สำหรับงานกราฟิก",
  classroom: s.classroom || "ปวช.1/2",
  strength: s.strength || "ใช้สื่อเหมาะสมและสื่อสารชัดเจน",
  feedback: s.feedback || "เพิ่มคำถามกระตุ้นการคิด",
  improvement: s.improvement || "เตรียมคำถามปลายเปิดเพิ่มขึ้น",
  score: s.score || "ดี",
  images: Array.isArray(s.images) ? s.images.map((img, i) => ({
    id: img.id || `sup-img-${i}`,
    fileName: img.fileName || `supervision_${i + 1}.jpg`,
    compressedDataUrl: img.compressedDataUrl || img.imageUrl || '',
    compressedSize: img.compressedSize || 0,
  })) : [],
}));

// 7. Research
const research = {
  title: researchRoot.researchTitle || rep.research?.title || "การพัฒนาทักษะการคิดวิเคราะห์ด้วยการจัดการเรียนรู้แบบใช้ปัญหาเป็นฐาน",
  target: researchRoot.targetGroup || rep.research?.target || "นักเรียนชั้นประถมศึกษาปีที่ 5",
  uploadDate: researchRoot.updatedAt?.slice(0, 10) || "2026-09-18",
  documentUrl: researchRoot.documentUrl || rep.research?.documentUrl || "https://drive.google.com/file/d/1VkLDkU_pePnQjnJV9xGRCtLrldDnrTJU/view?usp=sharing",
  items: [
    {
      id: "res-doc-1",
      title: "เอกสารรายงานวิจัยฉบับสมบูรณ์ (Google Drive)",
      url: researchRoot.documentUrl || rep.research?.documentUrl || "https://drive.google.com/file/d/1VkLDkU_pePnQjnJV9xGRCtLrldDnrTJU/view?usp=sharing",
    }
  ],
};

// 8. Activities
const activities = [];
const rawActs = [];
if (Array.isArray(rep.activities)) {
  rawActs.push(...rep.activities);
} else if (rep.activities) {
  for (const [k, v] of Object.entries(rep.activities)) {
    if (Array.isArray(v)) rawActs.push(...v);
    else if (typeof v === 'object' && v !== null && (v.title || v.caption)) rawActs.push(v);
  }
}

rawActs.forEach((act, idx) => {
  activities.push({
    id: act.id || `act-${idx + 1}`,
    title: act.title || 'กิจกรรมสถานศึกษา',
    date: act.date || '2026-09-14',
    caption: act.caption || '',
    imageUrl: act.imageUrl || act.imageMeta?.imageUrl || '',
  });
});

// 9. Practicum
const practicum = (rep.practicum || []).map((p, idx) => ({
  id: p.id || `prac-${idx + 1}`,
  title: p.title || (idx === 0 ? "ภาพการฝึกประสบการณ์วิชาชีพ" : "บรรยากาศห้องเรียน"),
  date: p.date || "2026-08-25",
  caption: p.caption || '',
  imageUrl: p.imageUrl || '',
}));

// 10. Settings
const settings = {
  siteName: "รายงานการฝึกสอน",
  authorName: profile.studentName,
  primaryTheme: "official",
  showSample: false,
  saveNote: `นำเข้าข้อมูลสมบูรณ์จาก Canva Firebase RTDB (${profile.schoolName})`,
};

const fullState = {
  profile,
  school,
  schedule,
  daily,
  plans,
  supervision,
  research,
  assessment: [],
  activities,
  practicum,
  settings,
};

const outputPath = path.resolve('converted-portfolio-data.json');
fs.writeFileSync(outputPath, JSON.stringify(fullState, null, 2), 'utf-8');

console.log(`SUCCESS: Migrated Canva Realtime Database to ${outputPath}`);
console.log(`- Profile: ${profile.studentName} (${profile.institution} -> ${profile.schoolName})`);
console.log(`- Schedule: ${schedule.length} items`);
console.log(`- Daily: ${daily.length} items (90 week-days)`);
console.log(`- Supervision: ${supervision.length} items`);
console.log(`- Research Document: ${research.documentUrl}`);
console.log(`- Activities: ${activities.length} items`);
console.log(`- Practicum: ${practicum.length} items`);
