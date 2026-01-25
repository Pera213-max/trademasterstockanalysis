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

  const [fiStatus, setFiStatus] = useState<MarketStatus>(() =>
    getMarketStatus("Europe/Helsinki", 10, 0, 18, 30)
  );

  useEffect(() => {
    const id = setInterval(() => {
      setFiStatus(getMarketStatus("Europe/Helsinki", 10, 0, 18, 30));
    }, 60 * 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <main className="min-h-screen bg-slate-900 flex flex-col">
      {/* Pääsisältö */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 2xl:px-20 py-8 sm:py-12 2xl:py-20">
        {/* Logo & Otsikko */}
        <div className="text-center mb-8 sm:mb-12 2xl:mb-20">
          <div className="inline-flex p-3 sm:p-4 2xl:p-6 bg-sky-600 rounded-xl sm:rounded-2xl 2xl:rounded-3xl mb-4 sm:mb-6 2xl:mb-10">
            <BarChart3 className="w-12 h-12 sm:w-16 sm:h-16 2xl:w-24 2xl:h-24 text-white" />
          </div>

          <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl 2xl:text-8xl font-bold text-white mb-3 sm:mb-4 2xl:mb-6">
            OsakedataX
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
              className="group relative bg-slate-800/60 hover:bg-slate-800 border border-sky-500/40 hover:border-sky-500/60 rounded-xl sm:rounded-2xl 2xl:rounded-3xl p-4 sm:p-6 2xl:p-10 transition-all block"
            >
              {/* Suositeltava badge */}
              <div className="absolute top-3 right-3 2xl:top-6 2xl:right-6 px-2 2xl:px-4 py-1 2xl:py-2 bg-sky-600 rounded-full text-[10px] 2xl:text-base font-semibold text-white flex items-center gap-1 2xl:gap-2">
                <Sparkles className="w-3 h-3 2xl:w-5 2xl:h-5" />
                Toiminnassa
              </div>

              <div>
                <div className="flex items-center gap-2 sm:gap-3 2xl:gap-5 mb-3 sm:mb-4 2xl:mb-6">
                  <div className="p-2 sm:p-3 2xl:p-5 bg-sky-500/20 rounded-lg sm:rounded-xl 2xl:rounded-2xl border border-sky-500/30">
                    <Flag className="w-5 h-5 sm:w-7 sm:h-7 2xl:w-12 2xl:h-12 text-sky-300" />
                  </div>
                  <div>
                    <h3 className="text-xl sm:text-2xl 2xl:text-5xl font-bold text-white">Suomi</h3>
                    <p className="text-xs sm:text-sm 2xl:text-xl text-sky-400">Nasdaq Helsinki</p>
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
                    <Sparkles className="w-3 h-3 2xl:w-6 2xl:h-6 text-sky-400 flex-shrink-0" />
                    <span>Pisteytys</span>
                  </div>
                  <div className="flex items-center gap-1 sm:gap-1.5 2xl:gap-3 text-slate-300">
                    <Newspaper className="w-3 h-3 2xl:w-6 2xl:h-6 text-sky-400 flex-shrink-0" />
                    <span>Tiedotteet</span>
                  </div>
                  <div className="flex items-center gap-1 sm:gap-1.5 2xl:gap-3 text-slate-300">
                    <LineChart className="w-3 h-3 2xl:w-6 2xl:h-6 text-sky-400 flex-shrink-0" />
                    <span>Analyysit</span>
                  </div>
                  <div className="flex items-center gap-1 sm:gap-1.5 2xl:gap-3 text-slate-300">
                    <Activity className="w-3 h-3 2xl:w-6 2xl:h-6 text-sky-400 flex-shrink-0" />
                    <span>Seulonta</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 2xl:gap-4 text-sm sm:text-base 2xl:text-2xl text-sky-400 font-semibold group-hover:gap-3 2xl:group-hover:gap-5 transition-all">
                  <span>Avaa Suomen osakkeet</span>
                  <ChevronRight className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8" />
                </div>
              </div>
            </Link>

            {/* Indeksisijoittaminen */}
            <Link
                href="/indeksit"
                className="group bg-slate-800/40 hover:bg-slate-800/60 border border-slate-700/50 hover:border-slate-600 rounded-xl sm:rounded-2xl 2xl:rounded-3xl p-4 sm:p-5 2xl:p-8 transition-all block"
              >
                <div>
                  <div className="flex items-center gap-2 sm:gap-3 2xl:gap-5 mb-2 sm:mb-3 2xl:mb-5">
                    <div className="p-1.5 sm:p-2 2xl:p-4 bg-sky-500/20 rounded-lg 2xl:rounded-xl">
                      <PiggyBank className="w-5 h-5 sm:w-6 sm:h-6 2xl:w-10 2xl:h-10 text-sky-400" />
                    </div>
                    <div>
                      <h3 className="text-lg sm:text-xl 2xl:text-4xl font-bold text-white">Indeksit</h3>
                      <p className="text-[11px] sm:text-xs 2xl:text-lg text-slate-400">Laskuri & vertailu</p>
                    </div>
                  </div>

                  <div className="space-y-1 2xl:space-y-2 mb-2 sm:mb-3 2xl:mb-5 text-[11px] sm:text-xs 2xl:text-lg">
                    <div className="flex items-center gap-2 2xl:gap-3 text-slate-300">
                      <Calculator className="w-3 h-3 2xl:w-5 2xl:h-5 text-sky-400" />
                      <span>Tuottolaskuri & 8 indeksiä</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 2xl:gap-3 text-sky-400 font-medium text-xs sm:text-sm 2xl:text-xl group-hover:gap-3 2xl:group-hover:gap-4 transition-all">
                    <span>Avaa</span>
                    <ChevronRight className="w-4 h-4 2xl:w-6 2xl:h-6" />
                  </div>
                </div>
              </Link>
          </div>

          {/* Ominaisuudet */}
          <div className="mt-8 sm:mt-12 2xl:mt-20">
            <h3 className="text-center text-base sm:text-lg 2xl:text-3xl text-slate-300 mb-4 sm:mb-6 2xl:mb-10">
              Keskeiset ominaisuudet
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-4 2xl:gap-6">
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-4 2xl:p-6">
                <div className="flex items-center gap-2 2xl:gap-3 mb-2 2xl:mb-4">
                  <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-7 2xl:h-7 text-sky-400 flex-shrink-0" />
                  <h4 className="text-white font-semibold text-xs sm:text-sm 2xl:text-xl">Pisteytys</h4>
                </div>
                <p className="text-[10px] sm:text-xs 2xl:text-lg text-slate-400">
                  173 osaketta pisteytettynä
                </p>
              </div>
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-4 2xl:p-6">
                <div className="flex items-center gap-2 2xl:gap-3 mb-2 2xl:mb-4">
                  <Newspaper className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-7 2xl:h-7 text-sky-400 flex-shrink-0" />
                  <h4 className="text-white font-semibold text-xs sm:text-sm 2xl:text-xl">Tiedotteet</h4>
                </div>
                <p className="text-[10px] sm:text-xs 2xl:text-lg text-slate-400">
                  Nasdaq & Kauppalehti
                </p>
              </div>
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-4 2xl:p-6">
                <div className="flex items-center gap-2 2xl:gap-3 mb-2 2xl:mb-4">
                  <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-7 2xl:h-7 text-sky-400 flex-shrink-0" />
                  <h4 className="text-white font-semibold text-xs sm:text-sm 2xl:text-xl">Momentum</h4>
                </div>
                <p className="text-[10px] sm:text-xs 2xl:text-lg text-slate-400">
                  RSI, volyymi, nousijat
                </p>
              </div>
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-4 2xl:p-6">
                <div className="flex items-center gap-2 2xl:gap-3 mb-2 2xl:mb-4">
                  <Globe className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-7 2xl:h-7 text-sky-400 flex-shrink-0" />
                  <h4 className="text-white font-semibold text-xs sm:text-sm 2xl:text-xl">Markkinat</h4>
                </div>
                <p className="text-[10px] sm:text-xs 2xl:text-lg text-slate-400">
                  Indeksit, valuutat, korot
                </p>
              </div>
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-4 2xl:p-6">
                <div className="flex items-center gap-2 2xl:gap-3 mb-2 2xl:mb-4">
                  <span className="text-lg 2xl:text-2xl">🥇</span>
                  <h4 className="text-white font-semibold text-xs sm:text-sm 2xl:text-xl">Jalometallit</h4>
                </div>
                <p className="text-[10px] sm:text-xs 2xl:text-lg text-slate-400">
                  Kulta & hopea chartit
                </p>
              </div>
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-4 2xl:p-6">
                <div className="flex items-center gap-2 2xl:gap-3 mb-2 2xl:mb-4">
                  <Activity className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-7 2xl:h-7 text-sky-400 flex-shrink-0" />
                  <h4 className="text-white font-semibold text-xs sm:text-sm 2xl:text-xl">Seulonta</h4>
                </div>
                <p className="text-[10px] sm:text-xs 2xl:text-lg text-slate-400">
                  Suodata kriteereilläsi
                </p>
              </div>
            </div>
          </div>

          {/* Miksi OsakedataX? */}
          <div className="mt-10 sm:mt-16 2xl:mt-24">
            <h3 className="text-center text-xl sm:text-2xl 2xl:text-5xl font-bold text-white mb-2 sm:mb-3 2xl:mb-6">
              Miksi OsakedataX?
            </h3>
            <p className="text-center text-sm sm:text-base 2xl:text-2xl text-slate-400 mb-6 sm:mb-8 2xl:mb-12 max-w-2xl 2xl:max-w-4xl mx-auto px-2">
              Suomen kattavin osakeanalyysi - kaikki data ja työkalut yhdessä paikassa.
            </p>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 2xl:gap-10">
              {/* Analyysikriteerit */}
              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl sm:rounded-2xl 2xl:rounded-3xl p-4 sm:p-6 2xl:p-10">
                <h4 className="text-base sm:text-lg 2xl:text-3xl font-bold text-sky-400 mb-3 sm:mb-4 2xl:mb-6 flex items-center gap-2 2xl:gap-4">
                  <Calculator className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8" />
                  Pisteytyksen perusteet
                </h4>
                <div className="space-y-2 sm:space-y-3 2xl:space-y-5 text-xs sm:text-sm 2xl:text-xl">
                  <div className="flex items-start gap-3">
                    <span className="text-sky-400 font-bold">P/E</span>
                    <span className="text-slate-300">Price-to-Earnings - osakkeen hinta suhteessa tulokseen</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-sky-400 font-bold">P/B</span>
                    <span className="text-slate-300">Price-to-Book - hinta suhteessa tasearvoon</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-sky-400 font-bold">ROE</span>
                    <span className="text-slate-300">Return on Equity - oman pääoman tuotto</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-sky-400 font-bold">Osinko-%</span>
                    <span className="text-slate-300">Osinkotuotto suhteessa hintaan</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-sky-400 font-bold">Kasvu</span>
                    <span className="text-slate-300">Liikevaihdon ja tuloksen kasvuvauhti</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-sky-400 font-bold">Velka</span>
                    <span className="text-slate-300">Velkaantumisaste (D/E) ja maksuvalmius</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-sky-400 font-bold">Beta</span>
                    <span className="text-slate-300">Volatiliteetti suhteessa markkinaan</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-sky-400 font-bold">Momentti</span>
                    <span className="text-slate-300">3kk ja 12kk hintakehitys</span>
                  </div>
                </div>
              </div>

              {/* Mitä dataa sivulla on */}
              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl sm:rounded-2xl 2xl:rounded-3xl p-4 sm:p-6 2xl:p-10">
                <h4 className="text-base sm:text-lg 2xl:text-3xl font-bold text-sky-400 mb-3 sm:mb-4 2xl:mb-6 flex items-center gap-2 2xl:gap-4">
                  <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5 2xl:w-8 2xl:h-8" />
                  Mitä dataa OsakedataX tarjoaa
                </h4>
                <div className="space-y-3 sm:space-y-4 2xl:space-y-6 text-xs sm:text-sm 2xl:text-xl">
                  <div>
                    <span className="text-sky-400 font-semibold">173 Suomiosaketta</span>
                    <p className="text-slate-400 mt-1">Kaikki Nasdaq Helsingin osakkeet pisteytettyinä ja analysoituna. Löydä parhaat sijoituskohteet.</p>
                  </div>
                  <div>
                    <span className="text-sky-400 font-semibold">Viikon Momentum</span>
                    <p className="text-slate-400 mt-1">Nousijat, laskijat, volyymisignaalit ja RSI-indikaattorit. Näe mihin markkinat liikkuvat.</p>
                  </div>
                  <div>
                    <span className="text-sky-400 font-semibold">Pörssitiedotteet</span>
                    <p className="text-slate-400 mt-1">Tuoreimmat yhtiötiedotteet, sisäpiirikaupat ja IR-uutiset suoraan Nasdaqilta ja Kauppalehdestä.</p>
                  </div>
                  <div>
                    <span className="text-sky-400 font-semibold">Jalometallit</span>
                    <p className="text-slate-400 mt-1">Kullan ja hopean reaaliaikaiset hinnat, chartit ja tunnusluvut USD:ssa.</p>
                  </div>
                  <div>
                    <span className="text-sky-400 font-semibold">Markkinakatsaus</span>
                    <p className="text-slate-400 mt-1">OMXH25, Euro Stoxx, DAX, valuutat, korot ja VIX - kaikki yhdessä näkymässä.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Miten käyttää dataa */}
          <div className="mt-8 sm:mt-12 2xl:mt-20">
            <h3 className="text-center text-lg sm:text-xl 2xl:text-4xl font-bold text-white mb-4 sm:mb-6 2xl:mb-10">
              Miten käyttää OsakedataX:ää
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4 2xl:gap-8">
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-5 2xl:p-8 text-center">
                <div className="w-10 h-10 sm:w-12 sm:h-12 2xl:w-16 2xl:h-16 mx-auto mb-2 sm:mb-3 2xl:mb-5 rounded-full bg-sky-500/20 flex items-center justify-center text-xl sm:text-2xl 2xl:text-3xl text-sky-400">
                  1
                </div>
                <h4 className="text-white font-semibold text-sm sm:text-base 2xl:text-2xl mb-1 sm:mb-2 2xl:mb-4">Seulo osakkeet</h4>
                <p className="text-[11px] sm:text-xs 2xl:text-lg text-slate-400">Käytä seulontaa löytääksesi osakkeet, jotka täyttävät kriteerisi (P/E, osinko, kasvu jne.)</p>
              </div>
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-5 2xl:p-8 text-center">
                <div className="w-10 h-10 sm:w-12 sm:h-12 2xl:w-16 2xl:h-16 mx-auto mb-2 sm:mb-3 2xl:mb-5 rounded-full bg-sky-500/20 flex items-center justify-center text-xl sm:text-2xl 2xl:text-3xl text-sky-400">
                  2
                </div>
                <h4 className="text-white font-semibold text-sm sm:text-base 2xl:text-2xl mb-1 sm:mb-2 2xl:mb-4">Analysoi</h4>
                <p className="text-[11px] sm:text-xs 2xl:text-lg text-slate-400">Tutki osakkeen tunnusluvut, tekninen analyysi ja viimeisimmät tiedotteet osakkeen sivulla</p>
              </div>
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg sm:rounded-xl 2xl:rounded-2xl p-3 sm:p-5 2xl:p-8 text-center">
                <div className="w-10 h-10 sm:w-12 sm:h-12 2xl:w-16 2xl:h-16 mx-auto mb-2 sm:mb-3 2xl:mb-5 rounded-full bg-sky-500/20 flex items-center justify-center text-xl sm:text-2xl 2xl:text-3xl text-sky-400">
                  3
                </div>
                <h4 className="text-white font-semibold text-sm sm:text-base 2xl:text-2xl mb-1 sm:mb-2 2xl:mb-4">Seuraa markkinoita</h4>
                <p className="text-[11px] sm:text-xs 2xl:text-lg text-slate-400">Pidä silmällä momenttia, tiedotteita ja makrodataa - pysyt ajan tasalla markkinoista</p>
              </div>
            </div>
          </div>

          {/* Erottautuminen */}
          <div className="mt-8 sm:mt-12 2xl:mt-20 bg-slate-800/50 border border-slate-700/50 rounded-xl sm:rounded-2xl 2xl:rounded-3xl p-4 sm:p-6 2xl:p-10 text-center">
            <h4 className="text-base sm:text-lg 2xl:text-3xl font-bold text-white mb-2 sm:mb-3 2xl:mb-6">
              Kaikki yhdessä paikassa
            </h4>
            <p className="text-slate-400 text-xs sm:text-sm 2xl:text-xl max-w-2xl 2xl:max-w-4xl mx-auto mb-3 sm:mb-4 2xl:mb-8 px-2">
              OsakedataX kokoaa yhteen kurssidatan, pörssitiedotteet, sisäpiirikaupat, fundamenttianalyysit
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
            <span>OsakedataX</span>
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
