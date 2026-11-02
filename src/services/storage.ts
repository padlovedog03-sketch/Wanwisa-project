import { PortfolioState } from '../types/portfolio';

export const INITIAL_PORTFOLIO_STATE: PortfolioState = {
  profile: {
    reportTitle: "รายงานการฝึกสอนประสบการณ์วิชาชีพครู",
    studentName: "นางสาวตัวอย่าง ครูดี",
    studentId: "6612345678",
    major: "สาขาวิชาการประถมศึกษา",
    institution: "มหาวิทยาลัยตัวอย่าง",
    schoolName: "โรงเรียนตัวอย่างวิทยา",
    semester: "ภาคเรียนที่ 1 / ปีการศึกษา 2569",
    practicumPeriod: "1 มิถุนายน – 30 กันยายน 2569",
    teachingHours: 48,
  },
  school: {
    schoolFullName: "โรงเรียนตัวอย่างวิทยา",
    address: "123 ถนนสุขุมวิท ตำบลตัวอย่าง อำเภอเมือง จังหวัดขอนแก่น",
    levels: "อนุบาล – มัธยมศึกษาตอนต้น",
    contact: "043-000-000",
    principal: "นายตัวอย่าง ใจดี",
    mentor: "นางครูตัวอย่าง แสงงาม",
    vision: "มุ่งพัฒนาผู้เรียนให้มีคุณภาพ มีความสุข และเป็นพลเมืองดี",
    mission: "จัดการเรียนรู้ที่เน้นผู้เรียนเป็นสำคัญและส่งเสริมการใช้เทคโนโลยี",
  },
  schedule: [
    {
      id: "sch-1",
      day: "จันทร์",
      time: "08:30–09:30",
      classroom: "ป.5/1",
      subject: "วิทยาศาสตร์",
      room: "ห้อง 501",
      note: "ข้อมูลตัวอย่าง",
      fileName: "",
      fileUrl: "",
    },
  ],
  daily: [
    {
      id: "day-1-0",
      week: 1,
      dayIndex: 0,
      day: "จันทร์",
      date: "2026-06-01",
      start: "08:00",
      end: "16:00",
      activity: "สังเกตการจัดการเรียนรู้และช่วยเตรียมสื่อ",
      learning: "ได้เรียนรู้การบริหารชั้นเรียน",
      problem: "นักเรียนบางส่วนคุยกัน",
      solution: "ใช้สัญญาณและกิจกรรมกระตุ้นความสนใจ",
      note: "ข้อมูลตัวอย่าง",
    },
  ],
  plans: [
    {
      id: "plan-1",
      title: "สิ่งมีชีวิตและสิ่งแวดล้อม",
      subject: "วิทยาศาสตร์",
      classroom: "ป.5/1",
      date: "2026-06-10",
      documentUrl: "",
      status: "ร่างแผน",
    },
  ],
  supervision: [
    {
      id: "sup-1",
      date: "2026-06-15",
      evaluator: "นางครูตัวอย่าง แสงงาม",
      subject: "วิทยาศาสตร์",
      classroom: "ป.5/1",
      strength: "ใช้สื่อเหมาะสมและสื่อสารชัดเจน",
      feedback: "เพิ่มคำถามกระตุ้นการคิด",
      improvement: "เตรียมคำถามปลายเปิดเพิ่มขึ้น",
      score: "ดี",
      images: [],
    },
  ],
  research: {
    title: "การพัฒนาทักษะการคิดวิเคราะห์ด้วยการจัดการเรียนรู้แบบใช้ปัญหาเป็นฐาน",
    target: "นักเรียนชั้นประถมศึกษาปีที่ 5",
    uploadDate: "2026-06-20",
    documentUrl: "",
    items: [],
  },
  assessment: [],
  activities: [
    {
      id: "act-1",
      title: "กิจกรรมฐานการเรียนรู้",
      date: "2026-06-20",
      caption: "ข้อมูลตัวอย่างสำหรับคำบรรยายรูปกิจกรรม",
      imageUrl: "",
    },
  ],
  practicum: [
    {
      id: "prac-1",
      title: "การสอนวิทยาศาสตร์ ป.5/1",
      date: "2026-06-10",
      caption: "ข้อมูลตัวอย่างสำหรับคำบรรยายภาพฝึกสอน",
      imageUrl: "",
    },
  ],
  settings: {
    siteName: "รายงานการฝึกสอนประสบการณ์วิชาชีพครู",
    authorName: "ผู้จัดทำตัวอย่าง",
    primaryTheme: "official",
    showSample: true,
    saveNote: "",
  },
};

const LOCAL_STORAGE_KEY = "teaching-practice-report-data-v2";

export function loadLocalPortfolio(): PortfolioState {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) return INITIAL_PORTFOLIO_STATE;
    const parsed = JSON.parse(raw);
    return { ...INITIAL_PORTFOLIO_STATE, ...parsed };
  } catch {
    return INITIAL_PORTFOLIO_STATE;
  }
}

export function saveLocalPortfolio(state: PortfolioState): boolean {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(state));
    return true;
  } catch (error) {
    console.error("Failed to save to localStorage:", error);
    return false;
  }
}

/**
 * Syncs the portfolio state to PostgreSQL via Vercel Serverless Function (/api/portfolio)
 */
export async function syncWithPostgres(state: PortfolioState): Promise<boolean> {
  try {
    const res = await fetch('/api/portfolio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state),
    });
    return res.ok;
  } catch (err) {
    console.warn("Postgres sync skipped or failed (offline / local):", err);
    return false;
  }
}

/**
 * Fetches the latest portfolio state from PostgreSQL via Vercel Serverless Function
 */
export async function fetchFromPostgres(): Promise<PortfolioState | null> {
  try {
    const res = await fetch('/api/portfolio');
    if (!res.ok) return null;
    const result = await res.json();
    if (result.found && result.data) {
      return { ...INITIAL_PORTFOLIO_STATE, ...result.data };
    }
    return null;
  } catch (err) {
    console.warn("Could not fetch from Postgres:", err);
    return null;
  }
}

/**
 * Parses and maps Firebase dump JSON into valid PortfolioState
 */
export function importPortfolioFromJson(rawJson: string): PortfolioState {
  const parsed = JSON.parse(rawJson);
  let target = parsed;
  if (parsed.teachingPracticeReport && parsed.teachingPracticeReport.data) {
    target = parsed.teachingPracticeReport.data;
    if (parsed.teaching_internship && parsed.teaching_internship.research) {
      target.research = { ...target.research, ...parsed.teaching_internship.research };
    }
  } else if (parsed.data) {
    target = parsed.data;
  }

  return {
    ...INITIAL_PORTFOLIO_STATE,
    ...target,
    profile: { ...INITIAL_PORTFOLIO_STATE.profile, ...(target.profile || {}) },
    school: { ...INITIAL_PORTFOLIO_STATE.school, ...(target.school || {}) },
    settings: { ...INITIAL_PORTFOLIO_STATE.settings, ...(target.settings || {}) },
  };
}
