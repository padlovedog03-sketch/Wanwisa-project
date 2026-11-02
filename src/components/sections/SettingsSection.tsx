import React from 'react';
import { AppSettings } from '../../types/portfolio';
import { Save, Printer } from 'lucide-react';

interface SettingsSectionProps {
  settings: AppSettings;
  onChange: (updated: AppSettings) => void;
  onSave: () => void;
  onPrint: () => void;
  onClearSection: (sectionKey: 'schedule' | 'daily' | 'plans' | 'activities') => void;
}

export const SettingsSection: React.FC<SettingsSectionProps> = ({
  settings,
  onChange,
  onSave,
  onPrint,
  onClearSection,
}) => {
  const handleChange = (field: keyof AppSettings, value: any) => {
    onChange({
      ...settings,
      [field]: value,
    });
  };

  return (
    <div className="border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-xl font-bold text-[#0c3574]">ตั้งค่าเว็บไซต์และการบันทึก</h3>
          <p className="text-xs text-[#587895] mt-1">กำหนดธีมสี ชื่อเว็บไซต์ และการพิมพ์รายงานออกเป็น PDF</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onPrint}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
          >
            <Printer className="w-3.5 h-3.5" />
            พิมพ์ / PDF
          </button>
          <button
            type="button"
            onClick={onSave}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-[#1267d6] text-white hover:bg-[#0b55b5] transition-colors"
          >
            <Save className="w-3.5 h-3.5" />
            บันทึก
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <label className="block mb-1 text-xs font-bold text-[#315272]">ชื่อเว็บไซต์ / แฟ้มสะสมงาน</label>
          <input
            type="text"
            value={settings.siteName}
            onChange={(e) => handleChange('siteName', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>

        <div>
          <label className="block mb-1 text-xs font-bold text-[#315272]">ข้อมูลผู้จัดทำสำหรับส่วนท้าย</label>
          <input
            type="text"
            value={settings.authorName}
            onChange={(e) => handleChange('authorName', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>

        <div>
          <label className="block mb-1 text-xs font-bold text-[#315272]">สีหรือธีม</label>
          <select
            value={settings.primaryTheme}
            onChange={(e) => handleChange('primaryTheme', e.target.value as any)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
          >
            <option value="official">สีน้ำเงินทางการ (Official Blue)</option>
            <option value="light">ฟ้าอ่อนสะอาด (Light Sky)</option>
            <option value="deep">น้ำเงินเข้ม (Deep Navy)</option>
          </select>
        </div>

        <div className="flex items-center gap-2 pt-6">
          <input
            id="showSample"
            type="checkbox"
            checked={settings.showSample}
            onChange={(e) => handleChange('showSample', e.target.checked)}
            className="w-4 h-4 rounded text-[#1267d6] focus:ring-blue-500"
          />
          <label htmlFor="showSample" className="text-xs font-bold text-[#315272] cursor-pointer">
            แสดงป้ายข้อมูลตัวอย่าง
          </label>
        </div>

        <div className="md:col-span-2">
          <label className="block mb-1 text-xs font-bold text-[#315272]">หมายเหตุการบันทึก</label>
          <textarea
            rows={2}
            value={settings.saveNote}
            onChange={(e) => handleChange('saveNote', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>
      </div>

      <div className="border-t border-slate-200 pt-5 space-y-3">
        <h4 className="text-sm font-bold text-red-700">ล้างข้อมูลเฉพาะส่วน</h4>
        <p className="text-xs text-[#587895]">เลือกส่วนที่ต้องการล้าง แล้วกดบันทึกเพื่อยืนยันการเปลี่ยนแปลง</p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onClearSection('schedule')}
            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
          >
            ล้างตารางสอน
          </button>
          <button
            type="button"
            onClick={() => onClearSection('daily')}
            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
          >
            ล้างบันทึกรายวัน
          </button>
          <button
            type="button"
            onClick={() => onClearSection('plans')}
            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
          >
            ล้างแผนการสอน
          </button>
          <button
            type="button"
            onClick={() => onClearSection('activities')}
            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
          >
            ล้างรูปกิจกรรม
          </button>
        </div>
      </div>
    </div>
  );
};
