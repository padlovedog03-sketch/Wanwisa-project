import React, { useState } from 'react';
import { DailyLogEntry, WorkDay } from '../../types/portfolio';
import { ArrowLeft, Save, Trash2 } from 'lucide-react';

interface DailyLogSectionProps {
  daily: DailyLogEntry[];
  onChange: (updated: DailyLogEntry[]) => void;
  onSaveAll: () => void;
  onConfirmClear: (task: () => void) => void;
}

const WORK_DAYS: WorkDay[] = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์'];

export const DailyLogSection: React.FC<DailyLogSectionProps> = ({
  daily,
  onChange,
  onSaveAll,
  onConfirmClear,
}) => {
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null);
  const [selectedDayIndex, setSelectedDayIndex] = useState<number>(0);

  const getDayEntry = (week: number, dayIndex: number): DailyLogEntry | undefined => {
    return daily.find((item) => item.week === week && item.dayIndex === dayIndex);
  };

  const handleSaveDay = (entryData: Partial<DailyLogEntry>) => {
    if (selectedWeek === null) return;
    const existing = getDayEntry(selectedWeek, selectedDayIndex);
    const day = WORK_DAYS[selectedDayIndex];

    const updatedEntry: DailyLogEntry = {
      id: existing?.id || crypto.randomUUID(),
      week: selectedWeek,
      dayIndex: selectedDayIndex,
      day,
      date: entryData.date || new Date().toISOString().slice(0, 10),
      start: entryData.start || '08:00',
      end: entryData.end || '16:00',
      activity: entryData.activity || '',
      learning: entryData.learning || '',
      problem: entryData.problem || '',
      solution: entryData.solution || '',
      note: entryData.note || '',
    };

    const nextList = daily.filter(
      (item) => !(item.week === selectedWeek && item.dayIndex === selectedDayIndex)
    );
    onChange([...nextList, updatedEntry]);
  };

  const handleClearDay = () => {
    if (selectedWeek === null) return;
    onConfirmClear(() => {
      onChange(
        daily.filter(
          (item) => !(item.week === selectedWeek && item.dayIndex === selectedDayIndex)
        )
      );
    });
  };

  const currentEntry = selectedWeek !== null ? getDayEntry(selectedWeek, selectedDayIndex) : undefined;

  return (
    <div className="border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-xl font-bold text-[#0c3574]">บันทึกรายวัน (18 สัปดาห์)</h3>
          <p className="text-xs text-[#587895] mt-1">
            เลือกดูสัปดาห์ที่ 1–18 และบันทึกผลการฝึกสอนรายวันจันทร์ถึงศุกร์
          </p>
        </div>
        <div className="flex gap-2">
          {selectedWeek !== null && (
            <button
              type="button"
              onClick={() => setSelectedWeek(null)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              กลับหน้ารวม
            </button>
          )}
          <button
            type="button"
            onClick={onSaveAll}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-[#1267d6] text-white hover:bg-[#0b55b5] transition-colors"
          >
            <Save className="w-3.5 h-3.5" />
            บันทึกทั้งหมด
          </button>
        </div>
      </div>

      {selectedWeek === null ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 18 }, (_, i) => i + 1).map((week) => {
            const count = WORK_DAYS.filter((_, dayIdx) => Boolean(getDayEntry(week, dayIdx))).length;
            const isComplete = count === 5;
            return (
              <button
                key={week}
                type="button"
                onClick={() => {
                  setSelectedWeek(week);
                  setSelectedDayIndex(0);
                }}
                className="text-left border border-[#cfe0f5] rounded-xl p-4 bg-[#f8fbff] hover:border-[#1267d6] hover:shadow-md transition-all cursor-pointer"
              >
                <div className="flex justify-between items-center">
                  <strong className="text-sm font-bold text-[#0c3574]">สัปดาห์ที่ {week}</strong>
                  <span
                    className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                      isComplete ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {isComplete ? 'ครบแล้ว' : 'ยังไม่ครบ'}
                  </span>
                </div>
                <p className="mt-2 text-xs text-[#587895]">บันทึกแล้ว {count} จาก 5 วัน</p>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-blue-100">
                  <div className="h-full bg-[#1267d6]" style={{ width: `${count * 20}%` }} />
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-2">
            {WORK_DAYS.map((day, idx) => {
              const hasEntry = Boolean(getDayEntry(selectedWeek, idx));
              const isActive = selectedDayIndex === idx;
              return (
                <button
                  key={day}
                  type="button"
                  onClick={() => setSelectedDayIndex(idx)}
                  className={`flex-1 min-w-[100px] p-3 rounded-xl border text-left transition-all ${
                    isActive
                      ? 'border-[#1267d6] bg-blue-50 text-[#1053ad] shadow-sm'
                      : 'border-slate-200 bg-white hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <strong className="block text-xs font-bold">{day}</strong>
                  <span className="block mt-1 text-[11px] text-[#587895]">
                    {hasEntry ? 'บันทึกแล้ว' : 'ยังไม่มีข้อมูล'}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="border border-[#d7e5f5] rounded-xl p-5 bg-[#f9fcff] space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block mb-1 text-xs font-bold text-[#315272]">วันที่</label>
                <input
                  type="date"
                  value={currentEntry?.date || ''}
                  onChange={(e) => handleSaveDay({ ...currentEntry, date: e.target.value })}
                  className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">เวลาเริ่มงาน</label>
                  <input
                    type="time"
                    value={currentEntry?.start || '08:00'}
                    onChange={(e) => handleSaveDay({ ...currentEntry, start: e.target.value })}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>
                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">เวลาสิ้นสุด</label>
                  <input
                    type="time"
                    value={currentEntry?.end || '16:00'}
                    onChange={(e) => handleSaveDay({ ...currentEntry, end: e.target.value })}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>
              </div>

              <div className="md:col-span-2">
                <label className="block mb-1 text-xs font-bold text-[#315272]">รายละเอียดกิจกรรมการสอน / ภาระงาน</label>
                <textarea
                  rows={3}
                  value={currentEntry?.activity || ''}
                  onChange={(e) => handleSaveDay({ ...currentEntry, activity: e.target.value })}
                  className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                />
              </div>

              <div>
                <label className="block mb-1 text-xs font-bold text-[#315272]">สิ่งที่ได้เรียนรู้</label>
                <textarea
                  rows={2}
                  value={currentEntry?.learning || ''}
                  onChange={(e) => handleSaveDay({ ...currentEntry, learning: e.target.value })}
                  className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                />
              </div>

              <div>
                <label className="block mb-1 text-xs font-bold text-[#315272]">ปัญหา / อุปสรรค</label>
                <textarea
                  rows={2}
                  value={currentEntry?.problem || ''}
                  onChange={(e) => handleSaveDay({ ...currentEntry, problem: e.target.value })}
                  className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                />
              </div>

              <div>
                <label className="block mb-1 text-xs font-bold text-[#315272]">แนวทางแก้ไข</label>
                <textarea
                  rows={2}
                  value={currentEntry?.solution || ''}
                  onChange={(e) => handleSaveDay({ ...currentEntry, solution: e.target.value })}
                  className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                />
              </div>

              <div>
                <label className="block mb-1 text-xs font-bold text-[#315272]">หมายเหตุ</label>
                <textarea
                  rows={2}
                  value={currentEntry?.note || ''}
                  onChange={(e) => handleSaveDay({ ...currentEntry, note: e.target.value })}
                  className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                />
              </div>
            </div>

            <div className="flex justify-end pt-3 border-t border-slate-200">
              <button
                type="button"
                onClick={handleClearDay}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-red-600 hover:bg-red-50 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                ล้างข้อมูลวันนี้
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

