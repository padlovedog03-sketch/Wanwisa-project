import React from 'react';
import { ScheduleItem } from '../../types/portfolio';
import { Plus, Trash2, ExternalLink, Save } from 'lucide-react';
import { isValidHttpUrl } from '../../utils/validation';

interface ScheduleSectionProps {
  schedule: ScheduleItem[];
  onChange: (updated: ScheduleItem[]) => void;
  onSave: () => void;
  onConfirmDelete: (task: () => void) => void;
}

export const ScheduleSection: React.FC<ScheduleSectionProps> = ({
  schedule,
  onChange,
  onSave,
  onConfirmDelete,
}) => {
  const handleAdd = () => {
    const newItem: ScheduleItem = {
      id: crypto.randomUUID(),
      day: 'จันทร์',
      time: '08:30–09:30',
      classroom: '',
      subject: '',
      room: '',
      note: '',
      fileName: '',
      fileUrl: '',
    };
    onChange([...schedule, newItem]);
  };

  const handleUpdate = (id: string, field: keyof ScheduleItem, value: string) => {
    onChange(
      schedule.map((item) => (item.id === id ? { ...item, [field]: value } : item))
    );
  };

  const handleDelete = (id: string) => {
    onConfirmDelete(() => {
      onChange(schedule.filter((item) => item.id !== id));
    });
  };

  return (
    <div className="border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-xl font-bold text-[#0c3574]">ตารางสอน</h3>
          <p className="text-xs text-[#587895] mt-1">เพิ่ม แก้ไข หรือลบตารางสอน พร้อมแนบลิงก์ไฟล์เอกสารประกอบ</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleAdd}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-blue-50 text-[#1267d6] hover:bg-blue-100 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            เพิ่มแถว
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
        {schedule.length === 0 ? (
          <p className="p-8 text-center text-sm font-semibold text-slate-400 border border-dashed rounded-xl">
            ยังไม่มีรายการตารางสอน กด "เพิ่มแถว" เพื่อเริ่มต้น
          </p>
        ) : (
          schedule.map((item) => (
            <div key={item.id} className="relative border border-[#d7e5f5] rounded-xl p-4 bg-[#f9fcff]">
              <button
                type="button"
                onClick={() => handleDelete(item.id)}
                className="absolute top-3 right-3 p-1.5 rounded-lg text-red-500 hover:bg-red-50 transition-colors"
                title="ลบแถวนี้"
              >
                <Trash2 className="w-4 h-4" />
              </button>

              <div className="grid md:grid-cols-3 lg:grid-cols-4 gap-3 pr-8">
                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">วัน</label>
                  <input
                    type="text"
                    value={item.day}
                    onChange={(e) => handleUpdate(item.id, 'day', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">เวลา</label>
                  <input
                    type="text"
                    value={item.time}
                    onChange={(e) => handleUpdate(item.id, 'time', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">ชั้น/ห้อง</label>
                  <input
                    type="text"
                    value={item.classroom}
                    onChange={(e) => handleUpdate(item.id, 'classroom', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">วิชา</label>
                  <input
                    type="text"
                    value={item.subject}
                    onChange={(e) => handleUpdate(item.id, 'subject', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">ห้องเรียน</label>
                  <input
                    type="text"
                    value={item.room}
                    onChange={(e) => handleUpdate(item.id, 'room', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">หมายเหตุ</label>
                  <input
                    type="text"
                    value={item.note}
                    onChange={(e) => handleUpdate(item.id, 'note', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">ชื่อไฟล์เอกสาร</label>
                  <input
                    type="text"
                    value={item.fileName}
                    onChange={(e) => handleUpdate(item.id, 'fileName', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">ลิงก์ไฟล์ (URL)</label>
                  <input
                    type="url"
                    value={item.fileUrl}
                    onChange={(e) => handleUpdate(item.id, 'fileUrl', e.target.value)}
                    placeholder="https://example.com/file.pdf"
                    className="w-full border border-[#cbdcf2] rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>
              </div>

              {item.fileUrl && isValidHttpUrl(item.fileUrl) && (
                <div className="mt-3 flex items-center gap-2">
                  <a
                    href={item.fileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-[#1267d6] hover:underline"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    เปิดไฟล์ประกอบ ({item.fileName || 'เปิดลิงก์'})
                  </a>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

