import React from 'react';
import { GalleryItem } from '../../types/portfolio';
import { Plus, Trash2, Save, ImagePlus } from 'lucide-react';
import { compressImageFile } from '../../utils/compression';

interface PracticumSectionProps {
  practicum: GalleryItem[];
  onChange: (updated: GalleryItem[]) => void;
  onSave: () => void;
  onConfirmDelete: (task: () => void) => void;
  onShowToast: (msg: string, type?: 'success' | 'error') => void;
}

export const PracticumSection: React.FC<PracticumSectionProps> = ({
  practicum,
  onChange,
  onSave,
  onConfirmDelete,
  onShowToast,
}) => {
  const handleAdd = () => {
    const newItem: GalleryItem = {
      id: crypto.randomUUID(),
      title: 'การจัดการเรียนรู้',
      date: new Date().toISOString().slice(0, 10),
      caption: '',
      imageUrl: '',
    };
    onChange([...practicum, newItem]);
  };

  const handleUpdate = (id: string, field: keyof GalleryItem, value: string) => {
    onChange(practicum.map((item) => (item.id === id ? { ...item, [field]: value } : item)));
  };

  const handleDelete = (id: string) => {
    onConfirmDelete(() => {
      onChange(practicum.filter((item) => item.id !== id));
    });
  };

  const handleUpload = async (id: string, file: File | null) => {
    if (!file) return;
    try {
      const compressed = await compressImageFile(file);
      handleUpdate(id, 'imageUrl', compressed.compressedDataUrl);
      onShowToast('ย่อขนาดรูปภาพและบันทึกภาพตัวอย่างเรียบร้อย');
    } catch (err: any) {
      onShowToast(err.message === 'IMAGE_TOO_LARGE' ? 'รูปภาพมีขนาดเกิน 200KB' : 'ไม่สามารถประมวลผลรูปภาพได้', 'error');
    }
  };

  return (
    <div className="border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-xl font-bold text-[#0c3574]">รูปฝึกสอนในชั้นเรียน</h3>
          <p className="text-xs text-[#587895] mt-1">รวบรวมภาพการปฏิบัติการสอนและการจัดบรรยากาศชั้นเรียน</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleAdd}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-blue-50 text-[#1267d6] hover:bg-blue-100 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            เพิ่มรูป
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
        {practicum.length === 0 ? (
          <p className="md:col-span-2 p-8 text-center text-sm font-semibold text-slate-400 border border-dashed rounded-xl">
            ยังไม่มีรูปฝึกสอน กด "เพิ่มรูป" เพื่อเริ่มต้น
          </p>
        ) : (
          practicum.map((item, index) => (
            <div key={item.id} className="border border-[#d7e5f5] rounded-2xl p-5 bg-[#f9fcff] space-y-4 shadow-xs">
              <div className="flex items-center justify-between pb-3 border-b border-blue-100/60">
                <span className="text-xs font-bold text-[#174a80] flex items-center gap-1.5">
                  <span className="w-5 h-5 rounded-full bg-blue-100 text-[#1267d6] flex items-center justify-center text-[11px] font-extrabold">
                    {index + 1}
                  </span>
                  {item.title ? item.title : `รูปฝึกสอนที่ ${index + 1}`}
                </span>
                <button
                  type="button"
                  onClick={() => handleDelete(item.id)}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold text-red-500 hover:text-red-700 hover:bg-red-50 transition-colors border border-transparent hover:border-red-100"
                  title="ลบรายการนี้"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>ลบ</span>
                </button>
              </div>

              <div className="min-h-[220px] max-h-[360px] h-64 md:h-72 w-full rounded-xl bg-slate-900/5 border border-dashed border-blue-200 overflow-hidden flex items-center justify-center p-1.5 relative">
                {item.imageUrl ? (
                  <img
                    src={item.imageUrl}
                    alt={item.title || 'รูปบรรยากาศการฝึกสอน'}
                    className="max-h-full max-w-full object-contain rounded-lg shadow-sm"
                  />
                ) : (
                  <div className="text-center text-[#587895] p-6">
                    <ImagePlus className="w-10 h-10 mx-auto mb-2 opacity-50 text-[#1267d6]" />
                    <span className="text-xs font-semibold">ยังไม่มีรูปภาพตัวอย่าง กด "เลือกรูปภาพ" ด้านล่าง</span>
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <label className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-blue-50 text-[#1267d6] hover:bg-blue-100 transition-colors">
                  <ImagePlus className="w-3.5 h-3.5" />
                  เลือกรูปภาพ
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => handleUpload(item.id, e.target.files?.[0] || null)}
                  />
                </label>
                {item.imageUrl && (
                  <button
                    type="button"
                    onClick={() => handleUpdate(item.id, 'imageUrl', '')}
                    className="px-3 py-1.5 rounded-lg text-xs font-bold text-red-600 hover:bg-red-50 transition-colors"
                  >
                    ลบรูปนี้
                  </button>
                )}
              </div>

              <div>
                <label className="block mb-1 text-xs font-bold text-[#315272]">บริบทการฝึกสอน / ชื่อเรื่อง</label>
                <input
                  type="text"
                  value={item.title}
                  onChange={(e) => handleUpdate(item.id, 'title', e.target.value)}
                  className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                />
              </div>

              <div>
                <label className="block mb-1 text-xs font-bold text-[#315272]">วันที่</label>
                <input
                  type="date"
                  value={item.date}
                  onChange={(e) => handleUpdate(item.id, 'date', e.target.value)}
                  className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                />
              </div>

              <div>
                <label className="block mb-1 text-xs font-bold text-[#315272]">คำบรรยายภาพ</label>
                <textarea
                  rows={2}
                  value={item.caption}
                  onChange={(e) => handleUpdate(item.id, 'caption', e.target.value)}
                  className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

