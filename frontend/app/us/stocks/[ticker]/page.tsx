"use client";

import React from 'react';
import Link from 'next/link';
import { Globe, Clock, ArrowLeft } from 'lucide-react';

export default function USStockPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-blue-600/20 border border-blue-500/30 rounded-2xl">
            <Globe className="w-12 h-12 text-blue-400" />
          </div>
        </div>

        <h1 className="text-2xl font-bold text-white mb-2">USA Markets</h1>
        <p className="text-slate-400 mb-6 flex items-center justify-center gap-2">
          <Clock className="w-4 h-4" />
          Tulossa pian
        </p>

        <Link
          href="/fi/dashboard"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 rounded-lg font-medium transition-all text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          Suomen osakkeet
        </Link>
      </div>
    </div>
  );
}
