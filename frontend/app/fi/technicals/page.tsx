"use client";

import { Suspense } from "react";
import TechnicalAnalysisFi from "@/components/TechnicalAnalysisFi";

function TechnicalsContent() {
  return <TechnicalAnalysisFi />;
}

export default function TechnicalsPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Suspense fallback={
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-400"></div>
        </div>
      }>
        <TechnicalsContent />
      </Suspense>
    </main>
  );
}
