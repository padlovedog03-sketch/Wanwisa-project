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

export type WorkDay = 'จันทร์' | 'อังคาร' | 'พุธ' | 'พฤหัสบดี' | 'ศุกร์';

export interface DailyLogEntry {
  id: string;
  week: number;
  dayIndex: number;
  day: WorkDay;
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

export interface CompressedImage {
  id: string;
  fileName: string;
  compressedDataUrl: string;
  compressedSize: number;
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
  images: CompressedImage[];
}

export interface ResearchData {
  title: string;
  target: string;
  uploadDate: string;
  documentUrl: string;
  items: Array<{ id: string; title: string; url: string }>;
}

export interface AssessmentItem {
  id: string;
  title: string;
  url: string;
  fileName?: string;
  pdfData?: string;
}

export interface GalleryItem {
  id: string;
  title: string;
  date: string;
  caption: string;
  imageUrl: string;
}

export interface AppSettings {
  siteName: string;
  authorName: string;
  primaryTheme: 'official' | 'light' | 'deep';
  showSample: boolean;
  saveNote: string;
}

export interface PortfolioState {
  profile: TeacherProfile;
  school: SchoolInfo;
  schedule: ScheduleItem[];
  daily: DailyLogEntry[];
  plans: LessonPlanItem[];
  supervision: SupervisionItem[];
  research: ResearchData;
  assessment: AssessmentItem[];
  activities: GalleryItem[];
  practicum: GalleryItem[];
  settings: AppSettings;
}

export type SectionKey =
  | 'home'
  | 'school'
  | 'schedule'
  | 'daily'
  | 'plans'
  | 'supervision'
  | 'research'
  | 'assessment'
  | 'activities'
  | 'practicum'
  | 'settings';
