import React, { useState } from 'react';
import {
  GraduationCap,
  Menu,
  House,
  Building2,
  CalendarDays,
  NotebookPen,
  BookOpenCheck,
  ClipboardCheck,
  Microscope,
  BadgeCheck,
  Images,
  Presentation,
  Settings,
} from 'lucide-react';
import { SectionKey } from '../../types/portfolio';

interface HeaderProps {
  activeSection: SectionKey;
  onSelectSection: (key: SectionKey) => void;
  siteName: string;
}

const NAV_ITEMS: Array<{ key: SectionKey; label: string; icon: React.ElementType }> = [
  { key: 'home', label: 'หน้าแรก', icon: House },
  { key: 'school', label: 'ข้อมูลสถานศึกษา', icon: Building2 },
  { key: 'schedule', label: 'ตารางสอน', icon: CalendarDays },
  { key: 'daily', label: 'บันทึกรายวัน', icon: NotebookPen },
  { key: 'plans', label: 'แผนการสอน', icon: BookOpenCheck },
  { key: 'supervision', label: 'นิเทศการสอน', icon: ClipboardCheck },
  { key: 'research', label: 'วิจัยในชั้นเรียน', icon: Microscope },
  { key: 'assessment', label: 'แบบประเมินสมรรถนะ', icon: BadgeCheck },
  { key: 'activities', label: 'รูปกิจกรรม', icon: Images },
  { key: 'practicum', label: 'รูปฝึกสอน', icon: Presentation },
  { key: 'settings', label: 'ตั้งค่า', icon: Settings },
];

export const Header: React.FC<HeaderProps> = ({ activeSection, onSelectSection, siteName }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 shadow-lg no-print bg-[#0c3574]">
      <div className="w-full max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 shrink-0 grid place-items-center rounded-xl bg-[#1b75df] text-white">
            <GraduationCap className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <p className="text-blue-200 text-xs font-semibold">แฟ้มสะสมผลงานการฝึกประสบการณ์วิชาชีพครู</p>
            <h1 className="text-white font-bold text-lg md:text-xl truncate leading-tight">{siteName}</h1>
          </div>
        </div>

        <button
          type="button"
          className="md:hidden p-2 rounded-lg text-white hover:bg-white/10"
          onClick={() => setMobileMenuOpen((prev) => !prev)}
          aria-label="เปิดหรือปิดเมนู"
        >
          <Menu className="w-6 h-6" />
        </button>

        <nav className="hidden md:flex gap-1 items-center overflow-x-auto" aria-label="เมนูหลัก">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.key;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => onSelectSection(item.key)}
                className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-bold whitespace-nowrap transition-colors ${
                  isActive ? 'bg-white/20 text-white' : 'text-blue-100 hover:bg-white/10 hover:text-white'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {mobileMenuOpen && (
        <nav className="md:hidden bg-[#082b60] px-4 py-3 border-t border-white/10 grid grid-cols-2 gap-2" aria-label="เมนูมือถือ">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.key;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => {
                  onSelectSection(item.key);
                  setMobileMenuOpen(false);
                }}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-bold transition-colors ${
                  isActive ? 'bg-white/20 text-white' : 'text-blue-100 hover:bg-white/10 hover:text-white'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      )}
    </header>
  );
};
