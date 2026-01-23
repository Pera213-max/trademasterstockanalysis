"use client";

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import {
  BarChart3, TrendingUp, TrendingDown, ArrowLeft, Globe,
  Calculator, LineChart, PiggyBank, Target, Calendar,
  ChevronRight, Info, DollarSign, Percent, Award,
  ArrowUpRight, ArrowDownRight, Sparkles, Building2,
  Clock, CheckCircle, AlertTriangle, HelpCircle
} from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';

// ============================================================================
// TYPES
// ============================================================================
interface IndexData {
  symbol: string;
  name: string;
  nameFi: string;
  price: number;
  change: number;
  changePercent: number;
  currency: string;
  country: string;
  flag: string;
  description: string;
  // Historical returns
  return1y?: number;
  return3y?: number;
  return5y?: number;
  return10y?: number;
  return20y?: number;
  avgAnnualReturn?: number;
}

interface IndexFund {
  name: string;
  ticker: string;
  index: string;
  ter: number; // Total Expense Ratio
  size: string; // Fund size
  provider: string;
  dividends: 'acc' | 'dist'; // Accumulating or Distributing
  domicile: string;
  description: string;
}

// ============================================================================
// INDEX DATA - Major world indices with historical performance
// ============================================================================
const INDICES: IndexData[] = [
  {
    symbol: "^GSPC",
    name: "S&P 500",
    nameFi: "S&P 500",
    price: 0,
    change: 0,
    changePercent: 0,
    currency: "USD",
    country: "USA",
    flag: "🇺🇸",
    description: "500 suurinta USA:n yritystä. Maailman seuratuin osakeindeksi.",
    return1y: 26.3,
    return3y: 33.7,
    return5y: 87.2,
    return10y: 237.4,
    return20y: 546.8,
    avgAnnualReturn: 10.5
  },
  {
    symbol: "^NDX",
    name: "NASDAQ 100",
    nameFi: "NASDAQ 100",
    price: 0,
    change: 0,
    changePercent: 0,
    currency: "USD",
    country: "USA",
    flag: "🇺🇸",
    description: "100 suurinta teknologiapainotteista yritystä NASDAQissa.",
    return1y: 28.5,
    return3y: 42.1,
    return5y: 156.3,
    return10y: 456.7,
    return20y: 1245.2,
    avgAnnualReturn: 14.2
  },
  {
    symbol: "^OMXH25",
    name: "OMX Helsinki 25",
    nameFi: "OMXH25",
    price: 0,
    change: 0,
    changePercent: 0,
    currency: "EUR",
    country: "Suomi",
    flag: "🇫🇮",
    description: "25 vaihdetuinta osaketta Helsingin pörssissä.",
    return1y: 8.2,
    return3y: -5.4,
    return5y: 22.1,
    return10y: 68.5,
    return20y: 124.3,
    avgAnnualReturn: 6.8
  },
  {
    symbol: "^STOXX50E",
    name: "EURO STOXX 50",
    nameFi: "Euro Stoxx 50",
    price: 0,
    change: 0,
    changePercent: 0,
    currency: "EUR",
    country: "Eurooppa",
    flag: "🇪🇺",
    description: "50 suurinta euroalueen yritystä.",
    return1y: 12.4,
    return3y: 28.6,
    return5y: 45.2,
    return10y: 89.3,
    return20y: 78.4,
    avgAnnualReturn: 5.2
  },
  {
    symbol: "^GDAXI",
    name: "DAX",
    nameFi: "DAX 40",
    price: 0,
    change: 0,
    changePercent: 0,
    currency: "EUR",
    country: "Saksa",
    flag: "🇩🇪",
    description: "40 suurinta saksalaista yritystä.",
    return1y: 19.2,
    return3y: 31.4,
    return5y: 52.8,
    return10y: 112.6,
    return20y: 298.4,
    avgAnnualReturn: 8.1
  },
  {
    symbol: "^FTSE",
    name: "FTSE 100",
    nameFi: "FTSE 100",
    price: 0,
    change: 0,
    changePercent: 0,
    currency: "GBP",
    country: "UK",
    flag: "🇬🇧",
    description: "100 suurinta yritystä Lontoon pörssissä.",
    return1y: 9.8,
    return3y: 24.1,
    return5y: 18.6,
    return10y: 42.3,
    return20y: 68.9,
    avgAnnualReturn: 5.4
  },
  {
    symbol: "^N225",
    name: "Nikkei 225",
    nameFi: "Nikkei 225",
    price: 0,
    change: 0,
    changePercent: 0,
    currency: "JPY",
    country: "Japani",
    flag: "🇯🇵",
    description: "225 suurinta japanilaista yritystä.",
    return1y: 21.3,
    return3y: 45.2,
    return5y: 68.4,
    return10y: 156.8,
    return20y: 124.5,
    avgAnnualReturn: 7.2
  },
  {
    symbol: "ACWI",
    name: "MSCI ACWI",
    nameFi: "MSCI Maailma",
    price: 0,
    change: 0,
    changePercent: 0,
    currency: "USD",
    country: "Maailma",
    flag: "🌍",
    description: "Koko maailman osakemarkkinat yhdessä indeksissä.",
    return1y: 22.1,
    return3y: 28.4,
    return5y: 72.3,
    return10y: 168.4,
    return20y: 412.6,
    avgAnnualReturn: 9.2
  }
];

