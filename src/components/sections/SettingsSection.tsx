import React, { useState } from 'react';
import { AppSettings, PortfolioState } from '../../types/portfolio';
import { Save, Printer, Download, Upload } from 'lucide-react';

interface SettingsSectionProps {
  settings: AppSettings;
  fullState: PortfolioState;
  onChange: (updated: AppSettings) => void;
  onSave: () => void;
  onPrint: () => void;
  onClearSection: (sectionKey: 'schedule' | 'daily' | 'plans' | 'activities') => void;
  onImportJson: (rawJson: string) => boolean;
  onShowToast: (msg: string, type?: 'success' | 'error') => void;
}

export const SettingsSection: React.FC<SettingsSectionProps> = ({
  settings,
  fullState,
  onChange,
  onSave,
  onPrint,
  onClearSection,
  onImportJson,
  onShowToast,
}) => {
  const [jsonInput, setJsonInput] = useState('');
  const [showImportBox, setShowImportBox] = useState(false);

  const handleChange = (field: keyof AppSettings, value: any) => {
    onChange({
      ...settings,
      [field]: value,
    });
  };

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(fullState, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `portfolio-backup-${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    onShowToast('ส่งออกไฟล์สำรอง JSON เรียบร้อยแล้ว');
  };

  const handleImportSubmit = () => {
    if (!jsonInput.trim()) {
      onShowToast('กรุณาวางข้อความ JSON ก่อนกดยืนยัน', 'error');
      return;
    }
    const success = onImportJson(jsonInput.trim());
    if (success) {
      onShowToast('นำเข้าข้อมูลสำเร็จเรียบร้อย ข้อมูลถูกอัปเดตลงระบบทันที');
      setJsonInput('');
      setShowImportBox(false);
    } else {
      onShowToast('รูปแบบไฟล์ JSON ไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง', 'error');
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) {
        const success = onImportJson(content);
        if (success) {
          onShowToast(`นำเข้าข้อมูลจากไฟล์ ${file.name} สำเร็จเรียบร้อย`);
        } else {
          onShowToast('โครงสร้าง JSON ในไฟล์ไม่ถูกต้อง', 'error');
        }
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  return (
    <div className="border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-xl font-bold text-[#0c3574]">ตั้งค่าเว็บไซต์และการบันทึก</h3>
          <p className="text-xs text-[#587895] mt-1">กำหนดธีมสี ชื่อเว็บไซต์ และการพิมพ์รายงานออกเป็น PDF</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onPrint}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
          >
            <Printer className="w-3.5 h-3.5" />
            พิมพ์ / PDF
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
        <div>
          <label className="block mb-1 text-xs font-bold text-[#315272]">ชื่อเว็บไซต์ / แฟ้มสะสมงาน</label>
          <input
            type="text"
            value={settings.siteName}
            onChange={(e) => handleChange('siteName', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>

        <div>
          <label className="block mb-1 text-xs font-bold text-[#315272]">ข้อมูลผู้จัดทำสำหรับส่วนท้าย</label>
          <input
            type="text"
            value={settings.authorName}
            onChange={(e) => handleChange('authorName', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>

        <div>
          <label className="block mb-1 text-xs font-bold text-[#315272]">สีหรือธีม</label>
          <select
            value={settings.primaryTheme}
            onChange={(e) => handleChange('primaryTheme', e.target.value as any)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
          >
            <option value="official">สีน้ำเงินทางการ (Official Blue)</option>
            <option value="light">ฟ้าอ่อนสะอาด (Light Sky)</option>
            <option value="deep">น้ำเงินเข้ม (Deep Navy)</option>
          </select>
        </div>

        <div className="flex items-center gap-2 pt-6">
          <input
            id="showSample"
            type="checkbox"
            checked={settings.showSample}
            onChange={(e) => handleChange('showSample', e.target.checked)}
            className="w-4 h-4 rounded text-[#1267d6] focus:ring-blue-500"
          />
          <label htmlFor="showSample" className="text-xs font-bold text-[#315272] cursor-pointer">
            แสดงป้ายข้อมูลตัวอย่าง
          </label>
        </div>

        <div className="md:col-span-2">
          <label className="block mb-1 text-xs font-bold text-[#315272]">หมายเหตุการบันทึก</label>
          <textarea
            rows={2}
            value={settings.saveNote}
            onChange={(e) => handleChange('saveNote', e.target.value)}
            className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
          />
        </div>
      </div>

      {/* Data Backup & Migration Section */}
      <div className="border-t border-slate-200 pt-5 space-y-4">
        <div>
          <h4 className="text-sm font-bold text-[#0c3574]">นำเข้าและส่งออกข้อมูล (Data Backup & Migration)</h4>
          <p className="text-xs text-[#587895] mt-1">
            สำรองข้อมูลเป็นไฟล์ JSON หรือนำเข้าข้อมูลเดิมที่ Dump มาจาก Firebase / Canva
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={handleExportJson}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-blue-50 text-[#1267d6] hover:bg-blue-100 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            ดาวน์โหลดไฟล์สำรอง (Export JSON)
          </button>

          <label className="cursor-pointer inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors">
            <Upload className="w-3.5 h-3.5" />
            นำเข้าไฟล์ JSON จากเครื่อง
            <input
              type="file"
              accept=".json,application/json"
              className="hidden"
              onChange={handleFileUpload}
            />
          </label>

          <button
            type="button"
            onClick={() => setShowImportBox((prev) => !prev)}
            className="px-3.5 py-2 rounded-xl text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
          >
            {showImportBox ? 'ปิดช่องวางข้อความ' : 'วางข้อความ JSON ด้วยตนเอง'}
          </button>
        </div>

        {showImportBox && (
          <div className="p-4 rounded-xl border border-blue-100 bg-blue-50/50 space-y-3">
            <label className="block text-xs font-bold text-[#315272]">
              วางข้อความ JSON ที่ได้จาก Firebase Realtime Database หรือ LocalStorage ที่นี่:
            </label>
            <textarea
              rows={5}
              value={jsonInput}
              onChange={(e) => setJsonInput(e.target.value)}
              placeholder='{"profile": {...}, "schedule": [...]}'
              className="w-full border border-[#cbdcf2] rounded-lg p-2.5 text-xs font-mono bg-white focus:outline-none focus:border-[#1267d6]"
            />
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleImportSubmit}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-[#1267d6] text-white hover:bg-[#0b55b5] transition-colors"
              >
                ยืนยันการนำเข้าข้อมูล
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-slate-200 pt-5 space-y-3">
        <h4 className="text-sm font-bold text-red-700">ล้างข้อมูลเฉพาะส่วน</h4>
        <p className="text-xs text-[#587895]">เลือกส่วนที่ต้องการล้าง แล้วกดบันทึกเพื่อยืนยันการเปลี่ยนแปลง</p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onClearSection('schedule')}
            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
          >
            ล้างตารางสอน
          </button>
          <button
            type="button"
            onClick={() => onClearSection('daily')}
            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
          >
            ล้างบันทึกรายวัน
          </button>
          <button
            type="button"
            onClick={() => onClearSection('plans')}
            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
          >
            ล้างแผนการสอน
          </button>
          <button
            type="button"
            onClick={() => onClearSection('activities')}
            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
          >
            ล้างรูปกิจกรรม
          </button>
        </div>
      </div>
    </div>
  );
};
