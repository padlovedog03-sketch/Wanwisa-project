import React from 'react';
import { ResearchData } from '../../types/portfolio';
import { Save, ExternalLink } from 'lucide-react';
import { isValidHttpUrl } from '../../utils/validation';

interface ResearchSectionProps {
  research: ResearchData;
  onChange: (updated: ResearchData) => void;
  onSave: () => void;
}

export const ResearchSection: React.FC<ResearchSectionProps> = ({
  research,
  onChange,
  onSave,
}) => {
  const handleChange = (field: keyof ResearchData, value: any) => {
    onChange({
      ...research,
      [field]: value,
    });
  };

  return (
    <div className="border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-xl font-bold text-[#0c3574]">วิจัยในชั้นเรียน</h3>
          <p className="text-xs text-[#587895] mt-1">แนบเอกสารและข้อมูลกำกับงานวิจัยในชั้นเรียน</p>
        </div>
        <button
          type="button"
          onClick={onSave}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-[#1267d6] text-white hover:bg-[#0b55b5] transition-colors"
        >
          <Save className="w-3.5 h-3.5" />
          บันทึก
        </button>
      </div>

      <div className="border border-blue-100 bg-blue-50 rounded-2xl p-5 space-y-4">
        <div className="grid md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block mb-1 text-xs font-bold text-[#315272]">ชื่อเรื่องวิจัย</label>
            <input
              type="text"
              value={research.title}
              onChange={(e) => handleChange('title', e.target.value)}
              placeholder="เช่น การพัฒนาทักษะการคิดวิเคราะห์..."
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">กลุ่มเป้าหมาย / ชั้นเรียน</label>
            <input
              type="text"
              value={research.target}
              onChange={(e) => handleChange('target', e.target.value)}
              placeholder="เช่น นักเรียนชั้น ป.5/1"
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">วันที่เผยแพร่ / อัปโหลด</label>
            <input
              type="date"
              value={research.uploadDate}
              onChange={(e) => handleChange('uploadDate', e.target.value)}
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
            />
          </div>

          <div className="md:col-span-2">
            <label className="block mb-1 text-xs font-bold text-[#315272]">
              ลิงก์เอกสารฉบับเต็ม (Google Drive URL)
            </label>
            <div className="flex gap-2">
              <input
                type="url"
                value={research.documentUrl}
                onChange={(e) => handleChange('documentUrl', e.target.value)}
                placeholder="https://drive.google.com/..."
                className="flex-1 border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
              />
              {research.documentUrl && isValidHttpUrl(research.documentUrl) && (
                <a
                  href={research.documentUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold bg-blue-100 text-[#1267d6] hover:bg-blue-200 transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  เปิดไฟล์
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

