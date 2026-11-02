import React, { useRef } from 'react';
import { SchoolInfo } from '../../types/portfolio';
import { Save, RotateCcw, Camera } from 'lucide-react';
import { compressImageFile } from '../../utils/compression';

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
  const logoInputRef = useRef<HTMLInputElement>(null);

  const handleChange = (field: keyof SchoolInfo, value: string) => {
    onChange({
      ...school,
      [field]: value,
    });
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const compressed = await compressImageFile(file);
      onChange({
        ...school,
        logoUrl: compressed.compressedDataUrl,
      });
    } catch (err) {
      console.error('Failed to compress school logo:', err);
      alert('ไม่สามารถอัปโหลดรูปภาพได้ กรุณาใช้ไฟล์รูปภาพขนาดไม่เกิน 5MB');
    } finally {
      e.target.value = '';
    }
  };

  return (
    <div className="flex flex-col lg:flex-row items-stretch gap-6">
      {/* Left Card: School Logo / Emblem (matching Canva original) */}
      <div className="w-full lg:w-80 border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm flex flex-col items-center justify-center relative group min-h-[380px] shrink-0">
        <div className="w-full h-full flex flex-col items-center justify-center relative">
          <img
            src={school.logoUrl || '/images/school_logo.jpg'}
            alt="ตราสัญลักษณ์สถานศึกษา"
            className="w-56 h-56 md:w-64 md:h-64 object-contain transition-transform group-hover:scale-105"
          />
          <button
            type="button"
            onClick={() => logoInputRef.current?.click()}
            className="absolute inset-0 bg-black/40 text-white flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity rounded-xl text-xs font-medium gap-1.5 cursor-pointer"
            title="เปลี่ยนตราสัญลักษณ์สถานศึกษา"
          >
            <Camera className="w-6 h-6" />
            <span>เปลี่ยนตราสัญลักษณ์</span>
          </button>
          <input
            type="file"
            ref={logoInputRef}
            onChange={handleLogoUpload}
            accept="image/*"
            className="hidden"
          />
        </div>
        <span className="mt-3 text-xs font-medium text-[#587895]">ตราสัญลักษณ์สถานศึกษา</span>
      </div>

      {/* Right Card: School Information Form */}
      <div className="flex-1 border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm">
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
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div className="md:col-span-2">
            <label className="block mb-1 text-xs font-bold text-[#315272]">ที่อยู่</label>
            <textarea
              rows={2}
              value={school.address}
              onChange={(e) => handleChange('address', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">ระดับชั้นที่เปิดสอน</label>
            <input
              type="text"
              value={school.levels}
              onChange={(e) => handleChange('levels', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">ข้อมูลติดต่อ</label>
            <input
              type="text"
              value={school.contact}
              onChange={(e) => handleChange('contact', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">ผู้บริหารสถานศึกษา</label>
            <input
              type="text"
              value={school.principal}
              onChange={(e) => handleChange('principal', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">ครูพี่เลี้ยง</label>
            <input
              type="text"
              value={school.mentor}
              onChange={(e) => handleChange('mentor', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">วิสัยทัศน์</label>
            <textarea
              rows={3}
              value={school.vision}
              onChange={(e) => handleChange('vision', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">พันธกิจ</label>
            <textarea
              rows={3}
              value={school.mission}
              onChange={(e) => handleChange('mission', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
