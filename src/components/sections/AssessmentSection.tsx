import React, { useState } from 'react';
import { AssessmentItem } from '../../types/portfolio';
import { Plus, Trash2, Save, ExternalLink, FileText } from 'lucide-react';
import { isValidHttpUrl } from '../../utils/validation';

interface AssessmentSectionProps {
  assessment: AssessmentItem[];
  onChange: (updated: AssessmentItem[]) => void;
  onSave: () => void;
  onConfirmDelete: (task: () => void) => void;
  onShowToast: (msg: string, type?: 'success' | 'error') => void;
}

export const AssessmentSection: React.FC<AssessmentSectionProps> = ({
  assessment,
  onChange,
  onSave,
  onConfirmDelete,
  onShowToast,
}) => {
  const [title, setTitle] = useState('');
  const [url, setUrl] = useState('');

  const handleAdd = () => {
    if (!title.trim() && !url.trim()) {
      onShowToast('กรุณาระบุชื่อหรือลิงก์ของแบบประเมิน', 'error');
      return;
    }

    const newItem: AssessmentItem = {
      id: crypto.randomUUID(),
      title: title.trim() || 'แบบประเมินสมรรถนะ',
      url: url.trim(),
    };

    onChange([...assessment, newItem]);
    setTitle('');
    setUrl('');
    onShowToast('เพิ่มรายการแบบประเมินแล้ว');
  };

  const handleDelete = (id: string) => {
    onConfirmDelete(() => {
      onChange(assessment.filter((item) => item.id !== id));
    });
  };

  return (
    <div className="border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-xl font-bold text-[#0c3574]">แบบประเมินสมรรถนะทางวิชาชีพครู</h3>
          <p className="text-xs text-[#587895] mt-1">เพิ่มลิงก์หรือเอกสารประเมินสมรรถนะวิชาชีพ</p>
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
        <h4 className="text-xs font-bold text-[#174a80]">เพิ่มรายการใหม่</h4>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">ชื่อหรือคำอธิบาย</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="เช่น แบบประเมินสมรรถนะภาคเรียนที่ 1"
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
            />
          </div>
          <div>
            <label className="block mb-1 text-xs font-bold text-[#315272]">ลิงก์ที่เกี่ยวข้อง</label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
            />
          </div>
        </div>
        <button
          type="button"
          onClick={handleAdd}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-[#1267d6] text-white hover:bg-[#0b55b5] transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          เพิ่มรายการ
        </button>
      </div>

      <div className="space-y-3">
        {assessment.length === 0 ? (
          <p className="p-8 text-center text-sm font-semibold text-slate-400 border border-dashed rounded-xl">
            ยังไม่มีรายการแบบประเมิน
          </p>
        ) : (
          assessment.map((item) => (
            <div
              key={item.id}
              className="border border-[#d7e5f5] rounded-xl p-4 bg-[#f9fcff] flex flex-wrap items-center justify-between gap-3"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-100 text-[#1267d6] grid place-items-center">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <strong className="block text-sm font-bold text-[#0c3574]">{item.title}</strong>
                  <span className="block text-xs text-[#587895]">{item.url || 'ไม่มีลิงก์'}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {item.url && isValidHttpUrl(item.url) && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-blue-50 text-[#1267d6] hover:bg-blue-100 transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    เปิดลิงก์
                  </a>
                )}
                <button
                  type="button"
                  onClick={() => handleDelete(item.id)}
                  className="p-1.5 rounded-lg text-red-500 hover:bg-red-50 transition-colors"
                  title="ลบรายการ"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

