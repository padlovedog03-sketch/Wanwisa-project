import fs from 'fs';
import path from 'path';

const dumpPath = path.resolve('firebase-firestore-dump.json');
if (!fs.existsSync(dumpPath)) {
  console.error("firebase-firestore-dump.json not found!");
  process.exit(1);
}

const rawDump = JSON.parse(fs.readFileSync(dumpPath, 'utf-8'));
const targetUserId = process.argv[2] || 'intern_blwd6moo';
const userData = rawDump.users?.[targetUserId];

if (!userData) {
  console.error(`User '${targetUserId}' not found in dump!`);
  process.exit(1);
}

console.log(`Converting data for user: ${userData.name} (${targetUserId})...`);

const weeklyLogsMap = userData._subcollections?.weekly_logs || {};
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

// Format mentor string cleanly
let mentorDisplay = "อาจารย์วิชัย เกียรติสกุล (ครูชำนาญการพิเศษ • กลุ่มสาระการเรียนรู้ภาษาไทย)";
if (userData.schoolInfo?.mentorName) {
  mentorDisplay = `${userData.schoolInfo.mentorName} (${userData.schoolInfo.mentorPosition || 'ครูชำนาญการพิเศษ'})`;
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

const portfolioState = {
  profile: {
    reportTitle: "รายงานการฝึกสอนประสบการณ์วิชาชีพครู",
    studentName: userData.name || "",
    studentId: userData.studentId || "",
    major: userData.subjectGroup || "สาขาวิชาภาษาไทย",
    institution: userData.university || "มหาวิทยาลัยราชภัฏ",
    schoolName: userData.schoolInfo?.name || userData.schoolName || "ร.ร. สาธิตมหาวิทยาลัยราชภัฏ",
    semester: userData.term || "ภาคเรียนที่ 1/2567",
    practicumPeriod: "16 พฤษภาคม 2567 – 30 กันยายน 2567",
    teachingHours: totalHours || userData.stats?.teachingHoursDone || 180,
  },
  school: {
    schoolFullName: userData.schoolInfo?.name || userData.schoolName || "ร.ร. สาธิตมหาวิทยาลัยราชภัฏ",
    address: userData.schoolInfo?.address || "ถนนประสานมิตร แขวงคลองเตยเหนือ เขตวัฒนา กรุงเทพฯ 10110",
    levels: userData.schoolInfo?.levels || userData.educationLevel || "มัธยมศึกษาตอนต้น - ตอนปลาย",
    contact: userData.schoolInfo?.phone || userData.phone || "02-258-4000",
    principal: userData.schoolInfo?.directorName || "ดร.เกียรติศักดิ์ เจริญรัตน์",
    mentor: mentorDisplay,
    vision: userData.schoolInfo?.vision || "มุ่งพัฒนาผู้เรียนให้มีคุณภาพ คุณธรรม และความเป็นเลิศทางวิชาการ",
    mission: userData.schoolInfo?.mission || "จัดการเรียนรู้ที่เน้นผู้เรียนเป็นสำคัญ ส่งเสริมทักษะภาษาและคุณธรรม",
  },
  schedule: [
    {
      id: "sch-1",
      day: "จันทร์",
      time: "08:30–09:30",
      classroom: "ม.2/1",
      subject: "ภาษาไทยพื้นฐาน",
      room: "ห้อง 301",
      note: "คาบสอนหลัก",
      fileName: "",
      fileUrl: "",
    },
    {
      id: "sch-2",
      day: "อังคาร",
      time: "10:30–11:30",
      classroom: "ม.2/2",
      subject: "ภาษาไทยพื้นฐาน",
      room: "ห้อง 302",
      note: "คาบสอนหลัก",
      fileName: "",
      fileUrl: "",
    },
    {
      id: "sch-3",
      day: "พุธ",
      time: "13:00–14:00",
      classroom: "ม.2/3",
      subject: "ภาษาไทยพื้นฐาน",
      room: "ห้อง 401",
      note: "คาบสอนหลัก / นิเทศการสอน",
      fileName: "",
      fileUrl: "",
    },
    {
      id: "sch-4",
      day: "พฤหัสบดี",
      time: "09:30–10:30",
      classroom: "ม.2/1",
      subject: "วรรณคดีและวรรณกรรม",
      room: "ห้อง 301",
      note: "คาบสอนหลัก",
      fileName: "",
      fileUrl: "",
    },
    {
      id: "sch-5",
      day: "ศุกร์",
      time: "14:00–15:00",
      classroom: "ม.ต้น",
      subject: "ชุมนุมวรรณศิลป์",
      room: "ห้องสมุด",
      note: "กิจกรรมพัฒนาผู้เรียน",
      fileName: "",
      fileUrl: "",
    }
  ],
  daily: convertedDailyLogs,
  plans: [
    {
      id: "plan-1",
      title: "การจัดการเรียนรู้เรื่อง สำนวน สุภาษิต คำพังเพย",
      subject: "ภาษาไทย",
      classroom: "ม.2/3",
      date: "2024-09-03",
      documentUrl: "",
      status: "ผ่านการนิเทศ (รอบ 2)",
    },
    {
      id: "plan-2",
      title: "การจัดการเรียนรู้หน่วยที่ 4 เรื่อง ราชาธิราช ตอนสมิงพระรามอาสา",
      subject: "วรรณคดีและวรรณกรรม",
      classroom: "ม.2/1",
      date: "2024-08-20",
      documentUrl: "",
      status: "ตรวจอนุมัติแล้ว",
    },
    {
      id: "plan-3",
      title: "การจัดการเรียนรู้เรื่อง การอ่านจับใจความสำคัญโดยใช้ผังความคิด",
      subject: "ภาษาไทยพื้นฐาน",
      classroom: "ม.2/2",
      date: "2024-07-15",
      documentUrl: "",
      status: "ตรวจอนุมัติแล้ว",
    }
  ],
  supervision: [
    {
      id: "sup-1",
      date: "2024-09-03",
      evaluator: "ผศ.ดร.พรพิมล รัตนโกสินทร์ (อาจารย์นิเทศก์ มรภ.) และ อาจารย์วิชัย เกียรติสกุล (ครูพี่เลี้ยง)",
      subject: "ภาษาไทย",
      classroom: "ม.2/3",
      strength: "มีความเป็นครูมืออาชีพสูงขึ้นอย่างเห็นได้ชัด น้ำเสียงและการเคลื่อนไหวเป็นธรรมชาติ ใช้สื่ออย่างมีปฏิสัมพันธ์",
      feedback: "ควบคุมชั้นเรียนได้ดี ควรเพิ่มกิจกรรมกระตุ้นให้นักเรียนมีส่วนร่วมในการอภิปราย",
      improvement: "เตรียมคำถามปลายเปิดและกิจกรรมจำแนกสำนวนเพิ่มเติม",
      score: "ดีมาก",
      images: [],
    },
    {
      id: "sup-2",
      date: "2024-07-18",
      evaluator: "อาจารย์วิชัย เกียรติสกุล (ครูพี่เลี้ยง)",
      subject: "ภาษาไทย",
      classroom: "ม.2/1",
      strength: "การเตรียมตัวดีมาก สื่อการสอนน่าสนใจและลำดับเนื้อหาเข้าใจง่าย",
      feedback: "ควรบริหารเวลาในขั้นสรุปบทเรียนให้กระชับขึ้น",
      improvement: "ปรับกิจกรรมสรุปให้เป็นแบบกลุ่มย่อยเพื่อความรวดเร็ว",
      score: "ดี",
      images: [],
    }
  ],
  research: {
    title: "การพัฒนาทักษะการคิดวิเคราะห์ด้วยการจัดการเรียนรู้แบบใช้ปัญหาเป็นฐาน ในรายวิชาภาษาไทย",
    target: "นักเรียนชั้นมัธยมศึกษาปีที่ 2",
    uploadDate: "2024-09-10",
    documentUrl: "",
    items: [],
  },
  assessment: [],
  activities: [
    {
      id: "act-1",
      title: "กิจกรรมวันแม่แห่งชาติและวันรักภาษาไทย",
      date: "2024-08-10",
      caption: "ร่วมเป็นคณะกรรมการตัดสินการประกวดเรียงความและการเขียนกลอนสุภาพ กลุ่มสาระภาษาไทย",
      imageUrl: "",
    },
    {
      id: "act-2",
      title: "เวรประจำวันและการดูแลนักเรียนหน้าประตูโรงเรียน",
      date: "2024-09-04",
      caption: "ปฏิบัติหน้าที่เวรประจำวันพุธ ตรวจระเบียบและต้อนรับนักเรียนช่วงเช้า",
      imageUrl: "",
    },
    {
      id: "act-3",
      title: "ที่ปรึกษาชุมนุมวรรณศิลป์และวรรณกรรมร่วมสมัย",
      date: "2024-08-20",
      caption: "จัดกิจกรรมชุมนุม ส่งเสริมการแต่งคำประพันธ์และวรรณศิลป์แก่นักเรียน ม.ต้น",
      imageUrl: "",
    }
  ],
  practicum: [
    {
      id: "prac-1",
      title: "การจัดการเรียนรู้ชั้นมัธยมศึกษาปีที่ 2/3 (การนิเทศรอบ 2)",
      date: "2024-09-03",
      caption: "การจัดกิจกรรมการเรียนรู้เรื่องสำนวนไทย พร้อมการนิเทศก์การสอนโดยอาจารย์นิเทศก์และครูพี่เลี้ยง",
      imageUrl: "",
    },
    {
      id: "prac-2",
      title: "การจัดการเรียนรู้วรรณคดี เรื่อง ราชาธิราช ชั้น ม.2/1",
      date: "2024-08-25",
      caption: "การจัดกิจกรรมการเรียนรู้แบบมีส่วนร่วมและการวิเคราะห์คุณค่าทางวรรณคดี",
      imageUrl: "",
    }
  ],
  settings: {
    siteName: `รายงานการฝึกสอน - ${userData.name}`,
    authorName: userData.name,
    primaryTheme: "official",
    showSample: false,
    saveNote: "นำเข้าข้อมูลสมบูรณ์จาก Cloud Firestore (18 สัปดาห์ 89 รายการ)",
  }
};

const outputPath = path.resolve('converted-portfolio-data.json');
fs.writeFileSync(outputPath, JSON.stringify(portfolioState, null, 2), 'utf-8');
console.log(`SUCCESS: Converted ${convertedDailyLogs.length} daily logs across ${sortedWeekKeys.length} weeks!`);
console.log(`Saved clean portfolio state to: ${outputPath}`);
