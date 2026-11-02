import React from 'react';
import { SupervisionItem } from '../../types/portfolio';
import { Plus, Trash2, Save, ImagePlus } from 'lucide-react';
import { compressImageFile } from '../../utils/compression';

interface SupervisionSectionProps {
  supervision: SupervisionItem[];
  onChange: (updated: SupervisionItem[]) => void;
  onSave: () => void;
  onConfirmDelete: (task: () => void) => void;
  onShowToast: (msg: string, type?: 'success' | 'error') => void;
}

export const SupervisionSection: React.FC<SupervisionSectionProps> = ({
  supervision,
  onChange,
  onSave,
  onConfirmDelete,
  onShowToast,
}) => {
  const handleAdd = () => {
    const newItem: SupervisionItem = {
      id: crypto.randomUUID(),
      date: new Date().toISOString().slice(0, 10),
      evaluator: '',
      subject: '',
      classroom: '',
      strength: '',
      feedback: '',
      improvement: '',
      score: 'ดีมาก',
      images: [],
    };
    onChange([...supervision, newItem]);
  };

  const handleUpdate = (id: string, field: keyof SupervisionItem, value: any) => {
    onChange(supervision.map((s) => (s.id === id ? { ...s, [field]: value } : s)));
  };

  const handleDelete = (id: string) => {
    onConfirmDelete(() => {
      onChange(supervision.filter((s) => s.id !== id));
    });
  };

  const handleImageUpload = async (id: string, files: FileList | null) => {
    if (!files || files.length === 0) return;
    const targetItem = supervision.find((s) => s.id === id);
    if (!targetItem) return;

    try {
      const newImages = [...targetItem.images];
      for (const file of Array.from(files)) {
        const compressed = await compressImageFile(file);
        newImages.push(compressed);
      }
      handleUpdate(id, 'images', newImages);
      onShowToast(`ย่อและเพิ่มรูปภาพ ${files.length} รูปเรียบร้อย (ขนาดไม่เกิน 200KB)`);
    } catch (err: any) {
      onShowToast(err.message === 'IMAGE_TOO_LARGE' ? 'รูปภาพมีขนาดเกิน 200KB แม้บีบอัดแล้ว' : 'ไม่สามารถบีบอัดรูปภาพได้', 'error');
    }
  };

  const handleRemoveImage = (itemId: string, imageId: string) => {
    const targetItem = supervision.find((s) => s.id === itemId);
    if (!targetItem) return;
    handleUpdate(
      itemId,
      'images',
      targetItem.images.filter((img) => img.id !== imageId)
    );
  };

  return (
    <div className="border border-[#d7e5f5] rounded-2xl bg-white p-6 shadow-sm space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-xl font-bold text-[#0c3574]">นิเทศการสอน</h3>
          <p className="text-xs text-[#587895] mt-1">บันทึกผลการนิเทศการสอนและข้อเสนอแนะจากครูพี่เลี้ยง/อาจารย์นิเทศก์</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleAdd}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-blue-50 text-[#1267d6] hover:bg-blue-100 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            เพิ่มบันทึก
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
        {supervision.length === 0 ? (
          <p className="p-8 text-center text-sm font-semibold text-slate-400 border border-dashed rounded-xl">
            ยังไม่มีบันทึกการนิเทศ กด "เพิ่มบันทึก" เพื่อเริ่มต้น
          </p>
        ) : (
          supervision.map((item) => (
            <div key={item.id} className="relative border border-[#d7e5f5] rounded-xl p-5 bg-[#f9fcff] space-y-4">
              <button
                type="button"
                onClick={() => handleDelete(item.id)}
                className="absolute top-3 right-3 p-1.5 rounded-lg text-red-500 hover:bg-red-50 transition-colors"
                title="ลบบันทึกนี้"
              >
                <Trash2 className="w-4 h-4" />
              </button>

              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 pr-8">
                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">วันที่นิเทศ</label>
                  <input
                    type="date"
                    value={item.date}
                    onChange={(e) => handleUpdate(item.id, 'date', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">ผู้นิเทศ</label>
                  <input
                    type="text"
                    value={item.evaluator}
                    onChange={(e) => handleUpdate(item.id, 'evaluator', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">วิชา</label>
                  <input
                    type="text"
                    value={item.subject}
                    onChange={(e) => handleUpdate(item.id, 'subject', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div>
                  <label className="block mb-1 text-xs font-bold text-[#315272]">ชั้น / ห้อง</label>
                  <input
                    type="text"
                    value={item.classroom}
                    onChange={(e) => handleUpdate(item.id, 'classroom', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block mb-1 text-xs font-bold text-[#315272]">จุดเด่น</label>
                  <textarea
                    rows={2}
                    value={item.strength}
                    onChange={(e) => handleUpdate(item.id, 'strength', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block mb-1 text-xs font-bold text-[#315272]">ข้อเสนอแนะ</label>
                  <textarea
                    rows={2}
                    value={item.feedback}
                    onChange={(e) => handleUpdate(item.id, 'feedback', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block mb-1 text-xs font-bold text-[#315272]">แผนการปรับปรุงพัฒนา</label>
                  <textarea
                    rows={2}
                    value={item.improvement}
                    onChange={(e) => handleUpdate(item.id, 'improvement', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block mb-1 text-xs font-bold text-[#315272]">ระดับผลการประเมิน</label>
                  <input
                    type="text"
                    value={item.score}
                    onChange={(e) => handleUpdate(item.id, 'score', e.target.value)}
                    className="w-full border border-[#cbdcf2] rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-[#1267d6]"
                  />
                </div>
              </div>

              <div className="border-t border-slate-200 pt-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold text-[#315272]">รูปภาพประกอบการนิเทศ</span>
                  <label className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-blue-50 text-[#1267d6] hover:bg-blue-100 transition-colors">
                    <ImagePlus className="w-3.5 h-3.5" />
                    เพิ่มรูปภาพ
                    <input
                      type="file"
                      multiple
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => handleImageUpload(item.id, e.target.files)}
                    />
                  </label>
                </div>

                {item.images.length > 0 && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {item.images.map((img) => (
                      <div key={img.id} className="relative group border border-slate-200 rounded-xl overflow-hidden bg-white">
                        <img
                          src={img.compressedDataUrl}
                          alt={img.fileName}
                          className="w-full h-32 object-cover"
                        />
                        <button
                          type="button"
                          onClick={() => handleRemoveImage(item.id, img.id)}
                          className="absolute top-1.5 right-1.5 p-1 rounded-md bg-red-600 text-white text-xs opacity-80 hover:opacity-100 transition-opacity"
                        >
                          ลบ
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

