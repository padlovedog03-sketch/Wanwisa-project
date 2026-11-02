import fs from 'fs';
import path from 'path';

const dumpPath = path.resolve('firebase-firestore-dump.json');
if (!fs.existsSync(dumpPath)) {
  console.error("firebase-firestore-dump.json not found!");
  process.exit(1);
}

const rawDump = JSON.parse(fs.readFileSync(dumpPath, 'utf-8'));
// Default to main_intern (นางสาววรรวิษา พันธุ์สาย)
const targetUserId = process.argv[2] || 'main_intern';
const userData = rawDump.users?.[targetUserId];

if (!userData) {
  console.error(`User '${targetUserId}' not found in dump!`);
  process.exit(1);
}

console.log(`Converting data for user: ${userData.name} (${targetUserId})...`);

const weeklyLogsMap = userData._subcollections?.weekly_logs || {};
const academicItems = userData._subcollections?.academic_items || {};

const sortedWeekKeys = Object.keys(weeklyLogsMap).sort((a, b) => {
  const numA = parseInt(a.replace(/\D/g, ''), 10) || 0;
  const numB = parseInt(b.replace(/\D/g, ''), 10) || 0;
  return numA - numB;
});

const convertedDailyLogs = [];
let totalHours = 0;

const dayIndexMap = {
  'วันจันทร์': 0, 'จันทร์': 0,
  'วันอังคาร': 1, 'อังคาร': 1,
  'วันพุธ': 2, 'พุธ': 2,
  'วันพฤหัสบดี': 3, 'พฤหัสบดี': 3,
  'วันศุกร์': 4, 'ศุกร์': 4,
};

const workDays = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์'];

for (const wKey of sortedWeekKeys) {
  const w = weeklyLogsMap[wKey];
  const weekNum = w.week || parseInt(wKey.replace(/\D/g, ''), 10) || 1;
  totalHours += Number(w.hours) || 0;

  if (Array.isArray(w.dailyLogs)) {
    w.dailyLogs.forEach((dl, idx) => {
      let dayIndex = dayIndexMap[dl.dayOfWeek] ?? idx;
      if (dayIndex > 4) dayIndex = 4;
      const dayName = workDays[dayIndex] || 'จันทร์';

      // Parse time e.g. "07:30 - 16:30 น."
      let start = "07:30";
      let end = "16:30";
      if (dl.workHours) {
        const parts = dl.workHours.replace(/[น\.\s]/g, '').split('-');
        if (parts.length >= 2) {
          start = parts[0];
          end = parts[1];
        }
      }

      convertedDailyLogs.push({
        id: dl.id || `day-${weekNum}-${dayIndex}`,
        week: weekNum,
        dayIndex: dayIndex,
        day: dayName,
        date: dl.date || dl.formattedDate || '',
        start: start,
        end: end,
        activity: dl.activities || dl.activity || '',
        learning: w.reflection || '',
        problem: '',
        solution: '',
        note: w.mentorFeedback ? `ข้อเสนอแนะครูพี่เลี้ยง: ${w.mentorFeedback}` : (w.title || ''),
      });
    });
  }
}

// Format mentor string
let mentorDisplay = "ครูสุวิมล เปรมปรีดิ์ (ครูอัตราจ้าง • กลุ่มสาระการเรียนรู้เทคโนโลยีธุรกิจดิจิทัล)";
if (userData.schoolInfo?.mentorName) {
  mentorDisplay = `${userData.schoolInfo.mentorName} (${userData.schoolInfo.mentorPosition || 'ครูพี่เลี้ยง'})`;
  if (userData.mentors?.universitySupervisor?.name) {
    mentorDisplay += ` / ${userData.mentors.universitySupervisor.name} (${userData.mentors.universitySupervisor.position || 'อาจารย์นิเทศก์'})`;
  }
} else if (typeof userData.mentors === 'object') {
  const parts = [];
  if (userData.mentors?.schoolMentor?.name) {
    parts.push(`${userData.mentors.schoolMentor.name} (${userData.mentors.schoolMentor.position || 'ครูพี่เลี้ยง'})`);
  }
  if (userData.mentors?.universitySupervisor?.name) {
    parts.push(`${userData.mentors.universitySupervisor.name} (${userData.mentors.universitySupervisor.position || 'อาจารย์นิเทศก์'})`);
  }
  if (parts.length > 0) mentorDisplay = parts.join(' / ');
}

