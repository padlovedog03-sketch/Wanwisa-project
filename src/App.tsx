import { useState, useMemo } from 'react';
import { SectionKey } from './types/portfolio';
import { usePortfolioState } from './hooks/usePortfolioState';
import { calculateFieldsProgress } from './utils/validation';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { ProgressBar } from './components/layout/ProgressBar';
import { Toast } from './components/common/Toast';
import { ConfirmModal } from './components/common/ConfirmModal';

import { ProfileSection } from './components/sections/ProfileSection';
import { SchoolSection } from './components/sections/SchoolSection';
import { ScheduleSection } from './components/sections/ScheduleSection';
import { DailyLogSection } from './components/sections/DailyLogSection';
import { PlansSection } from './components/sections/PlansSection';
import { SupervisionSection } from './components/sections/SupervisionSection';
import { ResearchSection } from './components/sections/ResearchSection';
import { AssessmentSection } from './components/sections/AssessmentSection';
import { ActivitiesSection } from './components/sections/ActivitiesSection';
import { PracticumSection } from './components/sections/PracticumSection';
import { SettingsSection } from './components/sections/SettingsSection';

export function App() {
  const [activeSection, setActiveSection] = useState<SectionKey>('home');
  const [toastState, setToastState] = useState<{ message: string; type: 'success' | 'error'; visible: boolean }>({
    message: '',
    type: 'success',
    visible: false,
  });
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
  }>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {},
  });

  const { state, updateState, isDirty, lastSaved, saveAll, resetToSaved } = usePortfolioState();

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToastState({ message, type, visible: true });
    setTimeout(() => {
      setToastState((prev) => ({ ...prev, visible: false }));
    }, 3200);
  };

  const openConfirm = (title: string, message: string, task: () => void) => {
    setConfirmModal({
      isOpen: true,
      title,
      message,
      onConfirm: () => {
        task();
        setConfirmModal((prev) => ({ ...prev, isOpen: false }));
        showToast('ดำเนินการเรียบร้อยแล้ว');
      },
    });
  };

  const handleSave = () => {
    const success = saveAll();
    if (success) {
      showToast('บันทึกข้อมูลสำเร็จเรียบร้อย');
    } else {
      showToast('บันทึกข้อมูลไม่สำเร็จ', 'error');
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleClearSection = (sectionKey: 'schedule' | 'daily' | 'plans' | 'activities') => {
    openConfirm(
      'ยืนยันการล้างข้อมูล',
      `คุณต้องการล้างข้อมูลส่วน "${sectionKey}" ทั้งหมดใช่หรือไม่? การกระทำนี้ไม่สามารถย้อนกลับได้`,
      () => {
        updateState(sectionKey, []);
      }
    );
  };

  const progressPercentage = useMemo(() => {
    const profileProgress = calculateFieldsProgress(state.profile as any);
    const schoolProgress = calculateFieldsProgress(state.school as any);
    return Math.round((profileProgress + schoolProgress) / 2);
  }, [state.profile, state.school]);

  const stats = useMemo(() => {
    return {
      dailyCount: state.daily.length,
      plansCount: state.plans.length,
      activitiesCount: state.activities.length,
      hoursCount: state.profile.teachingHours || 0,
    };
  }, [state.daily, state.plans, state.activities, state.profile.teachingHours]);

  return (
    <div className="min-h-screen flex flex-col bg-[#edf5ff]">
      <Header
        activeSection={activeSection}
        onSelectSection={setActiveSection}
        siteName={state.settings.siteName}
      />

      <main className="flex-1 w-full max-w-7xl mx-auto px-4 py-6 md:py-8">
        <ProgressBar
          percentage={progressPercentage}
          isDirty={isDirty}
          lastSaved={lastSaved}
          onSaveNow={handleSave}
          onReset={resetToSaved}
        />

        <div className="mt-4">
          {activeSection === 'home' && (
            <ProfileSection
              profile={state.profile}
              onChange={(updated) => updateState('profile', updated)}
              onSave={handleSave}
              onReset={resetToSaved}
              stats={stats}
            />
          )}

          {activeSection === 'school' && (
            <SchoolSection
              school={state.school}
              onChange={(updated) => updateState('school', updated)}
              onSave={handleSave}
              onReset={resetToSaved}
            />
          )}

          {activeSection === 'schedule' && (
            <ScheduleSection
              schedule={state.schedule}
              onChange={(updated) => updateState('schedule', updated)}
              onSave={handleSave}
              onConfirmDelete={(task) =>
                openConfirm('ยืนยันการลบรายการ', 'ต้องการลบแถวตารางสอนนี้ใช่หรือไม่?', task)
              }
            />
          )}

          {activeSection === 'daily' && (
            <DailyLogSection
              daily={state.daily}
              onChange={(updated) => updateState('daily', updated)}
              onSaveAll={handleSave}
              onConfirmClear={(task) =>
                openConfirm('ยืนยันการล้างข้อมูลวันนี้', 'ต้องการล้างบันทึกประจำวันนี้ใช่หรือไม่?', task)
              }
            />
          )}

          {activeSection === 'plans' && (
            <PlansSection
              plans={state.plans}
              onChange={(updated) => updateState('plans', updated)}
              onSave={handleSave}
              onConfirmDelete={(task) =>
                openConfirm('ยืนยันการลบแผนการสอน', 'ต้องการลบแผนการจัดการเรียนรู้นี้ใช่หรือไม่?', task)
              }
            />
          )}

          {activeSection === 'supervision' && (
            <SupervisionSection
              supervision={state.supervision}
              onChange={(updated) => updateState('supervision', updated)}
              onSave={handleSave}
              onConfirmDelete={(task) =>
                openConfirm('ยืนยันการลบบันทึกนิเทศ', 'ต้องการลบบันทึกการนิเทศนี้ใช่หรือไม่?', task)
              }
              onShowToast={showToast}
            />
          )}

          {activeSection === 'research' && (
            <ResearchSection
              research={state.research}
              onChange={(updated) => updateState('research', updated)}
              onSave={handleSave}
            />
          )}

          {activeSection === 'assessment' && (
            <AssessmentSection
              assessment={state.assessment}
              onChange={(updated) => updateState('assessment', updated)}
              onSave={handleSave}
              onConfirmDelete={(task) =>
                openConfirm('ยืนยันการลบรายการ', 'ต้องการลบรายการแบบประเมินนี้ใช่หรือไม่?', task)
              }
              onShowToast={showToast}
            />
          )}

          {activeSection === 'activities' && (
            <ActivitiesSection
              activities={state.activities}
              onChange={(updated) => updateState('activities', updated)}
              onSave={handleSave}
              onConfirmDelete={(task) =>
                openConfirm('ยืนยันการลบรูปกิจกรรม', 'ต้องการลบรายการรูปกิจกรรมนี้ใช่หรือไม่?', task)
              }
              onShowToast={showToast}
            />
          )}

          {activeSection === 'practicum' && (
            <PracticumSection
              practicum={state.practicum}
              onChange={(updated) => updateState('practicum', updated)}
              onSave={handleSave}
              onConfirmDelete={(task) =>
                openConfirm('ยืนยันการลบรูปฝึกสอน', 'ต้องการลบรายการรูปฝึกสอนนี้ใช่หรือไม่?', task)
              }
              onShowToast={showToast}
            />
          )}

          {activeSection === 'settings' && (
            <SettingsSection
              settings={state.settings}
              onChange={(updated) => updateState('settings', updated)}
              onSave={handleSave}
              onPrint={handlePrint}
              onClearSection={handleClearSection}
            />
          )}
        </div>
      </main>

      <Footer authorName={state.settings.authorName} />

      <Toast
        message={toastState.message}
        type={toastState.type}
        visible={toastState.visible}
      />

      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal((prev) => ({ ...prev, isOpen: false }))}
      />
    </div>
  );
}

export default App;

