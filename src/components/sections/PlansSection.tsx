import React from 'react';
import { LessonPlanItem } from '../../types/portfolio';
import { Plus, Trash2, ExternalLink, Save } from 'lucide-react';
import { isValidHttpUrl } from '../../utils/validation';

interface PlansSectionProps {
  plans: LessonPlanItem[];
  onChange: (updated: LessonPlanItem[]) => void;
  onSave: () => void;
  onConfirmDelete: (task: () => void) => void;
}

export const PlansSection: React.FC<PlansSectionProps> = ({
  plans,
  onChange,
  onSave,
  onConfirmDelete,
}) => {
  const handleAdd = () => {
    const newPlan: LessonPlanItem = {
      id: crypto.randomUUID(),
      title: '',
      subject: '',
      classroom: '',
      date: new Date().toISOString().slice(0, 10),
      documentUrl: '',
      status: 'ร่างแผน',
    };
    onChange([...plans, newPlan]);
  };

  const handleUpdate = (id: string, field: keyof LessonPlanItem, value: string) => {
    onChange(plans.map((p) => (p.id === id ? { ...p, [field]: value } : p)));
  };

  const handleDelete = (id: string) => {
    onConfirmDelete(() => {
      onChange(plans.filter((p) => p.id !== id));
    });
  };

  return (
    <div className="border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-xl font-bold text-[#0c3574]">แผนการสอน</h3>
          <p className="text-xs text-[#587895] mt-1">จัดเก็บแผนการจัดการเรียนรู้พร้อมลิงก์ไฟล์ Google Drive</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleAdd}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-blue-50 text-[#1267d6] hover:bg-blue-100 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            เพิ่มแผน
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

      <div className="space-y-4">
        {plans.length === 0 ? (
          <p className="p-8 text-center text-sm font-semibold text-slate-400 border border-dashed rounded-xl">
            ยังไม่มีรายการแผนการสอน กด "เพิ่มแผน" เพื่อเริ่มต้น
          </p>
        ) : (
          plans.map((plan) => (
            <div key={plan.id} className="relative border border-[#d7e5f5] rounded-xl p-4 bg-[#f9fcff]">
              <button
                type="button"
                onClick={() => handleDelete(plan.id)}
                className="absolute top-3 right-3 p-1.5 rounded-lg text-red-500 hover:bg-red-50 transition-colors"
                title="ลบแผนนี้"
              >
                <Trash2 className="w-4 h-4" />
              </button>

              <div className="grid md:grid-cols-2 gap-4 pr-8">
                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">ชื่อแผนการสอน</label>
                  <input
                    type="text"
                    value={plan.title}
                    onChange={(e) => handleUpdate(plan.id, 'title', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">วิชา</label>
                  <input
                    type="text"
                    value={plan.subject}
                    onChange={(e) => handleUpdate(plan.id, 'subject', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">ชั้น / ห้อง</label>
                  <input
                    type="text"
                    value={plan.classroom}
                    onChange={(e) => handleUpdate(plan.id, 'classroom', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">วันที่สอน</label>
                  <input
                    type="date"
                    value={plan.date}
                    onChange={(e) => handleUpdate(plan.id, 'date', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block mb-1 text-xs font-bold text-[#315272]">
                    ลิงก์เอกสารแผนการสอน (Google Drive URL)
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="url"
                      value={plan.documentUrl}
                      onChange={(e) => handleUpdate(plan.id, 'documentUrl', e.target.value)}
                      placeholder="https://drive.google.com/..."
                      className="flex-1 border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                    />
                    {plan.documentUrl && isValidHttpUrl(plan.documentUrl) && (
                      <a
                        href={plan.documentUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold bg-blue-50 text-[#1267d6] hover:bg-blue-100 transition-colors"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        เปิดไฟล์
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

