import React from 'react';
import { SchoolInfo } from '../../types/portfolio';
import { Save, RotateCcw } from 'lucide-react';

interface SchoolSectionProps {
  school: SchoolInfo;
  onChange: (updated: SchoolInfo) => void;
  onSave: () => void;
  onReset: () => void;
}

export const SchoolSection: React.FC<SchoolSectionProps> = ({
  school,
  onChange,
  onSave,
  onReset,
}) => {
  const handleChange = (field: keyof SchoolInfo, value: string) => {
    onChange({
      ...school,
      [field]: value,
    });
  };

  return (
    <div className="border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-xl font-bold text-[#0c3574]">ข้อมูลสถานศึกษา</h3>
          <p className="text-xs text-[#587895] mt-1">ข้อมูลพื้นฐาน วิสัยทัศน์ และผู้บริหารสถานศึกษาที่ฝึกสอน</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onReset}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            ยกเลิก
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
        <div className="md:col-span-2">
          <label className="block mb-1 text-xs font-bold text-[#315272]">ชื่อสถานศึกษา</label>
          <input
            type="text"
            value={school.schoolFullName}
            onChange={(e) => handleChange('schoolFullName', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>

        <div className="md:col-span-2">
          <label className="block mb-1 text-xs font-bold text-[#315272]">ที่อยู่</label>
          <textarea
            rows={2}
            value={school.address}
            onChange={(e) => handleChange('address', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>

        <div>
          <label className="block mb-1 text-xs font-bold text-[#315272]">ระดับชั้นที่เปิดสอน</label>
          <input
            type="text"
            value={school.levels}
            onChange={(e) => handleChange('levels', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>

        <div>
          <label className="block mb-1 text-xs font-bold text-[#315272]">ข้อมูลติดต่อ</label>
          <input
            type="text"
            value={school.contact}
            onChange={(e) => handleChange('contact', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>

        <div>
          <label className="block mb-1 text-xs font-bold text-[#315272]">ผู้บริหารสถานศึกษา</label>
          <input
            type="text"
            value={school.principal}
            onChange={(e) => handleChange('principal', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>

        <div>
          <label className="block mb-1 text-xs font-bold text-[#315272]">ครูพี่เลี้ยง</label>
          <input
            type="text"
            value={school.mentor}
            onChange={(e) => handleChange('mentor', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>

        <div>
          <label className="block mb-1 text-xs font-bold text-[#315272]">วิสัยทัศน์</label>
          <textarea
            rows={3}
            value={school.vision}
            onChange={(e) => handleChange('vision', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>

        <div>
          <label className="block mb-1 text-xs font-bold text-[#315272]">พันธกิจ</label>
          <textarea
            rows={3}
            value={school.mission}
            onChange={(e) => handleChange('mission', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>
      </div>
    </div>
  );
};
