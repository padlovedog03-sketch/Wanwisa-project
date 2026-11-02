import React from 'react';

interface FooterProps {
  authorName: string;
}

export const Footer: React.FC<FooterProps> = ({ authorName }) => {
  return (
    <footer className="mt-10 py-6 text-center text-sm bg-[#0c3574] text-blue-100">
      รายงานการฝึกสอนประสบการณ์วิชาชีพครู • จัดทำโดย {authorName} • บันทึกและปรับปรุงข้อมูลได้จากระบบนี้
    </footer>
  );
};

