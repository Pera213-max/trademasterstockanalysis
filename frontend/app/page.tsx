"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  BarChart3,
  ChevronRight,
  Globe,
  Flag,
  TrendingUp,
  Building2,
  Sparkles,
  Newspaper,
  Shield,
  LineChart,
  Activity,
  Calculator,
  PiggyBank,
  Mail,
} from "lucide-react";

type MarketStatus = {
  isOpen: boolean;
  timeLabel: string;
};

const getMarketStatus = (
  timeZone: string,
  openHour: number,
  openMinute: number,
  closeHour: number,
  closeMinute: number
): MarketStatus => {
  const local = new Date(
    new Date().toLocaleString("en-US", { timeZone })
  );
  const day = local.getDay();
  const minutes = local.getHours() * 60 + local.getMinutes();
  const openMinutes = openHour * 60 + openMinute;
  const closeMinutes = closeHour * 60 + closeMinute;
  const isWeekend = day === 0 || day === 6;
  const isOpen = !isWeekend && minutes >= openMinutes && minutes < closeMinutes;
  const timeLabel = local.toLocaleTimeString("fi-FI", {
    hour: "2-digit",
    minute: "2-digit",
  });
  return { isOpen, timeLabel };
};

export default function Home() {
  const handleMarketSelect = (market: string) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("preferred_market", market);
    }
  };

  const [usStatus, setUsStatus] = useState<MarketStatus>(() =>
    getMarketStatus("America/New_York", 9, 30, 16, 0)
  );
  const [fiStatus, setFiStatus] = useState<MarketStatus>(() =>
    getMarketStatus("Europe/Helsinki", 10, 0, 18, 30)
  );

  useEffect(() => {
    const id = setInterval(() => {
      setUsStatus(getMarketStatus("America/New_York", 9, 30, 16, 0));
      setFiStatus(getMarketStatus("Europe/Helsinki", 10, 0, 18, 30));
    }, 60 * 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex flex-col">
      {/* Pääsisältö */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 2xl:px-20 py-8 sm:py-12 2xl:py-20">
        {/* Logo & Otsikko */}
        <div className="text-center mb-8 sm:mb-12 2xl:mb-20">
          <div className="inline-flex p-3 sm:p-4 2xl:p-6 bg-gradient-to-br from-cyan-600 to-blue-600 rounded-xl sm:rounded-2xl 2xl:rounded-3xl mb-4 sm:mb-6 2xl:mb-10 shadow-2xl">
            <BarChart3 className="w-12 h-12 sm:w-16 sm:h-16 2xl:w-24 2xl:h-24 text-white" />
          </div>

          <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl 2xl:text-8xl font-bold text-white mb-3 sm:mb-4 2xl:mb-6">
            TradeMaster Pro
          </h1>

          <p className="text-lg sm:text-xl md:text-2xl 2xl:text-4xl text-slate-300 mb-2 2xl:mb-4">
            Datalähtöinen osakeanalyysi
          </p>
          <p className="text-sm sm:text-base 2xl:text-2xl text-slate-400 max-w-xl 2xl:max-w-3xl mx-auto px-2">
            Ammattimaista markkina-analyysiä, reaaliaikaista dataa ja älykkäitä
            työkaluja parempiin sijoituspäätöksiin.
          </p>
        </div>

        {/* Markkinavalitsin */}
        <div className="w-full max-w-4xl 2xl:max-w-6xl px-2 sm:px-0">
          <h2 className="text-center text-base sm:text-lg 2xl:text-3xl text-slate-400 mb-4 sm:mb-6 2xl:mb-10">
            Valitse markkina
          </h2>

          {/* Kaikki markkinat samassa gridissä */}
          <div className="grid grid-cols-1 gap-3 sm:gap-4 2xl:gap-8">
            {/* Suomi - Pääosio */}
            <Link
              href="/fi/dashboard"
              onClick={() => handleMarketSelect("fi")}
              className="group relative overflow-hidden bg-gradient-to-br from-cyan-900/40 to-blue-900/40 hover:from-cyan-900/60 hover:to-blue-900/60 border-2 border-cyan-500/50 hover:border-cyan-400 rounded-xl sm:rounded-2xl 2xl:rounded-3xl p-4 sm:p-6 2xl:p-10 transition-all duration-300 hover:shadow-xl hover:shadow-cyan-500/30 block"
            >
              <div className="absolute top-0 right-0 w-32 h-32 2xl:w-48 2xl:h-48 bg-cyan-500/20 rounded-full blur-3xl group-hover:bg-cyan-500/30 transition-all" />

              {/* Suositeltava badge */}
              <div className="absolute top-3 right-3 2xl:top-6 2xl:right-6 px-2 2xl:px-4 py-1 2xl:py-2 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full text-[10px] 2xl:text-base font-semibold text-white shadow-lg flex items-center gap-1 2xl:gap-2">
                <Sparkles className="w-3 h-3 2xl:w-5 2xl:h-5" />
                Toiminnassa
              </div>

              <div className="relative">
                <div className="flex items-center gap-2 sm:gap-3 2xl:gap-5 mb-3 sm:mb-4 2xl:mb-6">
                  <div className="p-2 sm:p-3 2xl:p-5 bg-cyan-500/30 rounded-lg sm:rounded-xl 2xl:rounded-2xl border border-cyan-500/30">
                    <Flag className="w-5 h-5 sm:w-7 sm:h-7 2xl:w-12 2xl:h-12 text-cyan-300" />
                  </div>
                  <div>
                    <h3 className="text-xl sm:text-2xl 2xl:text-5xl font-bold text-white">Suomi</h3>
                    <p className="text-xs sm:text-sm 2xl:text-xl text-cyan-300">Nasdaq Helsinki</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 2xl:gap-4 mb-3 sm:mb-4 2xl:mb-6">
                  <div className="flex items-center gap-2 2xl:gap-3 text-[11px] sm:text-xs 2xl:text-lg bg-slate-900/50 rounded-lg 2xl:rounded-xl px-2 sm:px-3 2xl:px-5 py-1 sm:py-1.5 2xl:py-3">
                    <span className={`w-2 h-2 2xl:w-3 2xl:h-3 rounded-full ${fiStatus.isOpen ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`}></span>
                    <span className="text-slate-300">{fiStatus.isOpen ? 'Auki' : 'Kiinni'} {fiStatus.timeLabel}</span>
                  </div>
                  <div className="text-[11px] sm:text-xs 2xl:text-lg bg-slate-900/50 rounded-lg 2xl:rounded-xl px-2 sm:px-3 2xl:px-5 py-1 sm:py-1.5 2xl:py-3 text-slate-300">
                    173 osaketta
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 sm:gap-2 2xl:gap-4 mb-3 sm:mb-4 2xl:mb-6 text-[11px] sm:text-xs 2xl:text-lg">
                  <div className="flex items-center gap-1 sm:gap-1.5 2xl:gap-3 text-slate-300">
                    <Sparkles className="w-3 h-3 2xl:w-6 2xl:h-6 text-yellow-400 flex-shrink-0" />
                    <span>Pisteytys</span>
                  </div>
                  <div className="flex items-center gap-1 sm:gap-1.5 2xl:gap-3 text-slate-300">
                    <Newspaper className="w-3 h-3 2xl:w-6 2xl:h-6 text-cyan-400 flex-shrink-0" />
                    <span>Tiedotteet</span>
                  </div>
                  <div className="flex items-center gap-1 sm:gap-1.5 2xl:gap-3 text-slate-300">
                    <LineChart className="w-3 h-3 2xl:w-6 2xl:h-6 text-emerald-400 flex-shrink-0" />
                    <span>Analyysit</span>
                  </div>
                  <div className="flex items-center gap-1 sm:gap-1.5 2xl:gap-3 text-slate-300">
                    <Activity className="w-3 h-3 2xl:w-6 2xl:h-6 text-purple-400 flex-shrink-0" />
                    <span>Seulonta</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 2xl:gap-4 text-sm sm:text-base 2xl:text-2xl text-cyan-300 font-semibold group-hover:gap-3 2xl:group-hover:gap-5 transition-all">
                  <span>Avaa Suomen osakkeet</span>
                  <ChevronRight className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8" />
                </div>
              </div>
            </Link>

            {/* USA & Indeksit samalla rivillä */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 2xl:gap-8">
              {/* USA - Tulossa pian */}
              <div
                className="group relative overflow-hidden bg-slate-800/40 border border-slate-700/40 rounded-xl sm:rounded-2xl 2xl:rounded-3xl p-4 sm:p-5 2xl:p-8 opacity-80 cursor-default"
              >
                <div className="absolute top-0 right-0 w-24 h-24 2xl:w-40 2xl:h-40 bg-purple-500/5 rounded-full blur-2xl" />

                <div className="absolute top-3 right-3 2xl:top-5 2xl:right-5 px-2 2xl:px-4 py-0.5 2xl:py-1.5 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full text-[10px] 2xl:text-sm font-semibold text-white shadow-lg">
                  Tulossa pian
                </div>

                <div className="relative">
                  <div className="flex items-center gap-2 sm:gap-3 2xl:gap-5 mb-2 sm:mb-3 2xl:mb-5">
                    <div className="p-1.5 sm:p-2 2xl:p-4 bg-purple-500/20 rounded-lg 2xl:rounded-xl">
                      <Building2 className="w-5 h-5 sm:w-6 sm:h-6 2xl:w-10 2xl:h-10 text-purple-400" />
                    </div>
                    <div>
                      <h3 className="text-lg sm:text-xl 2xl:text-4xl font-bold text-white">USA</h3>
                      <p className="text-[11px] sm:text-xs 2xl:text-lg text-slate-400">NYSE & NASDAQ</p>
                    </div>
                  </div>

                  <div className="space-y-1 2xl:space-y-2 mb-2 sm:mb-3 2xl:mb-5 text-[11px] sm:text-xs 2xl:text-lg">
                    <div className="flex items-center gap-2 2xl:gap-3 text-slate-400">
                      <TrendingUp className="w-3 h-3 2xl:w-5 2xl:h-5 text-green-400" />
                      <span>S&P 500</span>
                    </div>
                    <div className="flex items-center gap-2 2xl:gap-3 text-slate-400">
                      <Building2 className="w-3 h-3 2xl:w-5 2xl:h-5 text-blue-400" />
                      <span>NYSE & NASDAQ</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 2xl:gap-3 text-slate-500 font-medium text-xs sm:text-sm 2xl:text-xl">
                    <span>Kehitteillä</span>
                  </div>
                </div>
              </div>

              {/* Indeksisijoittaminen */}
              <Link
                href="/indeksit"
                className="group relative overflow-hidden bg-gradient-to-r from-emerald-900/30 to-teal-900/30 hover:from-emerald-900/50 hover:to-teal-900/50 border border-emerald-700/40 hover:border-emerald-500/60 rounded-xl sm:rounded-2xl 2xl:rounded-3xl p-4 sm:p-5 2xl:p-8 transition-all duration-300 hover:shadow-xl hover:shadow-emerald-500/20 block"
              >
                <div className="absolute top-0 right-0 w-24 h-24 2xl:w-40 2xl:h-40 bg-emerald-500/10 rounded-full blur-2xl group-hover:bg-emerald-500/20 transition-all" />

                <div className="relative">
                  <div className="flex items-center gap-2 sm:gap-3 2xl:gap-5 mb-2 sm:mb-3 2xl:mb-5">
                    <div className="p-1.5 sm:p-2 2xl:p-4 bg-emerald-500/20 rounded-lg 2xl:rounded-xl">
                      <PiggyBank className="w-5 h-5 sm:w-6 sm:h-6 2xl:w-10 2xl:h-10 text-emerald-400" />
                    </div>
                    <div>
                      <h3 className="text-lg sm:text-xl 2xl:text-4xl font-bold text-white">Indeksit</h3>
                      <p className="text-[11px] sm:text-xs 2xl:text-lg text-slate-400">Laskuri & vertailu</p>
                    </div>
                  </div>

                  <div className="space-y-1 2xl:space-y-2 mb-2 sm:mb-3 2xl:mb-5 text-[11px] sm:text-xs 2xl:text-lg">
                    <div className="flex items-center gap-2 2xl:gap-3 text-slate-300">
                      <Calculator className="w-3 h-3 2xl:w-5 2xl:h-5 text-emerald-400" />
                      <span>Tuottolaskuri & 8 indeksiä</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 2xl:gap-3 text-emerald-400 font-medium text-xs sm:text-sm 2xl:text-xl group-hover:gap-3 2xl:group-hover:gap-4 transition-all">
                    <span>Avaa</span>
                    <ChevronRight className="w-4 h-4 2xl:w-6 2xl:h-6" />
                  </div>
                </div>
              </Link>
            </div>
          </div>

          {/* Ominaisuudet */}
          <div className="mt-8 sm:mt-12 2xl:mt-20">
            <h3 className="text-center text-base sm:text-lg 2xl:text-3xl text-slate-300 mb-4 sm:mb-6 2xl:mb-10">
              Keskeiset ominaisuudet
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-4 2xl:gap-8">
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-5 2xl:p-8">
                <div className="flex items-center gap-2 sm:gap-3 2xl:gap-4 mb-2 sm:mb-3 2xl:mb-5">
                  <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8 text-yellow-400 flex-shrink-0" />
                  <h4 className="text-white font-semibold text-xs sm:text-base 2xl:text-2xl">Älykäs pisteytys</h4>
                </div>
                <p className="text-[11px] sm:text-sm 2xl:text-xl text-slate-400 line-clamp-3 sm:line-clamp-none">
                  Automaattinen osakkeiden ranking tuotto-, riski- ja fundamenttianalyysillä.
                </p>
              </div>
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-5 2xl:p-8">
                <div className="flex items-center gap-2 sm:gap-3 2xl:gap-4 mb-2 sm:mb-3 2xl:mb-5">
                  <Newspaper className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8 text-cyan-400 flex-shrink-0" />
                  <h4 className="text-white font-semibold text-xs sm:text-base 2xl:text-2xl">Tiedotteet</h4>
                </div>
                <p className="text-[11px] sm:text-sm 2xl:text-xl text-slate-400 line-clamp-3 sm:line-clamp-none">
                  Pörssitiedotteet, sisäpiirikaupat ja uutiset yhdessä näkymässä.
                </p>
              </div>
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-5 2xl:p-8">
                <div className="flex items-center gap-2 sm:gap-3 2xl:gap-4 mb-2 sm:mb-3 2xl:mb-5">
                  <LineChart className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8 text-emerald-400 flex-shrink-0" />
                  <h4 className="text-white font-semibold text-xs sm:text-base 2xl:text-2xl">Markkinakatsaus</h4>
                </div>
                <p className="text-[11px] sm:text-sm 2xl:text-xl text-slate-400 line-clamp-3 sm:line-clamp-none">
                  Indeksit, valuutat, korot ja päivän suurimmat liikkujat.
                </p>
              </div>
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-5 2xl:p-8">
                <div className="flex items-center gap-2 sm:gap-3 2xl:gap-4 mb-2 sm:mb-3 2xl:mb-5">
                  <Shield className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8 text-purple-400 flex-shrink-0" />
                  <h4 className="text-white font-semibold text-xs sm:text-base 2xl:text-2xl">Riskianalyysi</h4>
                </div>
                <p className="text-[11px] sm:text-sm 2xl:text-xl text-slate-400 line-clamp-3 sm:line-clamp-none">
                  Volatiliteetti, drawdown ja fundamentit helposti nähtävillä.
                </p>
              </div>
            </div>
          </div>

          {/* Miksi TradeMaster Pro? */}
          <div className="mt-10 sm:mt-16 2xl:mt-24">
            <h3 className="text-center text-xl sm:text-2xl 2xl:text-5xl font-bold text-white mb-2 sm:mb-3 2xl:mb-6">
              Miksi TradeMaster Pro?
            </h3>
            <p className="text-center text-sm sm:text-base 2xl:text-2xl text-slate-400 mb-6 sm:mb-8 2xl:mb-12 max-w-2xl 2xl:max-w-4xl mx-auto px-2">
              Suomen kattavin osakeanalyysi - kaikki data ja työkalut yhdessä paikassa.
            </p>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 2xl:gap-10">
              {/* Analyysikriteerit */}
              <div className="bg-gradient-to-br from-cyan-900/30 to-blue-900/30 border border-cyan-700/40 rounded-xl sm:rounded-2xl 2xl:rounded-3xl p-4 sm:p-6 2xl:p-10">
                <h4 className="text-base sm:text-lg 2xl:text-3xl font-bold text-cyan-300 mb-3 sm:mb-4 2xl:mb-6 flex items-center gap-2 2xl:gap-4">
                  <Calculator className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8" />
                  Pisteytyksen perusteet
                </h4>
                <div className="space-y-2 sm:space-y-3 2xl:space-y-5 text-xs sm:text-sm 2xl:text-xl">
                  <div className="flex items-start gap-3">
                    <span className="text-cyan-400 font-bold">P/E</span>
                    <span className="text-slate-300">Price-to-Earnings - osakkeen hinta suhteessa tulokseen</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-cyan-400 font-bold">P/B</span>
                    <span className="text-slate-300">Price-to-Book - hinta suhteessa tasearvoon</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-cyan-400 font-bold">ROE</span>
                    <span className="text-slate-300">Return on Equity - oman pääoman tuotto</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-cyan-400 font-bold">Osinko-%</span>
                    <span className="text-slate-300">Osinkotuotto suhteessa hintaan</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-cyan-400 font-bold">Kasvu</span>
                    <span className="text-slate-300">Liikevaihdon ja tuloksen kasvuvauhti</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-cyan-400 font-bold">Velka</span>
                    <span className="text-slate-300">Velkaantumisaste (D/E) ja maksuvalmius</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-cyan-400 font-bold">Beta</span>
                    <span className="text-slate-300">Volatiliteetti suhteessa markkinaan</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-cyan-400 font-bold">Momentti</span>
                    <span className="text-slate-300">3kk ja 12kk hintakehitys</span>
                  </div>
                </div>
              </div>

              {/* Listausperusteet */}
              <div className="bg-gradient-to-br from-purple-900/30 to-pink-900/30 border border-purple-700/40 rounded-xl sm:rounded-2xl 2xl:rounded-3xl p-4 sm:p-6 2xl:p-10">
                <h4 className="text-base sm:text-lg 2xl:text-3xl font-bold text-purple-300 mb-3 sm:mb-4 2xl:mb-6 flex items-center gap-2 2xl:gap-4">
                  <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8" />
                  Näin osakkeet valitaan listoille
                </h4>
                <div className="space-y-3 sm:space-y-4 2xl:space-y-6 text-xs sm:text-sm 2xl:text-xl">
                  <div>
                    <span className="text-yellow-400 font-semibold">Top Suositukset</span>
                    <p className="text-slate-400 mt-1">Korkein kokonaispisteet yhdistäen arvostuksen, laadun ja kasvun. Painotetaan tasapainoisesti kaikkia mittareita.</p>
                  </div>
                  <div>
                    <span className="text-emerald-400 font-semibold">Piilotetut Helmet</span>
                    <p className="text-slate-400 mt-1">Matala P/E ja P/B, mutta vahva ROE ja tuloskasvu. Aliarvostettuja laatuyhtiöitä.</p>
                  </div>
                  <div>
                    <span className="text-orange-400 font-semibold">Nopeat Voitot</span>
                    <p className="text-slate-400 mt-1">Vahva lyhyen aikavälin momentti (3kk tuotto), korkea volyymi ja nouseva trendi.</p>
                  </div>
                  <div>
                    <span className="text-blue-400 font-semibold">Osinko-osakkeet</span>
                    <p className="text-slate-400 mt-1">Korkea ja vakaa osinkotuotto, matala velkaantuminen ja pitkä osinkohistoria.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Kehityssuunnitelma */}
          <div className="mt-8 sm:mt-12 2xl:mt-20">
            <h3 className="text-center text-lg sm:text-xl 2xl:text-4xl font-bold text-white mb-4 sm:mb-6 2xl:mb-10">
              Tulossa seuraavaksi
            </h3>
            <div className="grid grid-cols-2 gap-3 sm:gap-4 2xl:gap-8">
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-5 2xl:p-8 text-center">
                <div className="w-8 h-8 sm:w-10 sm:h-10 2xl:w-16 2xl:h-16 mx-auto mb-2 sm:mb-3 2xl:mb-5 rounded-full bg-emerald-500/20 flex items-center justify-center">
                  <Shield className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8 text-emerald-400" />
                </div>
                <h4 className="text-white font-semibold text-sm sm:text-base 2xl:text-2xl mb-1 sm:mb-2 2xl:mb-4">Salkkuanalyysi</h4>
                <p className="text-[11px] sm:text-xs 2xl:text-lg text-slate-400">Salkun hajauttaminen, riskit ja vertailu indekseihin</p>
              </div>
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-5 2xl:p-8 text-center">
                <div className="w-8 h-8 sm:w-10 sm:h-10 2xl:w-16 2xl:h-16 mx-auto mb-2 sm:mb-3 2xl:mb-5 rounded-full bg-purple-500/20 flex items-center justify-center">
                  <Globe className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8 text-purple-400" />
                </div>
                <h4 className="text-white font-semibold text-sm sm:text-base 2xl:text-2xl mb-1 sm:mb-2 2xl:mb-4">USA-analyysit</h4>
                <p className="text-[11px] sm:text-xs 2xl:text-lg text-slate-400">Syvälliset analyysit S&P 500 ja muille USA-osakkeille</p>
              </div>
            </div>
          </div>

          {/* Erottautuminen */}
          <div className="mt-8 sm:mt-12 2xl:mt-20 bg-gradient-to-r from-cyan-900/20 via-purple-900/20 to-pink-900/20 border border-slate-700/50 rounded-xl sm:rounded-2xl 2xl:rounded-3xl p-4 sm:p-6 2xl:p-10 text-center">
            <h4 className="text-base sm:text-lg 2xl:text-3xl font-bold text-white mb-2 sm:mb-3 2xl:mb-6">
              Kaikki yhdessä paikassa
            </h4>
            <p className="text-slate-400 text-xs sm:text-sm 2xl:text-xl max-w-2xl 2xl:max-w-4xl mx-auto mb-3 sm:mb-4 2xl:mb-8 px-2">
              TradeMaster Pro kokoaa yhteen kurssidatan, pörssitiedotteet, sisäpiirikaupat, fundamenttianalyysit
              ja osakepisteytyksen. Ei enää useiden sivustojen selaamista - löydät kaiken tarvitsemasi
              suomalaisista osakkeista yhdellä sivulla.
            </p>
            <div className="flex flex-wrap justify-center gap-2 sm:gap-4 2xl:gap-6 text-[10px] sm:text-xs 2xl:text-lg text-slate-400">
              <span className="px-2 sm:px-3 2xl:px-5 py-1 2xl:py-2 bg-slate-800/60 rounded-full">Ilmainen käyttö</span>
              <span className="px-2 sm:px-3 2xl:px-5 py-1 2xl:py-2 bg-slate-800/60 rounded-full">Ei rekisteröitymistä</span>
              <span className="px-2 sm:px-3 2xl:px-5 py-1 2xl:py-2 bg-slate-800/60 rounded-full">Reaaliaikainen data</span>
              <span className="px-2 sm:px-3 2xl:px-5 py-1 2xl:py-2 bg-slate-800/60 rounded-full">173+ osaketta</span>
              <span className="px-2 sm:px-3 2xl:px-5 py-1 2xl:py-2 bg-slate-800/60 rounded-full">Suomeksi</span>
            </div>
          </div>
        </div>
      </div>

      {/* Alatunniste */}
      <footer className="border-t border-slate-800 py-4 sm:py-6 2xl:py-10 px-4 2xl:px-20">
        <div className="max-w-4xl 2xl:max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4 2xl:gap-6 text-xs sm:text-sm 2xl:text-xl text-slate-500">
          <div className="flex items-center gap-2 2xl:gap-4">
            <BarChart3 className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8 text-cyan-400" />
            <span>TradeMaster Pro</span>
          </div>
          <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4 2xl:gap-6">
            <a
              href="mailto:sipeee185@gmail.com"
              className="flex items-center gap-1.5 2xl:gap-3 text-slate-400 hover:text-cyan-400 transition-colors"
            >
              <Mail className="w-3.5 h-3.5 sm:w-4 sm:h-4 2xl:w-6 2xl:h-6" />
              <span className="text-[11px] sm:text-sm 2xl:text-lg">Ota yhteyttä</span>
            </a>
            <p className="text-center sm:text-right text-[11px] sm:text-sm 2xl:text-lg">
              Datalähtöistä markkina-analyysiä. Ei sijoitusneuvontaa.
            </p>
          </div>
        </div>
      </footer>
    </main>
  );
}