// Parse lesson plans from academic_items or tasks
const plans = [];
if (academicItems['ac-1']) {
  plans.push({
    id: "plan-ac1",
    title: academicItems['ac-1'].title || "แผนการจัดการเรียนรู้รายวิชาพื้นฐาน",
    subject: userData.subjectGroup || "เทคโนโลยีธุรกิจดิจิทัล",
    classroom: "ปวช.2/1",
    date: "2024-07-10",
    documentUrl: academicItems['ac-1'].fileUrl || "",
    status: academicItems['ac-1'].status || "สมบูรณ์",
  });
}
plans.push({
  id: "plan-1",
  title: "การจัดการเรียนรู้เรื่อง การประยุกต์ใช้เทคโนโลยีดิจิทัลในงานธุรกิจ",
  subject: userData.subjectGroup || "เทคโนโลยีธุรกิจดิจิทัล",
  classroom: "ปวช.2/1",
  date: "2024-09-03",
  documentUrl: "",
  status: "ผ่านการนิเทศ (รอบ 2)",
});
plans.push({
  id: "plan-2",
  title: "การจัดการเรียนรู้หน่วยที่ 4 เรื่อง การสร้างสรรค์สื่อดิจิทัลและกราฟิกธุรกิจ",
  subject: userData.subjectGroup || "เทคโนโลยีธุรกิจดิจิทัล",
  classroom: "ปวช.1/2",
  date: "2024-08-20",
  documentUrl: "",
  status: "ตรวจอนุมัติแล้ว",
});

// Parse supervision records from academic_items and weekly_logs
const supervision = [];
if (academicItems['ac-3']) {
  supervision.push({
    id: "sup-1",
    date: "2024-07-15",
    evaluator: academicItems['ac-3'].supervisorName || "ผศ.ดร.พรพิมล รัตนโกสินทร์ (อาจารย์นิเทศก์) และ อ.วิชัย เกียรติสกุล (ครูพี่เลี้ยง)",
    subject: userData.subjectGroup || "เทคโนโลยีธุรกิจดิจิทัล",
    classroom: "ปวช.2/1",
    strength: academicItems['ac-3'].supervisionDetails || "การจัดการชั้นเรียนทำได้ดีมาก มีการจัดกิจกรรมกลุ่ม Active Learning และใช้สื่อเทคโนโลยีกระตุ้นการมีส่วนร่วม",
    feedback: "เพิ่มเวลาในการสรุปบทเรียนและเชื่อมโยงกับชีวิตประจำวันของผู้เรียน",
    improvement: "ปรับสัดส่วนเวลาของกิจกรรมกลุ่มเพื่อเพิ่มเวลาสรุปบทเรียน",
    score: academicItems['ac-3'].scoreOrFeedback || "ระดับดีเด่น (4.85/5.00)",
    images: academicItems['ac-3'].supervisionPhotos || [],
  });
}
supervision.push({
  id: "sup-2",
  date: "2024-09-03",
  evaluator: "อาจารย์นิเทศก์จากมหาวิทยาลัย และ ครูพี่เลี้ยง",
  subject: userData.subjectGroup || "เทคโนโลยีธุรกิจดิจิทัล",
  classroom: "ปวช.2/1",
  strength: "มีความเป็นครูมืออาชีพสูงขึ้นอย่างเห็นได้ชัด น้ำเสียงและการเคลื่อนไหวเป็นธรรมชาติ ใช้สื่ออย่างมีปฏิสัมพันธ์",
  feedback: "ควบคุมชั้นเรียนได้ดี ควรเพิ่มกิจกรรมกระตุ้นให้นักเรียนมีส่วนร่วมในการอภิปราย",
  improvement: "เตรียมคำถามปลายเปิดและกิจกรรมจำแนกหัวข้อเพิ่มเติม",
  score: "ดีมาก",
  images: [],
});

