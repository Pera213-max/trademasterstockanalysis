"use client";

import React from 'react';
import Link from 'next/link';
import { BarChart3, Globe, Clock, ArrowLeft, TrendingUp, Building2 } from 'lucide-react';

export default function USDashboard() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-xl border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl blur-lg opacity-50 group-hover:opacity-75 transition-opacity"></div>
                <div className="relative p-2 bg-gradient-to-br from-cyan-600 to-blue-600 rounded-xl">
                  <BarChart3 className="w-6 h-6 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">TradeMaster Pro</h1>
                <p className="text-xs text-slate-400">USA Markets</p>
              </div>
            </Link>

            <Link
              href="/fi/dashboard"
              className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Suomi</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content - Coming Soon */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-20">
        <div className="text-center">
          {/* Icon */}
          <div className="flex justify-center mb-8">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500 to-purple-600 rounded-3xl blur-2xl opacity-30"></div>
              <div className="relative p-6 bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-3xl">
                <Globe className="w-16 h-16 text-blue-400" />
              </div>
            </div>
          </div>

          {/* Title */}
          <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4">
            USA Markets
          </h1>
          <p className="text-xl text-slate-400 mb-8">
            Tulossa pian
          </p>

          {/* Coming Features */}
          <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-8 mb-8">
            <h2 className="text-lg font-semibold text-white mb-6 flex items-center justify-center gap-2">
              <Clock className="w-5 h-5 text-cyan-400" />
              Tulossa
            </h2>

            <div className="grid sm:grid-cols-3 gap-6">
              <div className="flex flex-col items-center gap-3 p-4">
                <div className="p-3 bg-green-500/20 rounded-xl">
                  <TrendingUp className="w-8 h-8 text-green-400" />
                </div>
                <div className="text-center">
                  <p className="font-medium text-white">S&P 500</p>
                  <p className="text-sm text-slate-400">500 suurinta yritystä</p>
                </div>
              </div>

              <div className="flex flex-col items-center gap-3 p-4">
                <div className="p-3 bg-blue-500/20 rounded-xl">
                  <Building2 className="w-8 h-8 text-blue-400" />
                </div>
                <div className="text-center">
                  <p className="font-medium text-white">NYSE</p>
                  <p className="text-sm text-slate-400">New York Stock Exchange</p>
                </div>
              </div>

              <div className="flex flex-col items-center gap-3 p-4">
                <div className="p-3 bg-purple-500/20 rounded-xl">
                  <BarChart3 className="w-8 h-8 text-purple-400" />
                </div>
                <div className="text-center">
                  <p className="font-medium text-white">NASDAQ</p>
                  <p className="text-sm text-slate-400">Teknologia & kasvu</p>
                </div>
              </div>
            </div>
          </div>

          {/* CTA */}
          <Link
            href="/fi/dashboard"
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 rounded-xl font-medium transition-all"
          >
            <ArrowLeft className="w-5 h-5" />
            Siirry Suomen osakkeisiin
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 py-8 mt-20">
        <div className="max-w-4xl mx-auto px-4 text-center text-sm text-slate-500">
          <p>TradeMaster Pro - AI-pohjainen osakeanalyysi</p>
        </div>
      </footer>
    </div>
  );
}
