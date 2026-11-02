import React, { useRef } from 'react';
import { TeacherProfile } from '../../types/portfolio';
import { Save, RotateCcw, Camera } from 'lucide-react';
import { compressImageFile } from '../../utils/compression';

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
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const coverInputRef = useRef<HTMLInputElement>(null);

  const handleFieldChange = (field: keyof TeacherProfile, value: string | number) => {
    onChange({
      ...profile,
      [field]: field === 'teachingHours' ? Number(value) || 0 : value,
    });
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const compressed = await compressImageFile(file);
      onChange({
        ...profile,
        avatarUrl: compressed.compressedDataUrl,
      });
    } catch (err) {
      console.error('Failed to compress avatar:', err);
      alert('ไม่สามารถอัปโหลดรูปภาพได้ กรุณาใช้ไฟล์รูปภาพขนาดไม่เกิน 5MB');
    } finally {
      e.target.value = '';
    }
  };

  const handleCoverUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const compressed = await compressImageFile(file);
      onChange({
        ...profile,
        coverImageUrl: compressed.compressedDataUrl,
      });
    } catch (err) {
      console.error('Failed to compress cover image:', err);
      alert('ไม่สามารถอัปโหลดรูปภาพได้ กรุณาใช้ไฟล์รูปภาพขนาดไม่เกิน 5MB');
    } finally {
      e.target.value = '';
    }
  };

  return (
    <div className="space-y-6">
      {/* Hero Banner with Right-side Cover Image Slot (Full Bleed to edges) */}
      <div className="border border-[#d7e5f5] rounded-2xl md:rounded-3xl overflow-hidden bg-gradient-to-br from-white to-[#e8f3ff] shadow-sm flex flex-col md:flex-row items-stretch justify-between">
        <div className="flex-1 p-6 md:p-8 flex flex-col justify-center">
          <span className="inline-block rounded-full bg-blue-100 text-[#1053ad] text-xs font-bold px-3 py-1 mb-3 self-start">
            ข้อมูลตัวอย่าง • แก้ไขแทนที่ได้ทันที
          </span>
          <h2 className="text-2xl md:text-3xl font-extrabold text-[#0c3574]">
            {profile.reportTitle || 'รายงานการฝึกสอนประสบการณ์วิชาชีพครู'}
          </h2>
          <p className="mt-2 text-sm md:text-base text-[#496987] max-w-2xl">
            จัดเก็บรายละเอียดการฝึกสอน แผนการจัดการเรียนรู้ การนิเทศ และผลงานของคุณไว้ในรายงานเดียว
          </p>
        </div>

        {/* Cover Photo Slot (Full Bleed) */}
        <div className="w-full md:w-[36%] lg:w-[34%] min-h-[220px] md:min-h-full relative group shrink-0 bg-slate-100 self-stretch">
          <img
            src={profile.coverImageUrl || '/images/cover_internship.jpg'}
            alt="ภาพหน้าปกรายงาน"
            className="w-full h-full object-cover block"
          />
          <button
            type="button"
            onClick={() => coverInputRef.current?.click()}
            className="absolute inset-0 bg-black/40 text-white flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer text-xs font-medium gap-1.5"
            title="เปลี่ยนภาพหน้าปก"
          >
            <Camera className="w-5 h-5" />
            <span>เปลี่ยนภาพหน้าปก</span>
          </button>
          <input
            type="file"
            ref={coverInputRef}
            onChange={handleCoverUpload}
            accept="image/*"
            className="hidden"
          />
        </div>
      </div>

      {/* Main Profile Form with Left-side Avatar Slot */}
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

        <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
          {/* Avatar Circle Container */}
          <div className="flex flex-col items-center gap-2 shrink-0">
            <div className="w-28 h-28 rounded-full ring-4 ring-blue-100 overflow-hidden shadow-md relative group bg-emerald-50 cursor-pointer">
              <img
                src={profile.avatarUrl || '/images/avatar_wanwisa.png'}
                alt={profile.studentName || 'รูปผู้จัดทำ'}
                className="w-full h-full object-cover"
              />
              <button
                type="button"
                onClick={() => avatarInputRef.current?.click()}
                className="absolute inset-0 bg-black/40 text-white flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity rounded-full text-[11px] font-medium gap-1 cursor-pointer"
                title="เปลี่ยนรูปโปรไฟล์"
              >
                <Camera className="w-5 h-5" />
                <span>เปลี่ยนรูป</span>
              </button>
              <input
                type="file"
                ref={avatarInputRef}
                onChange={handleAvatarUpload}
                accept="image/*"
                className="hidden"
              />
            </div>
            <span className="text-[11px] text-[#587895] font-medium">รูปถ่ายผู้จัดทำ</span>
          </div>

          {/* Form Fields Grid */}
          <div className="flex-1 w-full grid md:grid-cols-2 lg:grid-cols-3 gap-4">
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