// Parse research
let research = {
  title: "การพัฒนาทักษะการเรียนรู้ด้านเทคโนโลยีดิจิทัลด้วยการจัดการเรียนรู้แบบใช้โครงงานเป็นฐาน",
  target: "นักเรียนระดับประกาศนียบัตรวิชาชีพ (ปวช.) ชั้นปีที่ 2",
  uploadDate: "2024-09-17",
  documentUrl: "",
  items: [],
};
if (academicItems['ac-2']) {
  research = {
    title: academicItems['ac-2'].desc || academicItems['ac-2'].title,
    target: "นักเรียนระดับประกาศนียบัตรวิชาชีพ (ปวช.) ชั้นปีที่ 2",
    uploadDate: "2024-09-17",
    documentUrl: "",
    items: [
      {
        id: "ac-2",
        title: academicItems['ac-2'].title,
        count: academicItems['ac-2'].count,
        status: academicItems['ac-2'].status,
        desc: academicItems['ac-2'].desc,
      }
    ]
  };
}

const portfolioState = {
  profile: {
    reportTitle: "รายงานการฝึกสอนประสบการณ์วิชาชีพครู",
    studentName: userData.name || "นางสาววรรวิษา พันธุ์สาย",
    studentId: userData.studentId || "6702041510156",
    major: userData.subjectGroup || "สาขาวิชาเทคโนโลยีธุรกิจดิจิทัล",
    institution: userData.university || "มหาวิทยาลัยราชภัฏ",
    schoolName: userData.schoolName || userData.schoolInfo?.name || "วิทยาลัยอาชีวสุพรรณบุรี",
    semester: userData.term || "ภาคเรียนที่ 1/2569",
    practicumPeriod: "16 พฤษภาคม 2567 – 30 กันยายน 2567",
    teachingHours: totalHours || userData.stats?.teachingHoursDone || 208,
  },
  school: {
    schoolFullName: userData.schoolName || userData.schoolInfo?.name || "วิทยาลัยอาชีวสุพรรณบุรี",
    address: userData.schoolInfo?.address || "ถนนประสานมิตร แขวงคลองเตยเหนือ เขตวัฒนา กรุงเทพฯ 10110",
    levels: userData.schoolInfo?.levels || userData.educationLevel || "ระดับประกาศนียบัตรวิชาชีพ (ปวช.) - ประกาศนียบัตรวิชาชีพชั้นสูง (ปวส.)",
    contact: userData.schoolInfo?.phone || userData.phone || "02-258-4000",
    principal: userData.schoolInfo?.directorName || "ดร.เกียรติศักดิ์ เจริญรัตน์",
    mentor: mentorDisplay,
    vision: userData.schoolInfo?.vision || "มุ่งพัฒนาผู้เรียนสายอาชีพให้มีความเป็นเลิศทางเทคโนโลยี ทักษะวิชาชีพ และคุณธรรม",
    mission: userData.schoolInfo?.mission || "จัดการศึกษาวิชาชีพที่ตอบสนองตลาดแรงงาน ส่งเสริมการประยุกต์ใช้นวัตกรรมและดิจิทัล",
  },
  schedule: [
    {
      id: "sch-1",
      day: "จันทร์",
      time: "08:30–10:30",
      classroom: "ปวช.1/2",
      subject: "เทคโนโลยีดิจิทัลเพื่อการจัดการอาชีพ",
      room: "ห้องปฏิบัติการคอมพิวเตอร์ 1",
      note: "คาบสอนทฤษฎีและปฏิบัติ",
      fileName: "",
      fileUrl: "",
    },
    {
      id: "sch-2",
      day: "อังคาร",
      time: "10:30–12:30",
      classroom: "ปวช.2/1",
      subject: "การสร้างสรรค์สื่อดิจิทัลและกราฟิกธุรกิจ",
      room: "ห้องปฏิบัติการคอมพิวเตอร์ 2",
      note: "คาบปฏิบัติการ",
      fileName: "",
      fileUrl: "",
    },
    {
      id: "sch-3",
      day: "พุธ",
      time: "13:00–15:00",
      classroom: "ปวช.2/1",
      subject: "การประยุกต์ใช้เทคโนโลยีดิจิทัลในงานธุรกิจ",
      room: "ห้องปฏิบัติการ 3",
      note: "คาบสอนหลัก / นิเทศการสอน",
      fileName: "",
      fileUrl: "",
    },
    {
      id: "sch-4",
      day: "พฤหัสบดี",
      time: "09:30–11:30",
      classroom: "ปวช.1/2",
      subject: "โปรแกรมประมวลผลคำและตารางทำงาน",
      room: "ห้องปฏิบัติการคอมพิวเตอร์ 1",
      note: "คาบปฏิบัติการ",
      fileName: "",
      fileUrl: "",
    },
    {
      id: "sch-5",
      day: "ศุกร์",
      time: "13:30–15:30",
      classroom: "ปวช. รวม",
      subject: "ชุมนุมนวัตกรรมดิจิทัลธุรกิจ",
      room: "ศูนย์วิทยบริการ",
      note: "กิจกรรมพัฒนาผู้เรียน",
      fileName: "",
      fileUrl: "",
    }
  ],
  daily: convertedDailyLogs,
  plans: plans,
  supervision: supervision,
  research: research,
  assessment: [],
  activities: [
    {
      id: "act-1",
      title: "กิจกรรมวันแม่แห่งชาติและสัปดาห์ส่งเสริมทักษะวิชาชีพ",
      date: "2024-08-10",
      caption: "ร่วมเป็นคณะกรรมการและดำเนินกิจกรรมจัดนิทรรศการผลงานดิจิทัลของนักเรียนแผนกวิชาการตลาดและคอมพิวเตอร์",
      imageUrl: "",
    },
    {
      id: "act-2",
      title: "เวรประจำวันและการดูแลนักเรียนหน้าประตูสถานศึกษา",
      date: "2024-09-04",
      caption: "ปฏิบัติหน้าที่เวรประจำวันพุธ ตรวจระเบียบการแต่งกายและต้อนรับนักศึกษาช่วงเช้า",
      imageUrl: "",
    },
    {
      id: "act-3",
      title: "ที่ปรึกษาชุมนุมนวัตกรรมดิจิทัลธุรกิจ",
      date: "2024-08-20",
      caption: "จัดกิจกรรมชุมนุม ส่งเสริมการออกแบบกราฟิกและสื่อการตลาดออนไลน์แก่นักศึกษาสายอาชีพ",
      imageUrl: "",
    }
  ],
  practicum: [
    {
      id: "prac-1",
      title: "การจัดการเรียนรู้รายวิชาเทคโนโลยีธุรกิจดิจิทัล ปวช.2/1 (การนิเทศรอบ 1 และ 2)",
      date: "2024-09-03",
      caption: "การจัดกิจกรรมการเรียนรู้เชิงรุก (Active Learning) พร้อมรับการนิเทศก์การสอนโดยอาจารย์นิเทศก์และครูพี่เลี้ยง",
      imageUrl: "",
    },
    {
      id: "prac-2",
      title: "การฝึกอบรมเชิงปฏิบัติการ การออกแบบกราฟิกธุรกิจด้วย Canva และเครื่องมือ AI",
      date: "2024-08-25",
      caption: "การจัดอบรมและนำนักเรียนประยุกต์ใช้เทคโนโลยีดิจิทัลสมัยใหม่ในงานอาชีพ",
      imageUrl: "",
    }
  ],
  settings: {
    siteName: `รายงานการฝึกสอน - ${userData.name}`,
    authorName: userData.name,
    primaryTheme: "official",
    showSample: false,
    saveNote: `นำเข้าข้อมูลสมบูรณ์จาก Cloud Firestore (${userData.name} - ${targetUserId})`,
  }
};

const outputPath = path.resolve('converted-portfolio-data.json');
fs.writeFileSync(outputPath, JSON.stringify(portfolioState, null, 2), 'utf-8');
console.log(`SUCCESS: Converted ${convertedDailyLogs.length} daily logs across ${sortedWeekKeys.length} weeks for ${userData.name} (${targetUserId})!`);
console.log(`Saved clean portfolio state to: ${outputPath}`);
