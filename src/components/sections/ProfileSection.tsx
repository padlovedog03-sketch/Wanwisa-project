import React from 'react';
import { TeacherProfile } from '../../types/portfolio';
import { Save, RotateCcw } from 'lucide-react';

interface ProfileSectionProps {
  profile: TeacherProfile;
  onChange: (updated: TeacherProfile) => void;
  onSave: () => void;
  onReset: () => void;
  stats: {
    dailyCount: number;
    plansCount: number;
    activitiesCount: number;
    hoursCount: number;
  };
}

export const ProfileSection: React.FC<ProfileSectionProps> = ({
  profile,
  onChange,
  onSave,
  onReset,
  stats,
}) => {
  const handleFieldChange = (field: keyof TeacherProfile, value: string | number) => {
    onChange({
      ...profile,
      [field]: field === 'teachingHours' ? Number(value) || 0 : value,
    });
  };

  return (
    <div className="space-y-6">
      <div className="border border-[#d7e5f5] rounded-3xl overflow-hidden bg-gradient-to-br from-white to-[#e8f3ff] shadow-sm p-6 md:p-8">
        <span className="inline-block rounded-full bg-blue-100 text-[#1053ad] text-xs font-bold px-3 py-1 mb-3">
          แฟ้มสะสมงานวิชาชีพครู • ปรับปรุงข้อมูลได้ตลอดเวลา
        </span>
        <h2 className="text-2xl md:text-3xl font-extrabold text-[#0c3574]">
          {profile.reportTitle || 'รายงานการฝึกสอนประสบการณ์วิชาชีพครู'}
        </h2>
        <p className="mt-2 text-sm md:text-base text-[#496987] max-w-2xl">
          จัดเก็บรายละเอียดการฝึกสอน แผนการจัดการเรียนรู้ การนิเทศ และผลงานทั้งหมดไว้ในระบบเดียว
        </p>
      </div>

      <div className="border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-4 border-b border-slate-100">
          <h3 className="text-xl font-bold text-[#0c3574]">ข้อมูลผู้จัดทำรายงาน</h3>
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

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">ชื่อรายงาน</label>
            <input
              type="text"
              value={profile.reportTitle}
              onChange={(e) => handleFieldChange('reportTitle', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">ชื่อ-นามสกุล</label>
            <input
              type="text"
              value={profile.studentName}
              onChange={(e) => handleFieldChange('studentName', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">รหัสนักศึกษา</label>
            <input
              type="text"
              value={profile.studentId}
              onChange={(e) => handleFieldChange('studentId', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">สาขาวิชา</label>
            <input
              type="text"
              value={profile.major}
              onChange={(e) => handleFieldChange('major', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">มหาวิทยาลัย</label>
            <input
              type="text"
              value={profile.institution}
              onChange={(e) => handleFieldChange('institution', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">สถานศึกษาฝึกสอน</label>
            <input
              type="text"
              value={profile.schoolName}
              onChange={(e) => handleFieldChange('schoolName', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">ภาคเรียน / ปีการศึกษา</label>
            <input
              type="text"
              value={profile.semester}
              onChange={(e) => handleFieldChange('semester', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">ช่วงเวลาฝึกสอน</label>
            <input
              type="text"
              value={profile.practicumPeriod}
              onChange={(e) => handleFieldChange('practicumPeriod', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">ชั่วโมงสอนรวม</label>
            <input
              type="number"
              min="0"
              value={profile.teachingHours}
              onChange={(e) => handleFieldChange('teachingHours', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1267d6] focus:ring-2 focus:ring-blue-100"
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="border border-[#d7e5f5] rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold text-[#54718e]">บันทึกรายวัน</p>
          <p className="text-3xl font-extrabold text-[#1267d6] mt-1">{stats.dailyCount}</p>
        </div>
        <div className="border border-[#d7e5f5] rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold text-[#54718e]">แผนการสอน</p>
          <p className="text-3xl font-extrabold text-[#1267d6] mt-1">{stats.plansCount}</p>
        </div>
        <div className="border border-[#d7e5f5] rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold text-[#54718e]">รูปกิจกรรม</p>
          <p className="text-3xl font-extrabold text-[#1267d6] mt-1">{stats.activitiesCount}</p>
        </div>
        <div className="border border-[#d7e5f5] rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold text-[#54718e]">ชั่วโมงสอนรวม</p>
          <p className="text-3xl font-extrabold text-[#1267d6] mt-1">{stats.hoursCount}</p>
        </div>
      </div>
    </div>
  );
};