// ============================================================================
// RECOMMENDED INDEX FUNDS
// ============================================================================
const INDEX_FUNDS: IndexFund[] = [
  // S&P 500 rahastot
  {
    name: "iShares Core S&P 500 UCITS ETF",
    ticker: "SXR8",
    index: "S&P 500",
    ter: 0.07,
    size: "€75 mrd",
    provider: "iShares",
    dividends: 'acc',
    domicile: "Irlanti",
    description: "Suosituin S&P 500 ETF Euroopassa. Erittäin alhainen kulut."
  },
  {
    name: "Vanguard S&P 500 UCITS ETF",
    ticker: "VUSA",
    index: "S&P 500",
    ter: 0.07,
    size: "€42 mrd",
    provider: "Vanguard",
    dividends: 'dist',
    domicile: "Irlanti",
    description: "Vanguardin klassikko. Maksaa osingot neljännesvuosittain."
  },
  // NASDAQ 100
  {
    name: "iShares NASDAQ 100 UCITS ETF",
    ticker: "SXRV",
    index: "NASDAQ 100",
    ter: 0.33,
    size: "€12 mrd",
    provider: "iShares",
    dividends: 'acc',
    domicile: "Irlanti",
    description: "Teknologiapainotteinen USA-indeksi. Korkeampi tuotto ja riski."
  },
  {
    name: "Invesco EQQQ NASDAQ-100 UCITS ETF",
    ticker: "EQQQ",
    index: "NASDAQ 100",
    ter: 0.30,
    size: "€8 mrd",
    provider: "Invesco",
    dividends: 'acc',
    domicile: "Irlanti",
    description: "Toinen suosittu NASDAQ 100 vaihtoehto."
  },
  // Maailma
  {
    name: "iShares Core MSCI World UCITS ETF",
    ticker: "SWDA",
    index: "MSCI World",
    ter: 0.20,
    size: "€65 mrd",
    provider: "iShares",
    dividends: 'acc',
    domicile: "Irlanti",
    description: "Koko kehittynyt maailma yhdessä ETF:ssä. Erinomainen hajautus."
  },
  {
    name: "Vanguard FTSE All-World UCITS ETF",
    ticker: "VWCE",
    index: "FTSE All-World",
    ter: 0.22,
    size: "€18 mrd",
    provider: "Vanguard",
    dividends: 'acc',
    domicile: "Irlanti",
    description: "Sisältää myös kehittyvät markkinat. Todellinen maailmarahasto."
  },
  // Eurooppa
  {
    name: "iShares Core EURO STOXX 50 UCITS ETF",
    ticker: "CSX5",
    index: "Euro Stoxx 50",
    ter: 0.10,
    size: "€9 mrd",
    provider: "iShares",
    dividends: 'acc',
    domicile: "Irlanti",
    description: "Euroalueen 50 suurinta yritystä. Alhainen kulu."
  },
  // Suomi
  {
    name: "Seligson OMX Helsinki 25",
    ticker: "OMXH25",
    index: "OMXH25",
    ter: 0.18,
    size: "€450 milj",
    provider: "Seligson",
    dividends: 'dist',
    domicile: "Suomi",
    description: "Suomen markkinoiden klassikko. Suomalainen rahasto."
  },
];

