import React from 'react';
import { Database, AlertCircle } from 'lucide-react';

interface ProgressBarProps {
  percentage: number;
  isDirty: boolean;
  lastSaved: string;
  onSaveNow: () => void;
  onReset: () => void;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  percentage,
  isDirty,
  lastSaved,
  onSaveNow,
  onReset,
}) => {
  return (
    <div className="space-y-4 mb-6 no-print">
      <div className="border border-[#d7e5f5] rounded-2xl bg-white p-4 shadow-sm flex flex-col md:flex-row md:items-center gap-4">
        <div className="flex-1">
          <div className="flex justify-between gap-3 text-sm font-bold text-[#174a80]">
            <span>ความคืบหน้าการกรอกข้อมูลรวม</span>
            <span>{percentage}%</span>
          </div>
          <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-blue-100">
            <div
              className="h-full rounded-full bg-[#1267d6] transition-all duration-500"
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm font-semibold text-[#315272]">
          <Database className="w-4 h-4 text-blue-600" />
          <span>{lastSaved ? `บันทึกล่าสุด ${lastSaved}` : 'พร้อมแก้ไข'}</span>
        </div>
      </div>

      <div
        className={`rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 border transition-colors ${
          isDirty
            ? 'bg-amber-50 border-amber-200 text-amber-900'
            : 'bg-emerald-50 border-emerald-200 text-emerald-800'
        }`}
      >
        <div className="flex items-center gap-2 text-sm font-bold">
          {isDirty ? (
            <>
              <AlertCircle className="w-4 h-4 text-amber-600" />
              <span>มีการแก้ไขที่ยังไม่ได้บันทึก</span>
            </>
          ) : (
            <span>ข้อมูลเป็นปัจจุบัน</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isDirty && (
            <button
              type="button"
              onClick={onReset}
              className="px-3 py-1.5 rounded-lg text-xs font-bold bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 transition-colors"
            >
              ยกเลิกการแก้ไข
            </button>
          )}
          <button
            type="button"
            onClick={onSaveNow}
            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-[#1267d6] text-white hover:bg-[#0b55b5] transition-colors"
          >
            บันทึกทันที
          </button>
        </div>
      </div>
    </div>
  );
};