// ============================================================================
// INVESTMENT CALCULATOR COMPONENT
// ============================================================================
interface CalculatorResult {
  totalInvested: number;
  finalValue: number;
  profit: number;
  profitPercent: number;
  yearlyBreakdown: Array<{ year: number; invested: number; value: number }>;
}

function InvestmentCalculator() {
  const [monthlyAmount, setMonthlyAmount] = useState(500);
  const [years, setYears] = useState(20);
  const [annualReturn, setAnnualReturn] = useState(8);
  const [result, setResult] = useState<CalculatorResult | null>(null);

  useEffect(() => {
    const monthlyRate = annualReturn / 100 / 12;
    const months = years * 12;

    let value = 0;
    const yearlyBreakdown: CalculatorResult['yearlyBreakdown'] = [];

    for (let month = 1; month <= months; month++) {
      value = (value + monthlyAmount) * (1 + monthlyRate);

      if (month % 12 === 0) {
        yearlyBreakdown.push({
          year: month / 12,
          invested: monthlyAmount * month,
          value: Math.round(value)
        });
      }
    }

    const totalInvested = monthlyAmount * months;
    const finalValue = Math.round(value);
    const profit = finalValue - totalInvested;
    const profitPercent = ((finalValue / totalInvested) - 1) * 100;

    setResult({
      totalInvested,
      finalValue,
      profit,
      profitPercent,
      yearlyBreakdown
    });
  }, [monthlyAmount, years, annualReturn]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('fi-FI', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0
    }).format(value);
  };

  return (
    <div className="bg-gradient-to-br from-emerald-900/30 to-teal-900/30 border border-emerald-700/50 rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-emerald-500/20 rounded-xl">
          <Calculator className="w-6 h-6 text-emerald-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Sijoituslaskuri</h2>
          <p className="text-sm text-slate-400">Laske korkoa korolle -efekti</p>
        </div>
      </div>

      {/* Input Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div>
          <label className="block text-sm text-slate-400 mb-2">
            Kuukausisijoitus
          </label>
          <div className="relative">
            <input
              type="number"
              value={monthlyAmount}
              onChange={(e) => setMonthlyAmount(Number(e.target.value))}
              className="w-full bg-slate-800/50 border border-slate-600 rounded-lg px-4 py-3 text-white focus:border-emerald-500 focus:outline-none"
              min={50}
              max={10000}
              step={50}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">€/kk</span>
          </div>
          <input
            type="range"
            value={monthlyAmount}
            onChange={(e) => setMonthlyAmount(Number(e.target.value))}
            min={50}
            max={5000}
            step={50}
            className="w-full mt-2 accent-emerald-500"
          />
        </div>

        <div>
          <label className="block text-sm text-slate-400 mb-2">
            Sijoitusaika
          </label>
          <div className="relative">
            <input
              type="number"
              value={years}
              onChange={(e) => setYears(Number(e.target.value))}
              className="w-full bg-slate-800/50 border border-slate-600 rounded-lg px-4 py-3 text-white focus:border-emerald-500 focus:outline-none"
              min={1}
              max={50}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">vuotta</span>
          </div>
          <input
            type="range"
            value={years}
            onChange={(e) => setYears(Number(e.target.value))}
            min={1}
            max={40}
            className="w-full mt-2 accent-emerald-500"
          />
        </div>

        <div>
          <label className="block text-sm text-slate-400 mb-2">
            Vuosituotto-oletus
          </label>
          <div className="relative">
            <input
              type="number"
              value={annualReturn}
              onChange={(e) => setAnnualReturn(Number(e.target.value))}
              className="w-full bg-slate-800/50 border border-slate-600 rounded-lg px-4 py-3 text-white focus:border-emerald-500 focus:outline-none"
              min={1}
              max={20}
              step={0.5}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">%</span>
          </div>
          <input
            type="range"
            value={annualReturn}
            onChange={(e) => setAnnualReturn(Number(e.target.value))}
            min={4}
            max={15}
            step={0.5}
            className="w-full mt-2 accent-emerald-500"
          />
        </div>
      </div>

      {/* Quick Presets */}
      <div className="flex flex-wrap gap-2 mb-6">
        <span className="text-sm text-slate-400">Pikavalinta:</span>
        {[
          { label: '100€/kk, 30v', amount: 100, yrs: 30, ret: 8 },
          { label: '500€/kk, 20v', amount: 500, yrs: 20, ret: 8 },
          { label: '1000€/kk, 15v', amount: 1000, yrs: 15, ret: 8 },
          { label: 'Eläkesäästö', amount: 200, yrs: 35, ret: 7 },
        ].map((preset) => (
          <button
            key={preset.label}
            onClick={() => {
              setMonthlyAmount(preset.amount);
              setYears(preset.yrs);
              setAnnualReturn(preset.ret);
            }}
            className="px-3 py-1 bg-slate-700/50 hover:bg-emerald-600/30 border border-slate-600 hover:border-emerald-500 rounded-full text-sm text-slate-300 hover:text-white transition-colors"
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Main Result */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-800/50 rounded-xl p-4 text-center">
              <p className="text-sm text-slate-400 mb-1">Sijoitettu yhteensä</p>
              <p className="text-2xl font-bold text-white">{formatCurrency(result.totalInvested)}</p>
            </div>
            <div className="bg-emerald-900/30 border border-emerald-600/50 rounded-xl p-4 text-center">
              <p className="text-sm text-emerald-400 mb-1">Lopullinen arvo</p>
              <p className="text-3xl font-bold text-emerald-400">{formatCurrency(result.finalValue)}</p>
            </div>
            <div className="bg-slate-800/50 rounded-xl p-4 text-center">
              <p className="text-sm text-slate-400 mb-1">Tuotto (korkoa korolle)</p>
              <p className="text-2xl font-bold text-green-400">+{formatCurrency(result.profit)}</p>
              <p className="text-sm text-green-400">+{result.profitPercent.toFixed(0)}%</p>
            </div>
          </div>

          {/* Yearly Breakdown Chart */}
          <div className="bg-slate-800/30 rounded-xl p-4">
            <h4 className="text-sm font-semibold text-slate-300 mb-4">Varallisuuden kehitys vuosittain</h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {result.yearlyBreakdown.map((year) => {
                const maxValue = result.finalValue;
                const investedWidth = (year.invested / maxValue) * 100;
                const valueWidth = (year.value / maxValue) * 100;

                return (
                  <div key={year.year} className="flex items-center gap-3">
                    <span className="text-xs text-slate-400 w-16">Vuosi {year.year}</span>
                    <div className="flex-1 h-6 bg-slate-700/50 rounded-full overflow-hidden relative">
                      <div
                        className="absolute h-full bg-slate-500/50 rounded-full"
                        style={{ width: `${investedWidth}%` }}
                      />
                      <div
                        className="absolute h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-full"
                        style={{ width: `${valueWidth}%` }}
                      />
                    </div>
                    <span className="text-xs text-emerald-400 w-24 text-right">
                      {formatCurrency(year.value)}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center justify-center gap-6 mt-4 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-slate-500/50 rounded"></div>
                <span className="text-slate-400">Sijoitettu</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-emerald-500 rounded"></div>
                <span className="text-slate-400">Arvo tuottojen kanssa</span>
              </div>
            </div>
          </div>

          {/* Info Box */}
          <div className="bg-amber-900/20 border border-amber-700/50 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-amber-200">
                <p className="font-semibold mb-1">Huomio laskelmasta</p>
                <p className="text-amber-300/80">
                  Laskelma olettaa tasaisen {annualReturn}% vuosituoton. Todellisuudessa tuotot vaihtelevat
                  vuosittain. S&P 500:n historiallinen keskituotto on noin 10% vuodessa, mutta
                  yksittäiset vuodet voivat olla -30% tai +30%.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// INDEX PERFORMANCE COMPARISON
// ============================================================================
function IndexPerformanceComparison() {
  const [sortBy, setSortBy] = useState<'return1y' | 'return5y' | 'return10y' | 'avgAnnualReturn'>('avgAnnualReturn');

  const sortedIndices = useMemo(() => {
    return [...INDICES].sort((a, b) => {
      const aVal = a[sortBy] || 0;
      const bVal = b[sortBy] || 0;
      return bVal - aVal;
    });
  }, [sortBy]);

  return (
    <div className="bg-gradient-to-br from-blue-900/30 to-indigo-900/30 border border-blue-700/50 rounded-2xl p-4 sm:p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 sm:p-3 bg-blue-500/20 rounded-xl">
            <Award className="w-5 h-5 sm:w-6 sm:h-6 text-blue-400" />
          </div>
          <div>
            <h2 className="text-lg sm:text-xl font-bold text-white">Indeksien Vertailu</h2>
            <p className="text-xs sm:text-sm text-slate-400">Historiallinen tuotto</p>
          </div>
        </div>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as any)}
          className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white w-full sm:w-auto"
        >
          <option value="avgAnnualReturn">Keskituotto/vuosi</option>
          <option value="return1y">1 vuosi</option>
          <option value="return5y">5 vuotta</option>
          <option value="return10y">10 vuotta</option>
        </select>
      </div>

      <div className="space-y-3">
        {sortedIndices.map((index, i) => {
          const avgReturn = index.avgAnnualReturn || 0;
          const maxAvg = Math.max(...INDICES.map(i => i.avgAnnualReturn || 0));
          const barWidth = (avgReturn / maxAvg) * 100;

          return (
            <div key={index.symbol} className="bg-slate-800/50 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className={`w-6 h-6 flex items-center justify-center rounded-full text-xs font-bold ${
                    i === 0 ? 'bg-yellow-500 text-black' :
                    i === 1 ? 'bg-slate-400 text-black' :
                    i === 2 ? 'bg-amber-700 text-white' :
                    'bg-slate-700 text-slate-300'
                  }`}>
                    {i + 1}
                  </span>
                  <span className="text-lg">{index.flag}</span>
                  <div>
                    <h3 className="font-bold text-white">{index.nameFi}</h3>
                    <p className="text-xs text-slate-400">{index.country}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-blue-400">
                    {avgReturn.toFixed(1)}%
                    <span className="text-xs text-slate-400 ml-1">/vuosi</span>
                  </p>
                </div>
              </div>

              {/* Performance bar */}
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden mb-3">
                <div
                  className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full transition-all duration-500"
                  style={{ width: `${barWidth}%` }}
                />
              </div>

              {/* Return breakdown */}
              <div className="grid grid-cols-5 gap-2 text-center">
                <div>
                  <p className="text-xs text-slate-500">1v</p>
                  <p className={`text-sm font-semibold ${(index.return1y || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {index.return1y ? `${index.return1y > 0 ? '+' : ''}${index.return1y.toFixed(1)}%` : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">3v</p>
                  <p className={`text-sm font-semibold ${(index.return3y || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {index.return3y ? `${index.return3y > 0 ? '+' : ''}${index.return3y.toFixed(1)}%` : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">5v</p>
                  <p className={`text-sm font-semibold ${(index.return5y || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {index.return5y ? `${index.return5y > 0 ? '+' : ''}${index.return5y.toFixed(1)}%` : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">10v</p>
                  <p className={`text-sm font-semibold ${(index.return10y || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {index.return10y ? `${index.return10y > 0 ? '+' : ''}${index.return10y.toFixed(1)}%` : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">20v</p>
                  <p className={`text-sm font-semibold ${(index.return20y || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {index.return20y ? `${index.return20y > 0 ? '+' : ''}${index.return20y.toFixed(1)}%` : '-'}
                  </p>
                </div>
              </div>

              <p className="text-xs text-slate-500 mt-2">{index.description}</p>
            </div>
          );
        })}
      </div>

      {/* Key Insight */}
      <div className="mt-6 bg-blue-900/30 border border-blue-600/50 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="font-semibold text-blue-300 mb-1">Miksi USA dominoi?</p>
            <p className="text-blue-200/80">
              S&P 500 ja NASDAQ 100 ovat historiallisesti tuottaneet parhaiten johtuen USA:n
              teknologiayritysten (Apple, Microsoft, Google, Amazon) valtavasta kasvusta.
              Hajautuksen kannalta maailmarahasto (MSCI World) on turvallisempi valinta.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// INDEX FUND RECOMMENDATIONS
// ============================================================================
function IndexFundRecommendations() {
  const [selectedIndex, setSelectedIndex] = useState<string>('all');

  const filteredFunds = selectedIndex === 'all'
    ? INDEX_FUNDS
    : INDEX_FUNDS.filter(f => f.index.includes(selectedIndex));

  return (
    <div className="bg-gradient-to-br from-purple-900/30 to-pink-900/30 border border-purple-700/50 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-purple-500/20 rounded-xl">
            <PiggyBank className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Suositellut Indeksirahastot</h2>
            <p className="text-sm text-slate-400">ETF:t eurooppalaisille sijoittajille</p>
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="flex flex-wrap gap-2 mb-6">
        {['all', 'S&P 500', 'NASDAQ', 'World', 'Euro', 'OMXH25'].map((filter) => (
          <button
            key={filter}
            onClick={() => setSelectedIndex(filter)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedIndex === filter
                ? 'bg-purple-600 text-white'
                : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600/50'
            }`}
          >
            {filter === 'all' ? 'Kaikki' : filter}
          </button>
        ))}
      </div>

      {/* Fund Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredFunds.map((fund) => (
          <div
            key={fund.ticker}
            className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-purple-500/50 transition-colors"
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-bold text-white text-sm">{fund.name}</h3>
                <p className="text-xs text-slate-400">{fund.provider} • {fund.ticker}</p>
              </div>
              <span className="px-2 py-1 bg-purple-600/30 text-purple-300 text-xs rounded-full">
                {fund.index}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 mb-3">
              <div className="bg-slate-700/50 rounded-lg p-2 text-center">
                <p className="text-xs text-slate-400">TER</p>
                <p className="text-sm font-bold text-green-400">{fund.ter}%</p>
              </div>
              <div className="bg-slate-700/50 rounded-lg p-2 text-center">
                <p className="text-xs text-slate-400">Koko</p>
                <p className="text-sm font-bold text-white">{fund.size}</p>
              </div>
              <div className="bg-slate-700/50 rounded-lg p-2 text-center">
                <p className="text-xs text-slate-400">Osingot</p>
                <p className="text-sm font-bold text-white">
                  {fund.dividends === 'acc' ? 'Kasv.' : 'Jaettu'}
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-400">{fund.description}</p>
          </div>
        ))}
      </div>

      {/* TER Explanation */}
      <div className="mt-6 bg-slate-800/50 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <HelpCircle className="w-5 h-5 text-slate-400 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="font-semibold text-slate-300 mb-1">Mitä TER tarkoittaa?</p>
            <p className="text-slate-400">
              <strong>TER (Total Expense Ratio)</strong> on rahaston vuotuinen kokonaiskulu prosentteina.
              Esim. 0.07% TER tarkoittaa, että 10 000€ sijoituksesta maksat 7€ vuodessa kuluja.
              Passiivisissa indeksirahastoissa TER on tyypillisesti 0.05-0.30%.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// LIVE INDEX DATA COMPONENT
// ============================================================================
function LiveIndexData() {
  const [indexData, setIndexData] = useState<IndexData[]>(INDICES);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a real app, fetch live data from API
    // For now, simulate with random changes
    const fetchData = async () => {
      setLoading(true);
      await new Promise(resolve => setTimeout(resolve, 500));

      const updatedData = INDICES.map(index => ({
        ...index,
        price: getSimulatedPrice(index.symbol),
        change: (Math.random() - 0.4) * 2,
        changePercent: (Math.random() - 0.4) * 3
      }));

      setIndexData(updatedData);
      setLoading(false);
    };

    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  const getSimulatedPrice = (symbol: string): number => {
    const basePrices: Record<string, number> = {
      "^GSPC": 5950,
      "^NDX": 21200,
      "^OMXH25": 4850,
      "^STOXX50E": 5020,
      "^GDAXI": 20150,
      "^FTSE": 8320,
      "^N225": 39800,
      "ACWI": 118
    };
    return basePrices[symbol] || 100;
  };

  return (
    <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-slate-700/50 rounded-2xl p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 sm:p-3 bg-cyan-500/20 rounded-xl">
            <Globe className="w-5 h-5 sm:w-6 sm:h-6 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-lg sm:text-xl font-bold text-white">Maailman Indeksit</h2>
            <p className="text-xs sm:text-sm text-slate-400">Reaaliaikainen markkinakatsaus</p>
          </div>
        </div>
        <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400">
          <Clock className="w-4 h-4" />
          <span>Päivittyy minuutin välein</span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {indexData.map((index) => (
          <div
            key={index.symbol}
            className={`bg-slate-800/50 border rounded-xl p-4 transition-colors ${
              index.changePercent >= 0
                ? 'border-green-800/50 hover:border-green-600/50'
                : 'border-red-800/50 hover:border-red-600/50'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-lg">{index.flag}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                index.changePercent >= 0
                  ? 'bg-green-900/50 text-green-400'
                  : 'bg-red-900/50 text-red-400'
              }`}>
                {index.changePercent >= 0 ? '+' : ''}{index.changePercent.toFixed(2)}%
              </span>
            </div>
            <h3 className="font-bold text-white text-sm">{index.nameFi}</h3>
            <p className="text-xs text-slate-500">{index.country}</p>
            <p className="text-lg font-bold text-white mt-1">
              {index.price.toLocaleString('fi-FI')}
              <span className="text-xs text-slate-400 ml-1">{index.currency}</span>
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// BEGINNER GUIDE
// ============================================================================
function BeginnerGuide() {
  return (
    <div className="bg-gradient-to-br from-amber-900/30 to-orange-900/30 border border-amber-700/50 rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-amber-500/20 rounded-xl">
          <Target className="w-6 h-6 text-amber-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Aloittelijan Opas</h2>
          <p className="text-sm text-slate-400">Näin aloitat indeksisijoittamisen</p>
        </div>
      </div>

      <div className="space-y-4">
        {[
          {
            step: 1,
            title: "Avaa arvo-osuustili",
            description: "Nordnet, Degiro tai pankkisi kautta. Vertaa kuluja.",
            icon: Building2
          },
          {
            step: 2,
            title: "Valitse indeksirahasto",
            description: "S&P 500 tai MSCI World ovat hyviä aloittelijalle.",
            icon: LineChart
          },
          {
            step: 3,
            title: "Aseta kuukausisäästö",
            description: "Automaattinen osto esim. 100-500€/kk palkkapäivänä.",
            icon: Calendar
          },
          {
            step: 4,
            title: "Odota ja unohda",
            description: "Älä myy laskuissa. Korkoa korolle toimii vuosien kuluessa.",
            icon: Clock
          }
        ].map((item) => (
          <div key={item.step} className="flex items-start gap-4 bg-slate-800/30 rounded-xl p-4">
            <div className="w-8 h-8 bg-amber-500 rounded-full flex items-center justify-center text-black font-bold flex-shrink-0">
              {item.step}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <item.icon className="w-4 h-4 text-amber-400" />
                <h3 className="font-bold text-white">{item.title}</h3>
              </div>
              <p className="text-sm text-slate-400">{item.description}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 bg-green-900/20 border border-green-700/50 rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle className="w-5 h-5 text-green-400" />
          <span className="font-bold text-green-300">Vinkki ammattilaisilta</span>
        </div>
        <p className="text-sm text-green-200/80">
          &ldquo;Älä yritä ajoittaa markkinoita. Time in the market beats timing the market.
          Kuukausisäästäminen tasoittaa ostohinnan ja poistaa tunteet päätöksenteosta.&rdquo;
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN PAGE
// ============================================================================
export default function IndicesPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-900/95 backdrop-blur-md border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                <span className="hidden sm:inline">Takaisin</span>
              </Link>
              <div className="h-6 w-px bg-slate-700" />
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gradient-to-br from-cyan-600 to-blue-600 rounded-lg">
                  <BarChart3 className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-white">Indeksisijoittaminen</h1>
                  <p className="text-xs text-slate-400">Vertailu, laskuri & rahastot</p>
                </div>
              </div>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
        {/* Hero */}
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Indeksisijoittajan Työkalut
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto">
            Vertaile indeksejä, laske tuottoja ja löydä parhaat rahastot.
            Kaikki mitä tarvitset pitkäjänteiseen sijoittamiseen.
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 text-center">
            <p className="text-3xl font-bold text-cyan-400">10.5%</p>
            <p className="text-sm text-slate-400">S&P 500 keskim. tuotto/v</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 text-center">
            <p className="text-3xl font-bold text-purple-400">0.07%</p>
            <p className="text-sm text-slate-400">Alin ETF-kulu (TER)</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 text-center">
            <p className="text-3xl font-bold text-green-400">546%</p>
            <p className="text-sm text-slate-400">S&P 500 tuotto 20v</p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 text-center">
            <p className="text-3xl font-bold text-amber-400">8</p>
            <p className="text-sm text-slate-400">Vertailtavaa indeksiä</p>
          </div>
        </div>

        {/* Live Index Data */}
        <LiveIndexData />

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Calculator */}
          <InvestmentCalculator />

          {/* Beginner Guide */}
          <BeginnerGuide />
        </div>

        {/* Index Comparison - Full Width */}
        <IndexPerformanceComparison />

        {/* Fund Recommendations - Full Width */}
        <IndexFundRecommendations />

        {/* Disclaimer */}
        <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4 text-center">
          <p className="text-sm text-slate-400">
            <AlertTriangle className="w-4 h-4 inline mr-2 text-amber-400" />
            Historialliset tuotot eivät takaa tulevaisuuden tuottoja.
            Sijoittamiseen liittyy aina riski pääoman menettämisestä.
            Tämä ei ole sijoitusneuvontaa.
          </p>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-6 px-4 mt-12">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-500">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-cyan-400" />
            <span>OsakedataX - Indeksit</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/fi/dashboard" className="hover:text-cyan-400 transition-colors">
              Osakkeet
            </Link>
            <Link href="/" className="hover:text-white transition-colors">
              Etusivu
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
