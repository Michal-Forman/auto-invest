import { AlertTriangle, BarChart2, Bell, Bitcoin, Globe, Lock, RefreshCw, Smartphone, TrendingDown, TrendingUp, Zap } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const APP_URL = "https://auto-invest-web.vercel.app/app";

// --- Typewriter hook ---
const TYPEWRITER_OPTIONS = ["Bez námahy.", "Bez emocí.", "Bez stresu.", "Automaticky."];

function useTypewriter(options: string[], speed = 80, deleteSpeed = 45, pause = 2200) {
  const [displayText, setDisplayText] = useState("");
  const [optionIndex, setOptionIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const current = options[optionIndex];
    let timeout: ReturnType<typeof setTimeout>;

    if (!isDeleting && displayText === current) {
      timeout = setTimeout(() => setIsDeleting(true), pause);
    } else if (isDeleting && displayText === "") {
      setIsDeleting(false);
      setOptionIndex((i) => (i + 1) % options.length);
    } else if (isDeleting) {
      timeout = setTimeout(() => setDisplayText(current.slice(0, displayText.length - 1)), deleteSpeed);
    } else {
      timeout = setTimeout(() => setDisplayText(current.slice(0, displayText.length + 1)), speed);
    }

    return () => clearTimeout(timeout);
  }, [displayText, isDeleting, optionIndex, options, speed, deleteSpeed, pause]);

  return displayText;
}

// --- Scroll-triggered fade-in hook ---
function useFadeIn() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("landing-visible");
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return ref;
}

// --- Navbar ---
function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 bg-white border-b border-slate-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <a href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-blue-900 flex items-center justify-center">
            <svg viewBox="0 0 20 20" className="w-4 h-4 text-white fill-current">
              <rect x="2" y="12" width="3" height="6" rx="1"/>
              <rect x="7" y="8" width="3" height="10" rx="1"/>
              <rect x="12" y="4" width="3" height="14" rx="1"/>
              <path d="M3.5 11 L8.5 7 L13.5 3" stroke="white" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="font-bold text-blue-900 text-lg">auto-invest</span>
        </a>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8">
          <a href="#how-it-works" className="text-sm text-slate-600 hover:text-blue-900 transition-colors">Jak to funguje</a>
          <a href="#features" className="text-sm text-slate-600 hover:text-blue-900 transition-colors">Funkce</a>
          <a href="#strategy" className="text-sm text-slate-600 hover:text-blue-900 transition-colors">Strategie</a>
          <a href="#faq" className="text-sm text-slate-600 hover:text-blue-900 transition-colors">FAQ</a>
        </div>

        {/* CTA + mobile menu button */}
        <div className="flex items-center gap-3">
          <a
            href={APP_URL}
            className="hidden sm:inline-flex items-center gap-1 bg-blue-900 text-white text-sm font-medium px-4 py-2 rounded-md hover:bg-blue-800 transition-colors"
          >
            Začít investovat →
          </a>
          <button
            className="md:hidden p-2 text-slate-600"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Menu"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              {menuOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
                : <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16"/>
              }
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 py-4 flex flex-col gap-4">
          <a href="#how-it-works" className="text-sm text-slate-600" onClick={() => setMenuOpen(false)}>Jak to funguje</a>
          <a href="#features" className="text-sm text-slate-600" onClick={() => setMenuOpen(false)}>Funkce</a>
          <a href="#strategy" className="text-sm text-slate-600" onClick={() => setMenuOpen(false)}>Strategie</a>
          <a href="#faq" className="text-sm text-slate-600" onClick={() => setMenuOpen(false)}>FAQ</a>
          <a href={APP_URL} className="inline-flex items-center gap-1 bg-blue-900 text-white text-sm font-medium px-4 py-2 rounded-md w-fit">
            Začít investovat →
          </a>
        </div>
      )}
    </nav>
  );
}

// --- Hero ---
function Hero() {
  const ref = useFadeIn();
  const typedText = useTypewriter(TYPEWRITER_OPTIONS);
  return (
    <section className="bg-white overflow-hidden">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 md:py-24 flex flex-col lg:flex-row items-center gap-12">
        {/* Left content */}
        <div ref={ref} className="landing-fade flex-1 max-w-xl">
          <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-900 text-xs font-medium px-3 py-1 rounded-full border border-blue-200 mb-6">
            <Zap className="w-3 h-3" /> Automatické investování
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-slate-900 leading-tight mb-4">
            Investuj pravidelně.<br/>
            <span>{typedText}</span><span className="typewriter-cursor">|</span>
          </h1>
          <p className="text-slate-600 text-lg mb-8 leading-relaxed">
            auto-invest za tebe každý týden nakoupí ETF a Bitcoin — chytře rozdělí peníze tam, kde jsou ceny nejvíce pod historickým maximem.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 mb-8">
            <a
              href={APP_URL}
              className="inline-flex items-center justify-center gap-1 bg-blue-900 text-white font-medium px-6 py-3 rounded-md hover:bg-blue-800 transition-colors text-sm"
            >
              Vyzkoušet zdarma →
            </a>
            <a
              href="#how-it-works"
              className="inline-flex items-center justify-center gap-1 border border-slate-300 text-slate-700 font-medium px-6 py-3 rounded-md hover:bg-slate-50 transition-colors text-sm"
            >
              Jak to funguje?
            </a>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-500">
            <span className="flex items-center gap-1.5"><RefreshCw className="w-3.5 h-3.5" /> Plně automatické</span>
            <span className="text-slate-300">·</span>
            <span className="flex items-center gap-1.5"><TrendingUp className="w-3.5 h-3.5" /> Trading212 + Coinmate</span>
            <span className="text-slate-300">·</span>
            <span className="flex items-center gap-1.5"><Lock className="w-3.5 h-3.5" /> Zabezpečené přes Google</span>
          </div>
        </div>

        {/* Right: dashboard mockup */}
        <div className="flex-1 flex justify-center lg:justify-end w-full max-w-md">
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg overflow-hidden w-full" style={{borderTop: "3px solid #1e3a8a"}}>
            <div className="px-5 pt-5 pb-4 border-b border-slate-100">
              <p className="text-xs text-slate-500 mb-1">Příští investice</p>
              <p className="text-2xl font-bold text-slate-900">2 500 Kč</p>
              <p className="text-xs text-slate-400 mt-1">naplánováno na pátek</p>
            </div>
            <div className="px-5 py-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-slate-400 uppercase">
                    <th className="text-left pb-2 font-medium">Nástroj</th>
                    <th className="text-right pb-2 font-medium">Částka</th>
                    <th className="text-right pb-2 font-medium">Stav</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr>
                    <td className="py-2.5 font-medium text-slate-800">VWCE</td>
                    <td className="py-2.5 text-right text-slate-600">850 Kč</td>
                    <td className="py-2.5 text-right">
                      <span className="bg-emerald-100 text-emerald-700 text-xs font-medium px-2 py-0.5 rounded">FILLED</span>
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2.5 font-medium text-slate-800">CSPX</td>
                    <td className="py-2.5 text-right text-slate-600">620 Kč</td>
                    <td className="py-2.5 text-right">
                      <span className="bg-slate-100 text-slate-600 text-xs font-medium px-2 py-0.5 rounded">CREATED</span>
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2.5 font-medium text-slate-800">BTC</td>
                    <td className="py-2.5 text-right text-slate-600">480 Kč</td>
                    <td className="py-2.5 text-right">
                      <span className="bg-red-100 text-red-700 text-xs font-medium px-2 py-0.5 rounded">FAILED</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="px-5 pb-4">
              <div className="bg-slate-50 rounded-md px-3 py-2 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                <span className="text-xs text-slate-500">Automaticky každý pátek v 09:00</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// --- Problem ---
function Problem() {
  const ref = useFadeIn();
  const problems = [
    { icon: <AlertTriangle className="w-6 h-6 text-amber-500" />, title: "Zapomínáš", desc: "Chceš investovat každý měsíc, ale v den výplaty na to zapomeneš nebo to odkládáš." },
    { icon: <TrendingDown className="w-6 h-6 text-red-500" />, title: "Investuješ z emocí", desc: "Když trhy padají, bojíš se nakoupit. Když rostou, lituješ, že jsi nenakoupil dřív." },
    { icon: <BarChart2 className="w-6 h-6 text-blue-500" />, title: "Neumíš rozdělit peníze", desc: "Nevíš, kolik dát do ETF, kolik do BTC a kdy přidat víc do toho, co zlevnilo." },
  ];

  return (
    <section id="problem" className="bg-slate-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-16 md:py-20 text-center">
        <div ref={ref} className="landing-fade">
          <p className="text-xs font-semibold tracking-widest text-blue-600 uppercase mb-3">Problém</p>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-12">
            Ručně investovat? To nikdo nedělá dlouhodobě.
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {problems.map((p) => (
              <div key={p.title} className="bg-white rounded-xl border border-slate-200 p-6 text-left shadow-sm">
                <div className="mb-3">{p.icon}</div>
                <h3 className="font-semibold text-slate-900 mb-2">{p.title}</h3>
                <p className="text-sm text-slate-600 leading-relaxed">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// --- How It Works ---
function HowItWorks() {
  const ref = useFadeIn();
  const steps = [
    { n: "1", title: "Propoj své účty", desc: "Zadáš API klíče od Trading212 a Coinmate. Žádné heslo, jen přístup k obchodování." },
    { n: "2", title: "Nastav investiční plán", desc: "Zvol částku a interval (denně, týdně, měsíčně). My se postaráme o zbytek." },
    { n: "3", title: "Sleduj, jak roste portfolio", desc: "Každý nákup vidíš v přehledném dashboardu. Statistiky, grafy, historie — vše na jednom místě." },
  ];

  return (
    <section id="how-it-works" className="bg-white">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 md:py-20 text-center">
        <div ref={ref} className="landing-fade">
          <p className="text-xs font-semibold tracking-widest text-blue-600 uppercase mb-3">Jak to funguje</p>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-12">
            Nastav jednou. Investuj automaticky.
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {steps.map((s) => (
              <div key={s.n} className="flex flex-col items-center text-center">
                <div className="text-7xl font-bold text-blue-900/10 mb-4 leading-none select-none">{s.n}</div>
                <h3 className="font-semibold text-slate-900 text-lg mb-2">{s.title}</h3>
                <p className="text-sm text-slate-600 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// --- Features ---
function Features() {
  const ref = useFadeIn();
  const features = [
    { icon: <Zap className="w-5 h-5 text-blue-600" />, title: "Automatické spouštění", desc: "Investice probíhají přesně podle tvého rozvrhu, bez jakéhokoliv zásahu z tvé strany." },
    { icon: <TrendingDown className="w-5 h-5 text-blue-600" />, title: "Chytrá alokace dle ATH", desc: "Více peněz tam, kde je cena pod historickým maximem. Automatický contrarian investing." },
    { icon: <Globe className="w-5 h-5 text-blue-600" />, title: "ETF + Bitcoin", desc: "Trading212 pro diverzifikovaná ETF (VWCE, CSPX, NASDAQ…) a Coinmate pro Bitcoin." },
    { icon: <BarChart2 className="w-5 h-5 text-blue-600" />, title: "Dashboard s analytikou", desc: "Grafy investic v čase, rozdělení portfolia, průběh objednávek — vše přehledně." },
    { icon: <Bell className="w-5 h-5 text-blue-600" />, title: "E-mailové notifikace", desc: "Dostaneš upozornění, pokud se nákup nezdaří nebo dojde k problému s API." },
    { icon: <Smartphone className="w-5 h-5 text-blue-600" />, title: "PWA aplikace", desc: "Přidej si auto-invest na plochu telefonu jako nativní aplikaci." },
  ];

  return (
    <section id="features" className="bg-slate-50">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 md:py-20 text-center">
        <div ref={ref} className="landing-fade">
          <p className="text-xs font-semibold tracking-widest text-blue-600 uppercase mb-3">Funkce</p>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-12">
            Vše, co potřebuješ k automatickému investování
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((f) => (
              <div key={f.title} className="bg-white rounded-xl border border-slate-200 p-6 text-left shadow-sm">
                <div className="mb-3">{f.icon}</div>
                <h3 className="font-semibold text-slate-900 mb-2">{f.title}</h3>
                <p className="text-sm text-slate-600 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// --- Strategy ---
function Strategy() {
  const ref = useFadeIn();
  const instruments = [
    { name: "VWCE", drop: "-8%", mult: "1.1×", alloc: "20%", color: "text-emerald-600", bg: "bg-emerald-50" },
    { name: "CSPX", drop: "-22%", mult: "1.3×", alloc: "35%", color: "text-amber-600", bg: "bg-amber-50" },
    { name: "BTC",  drop: "-48%", mult: "1.7×", alloc: "45%", color: "text-red-500",   bg: "bg-red-50"   },
  ];

  return (
    <section id="strategy" className="bg-white">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 md:py-20">
        <div ref={ref} className="landing-fade grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          {/* Text */}
          <div>
            <p className="text-xs font-semibold tracking-widest text-blue-600 uppercase mb-3">Strategie</p>
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-6">
              Nakupuj více, když jsou ceny dole
            </h2>
            <div className="space-y-4 text-slate-600 leading-relaxed">
              <p>Většina lidí nakupuje méně, když trhy klesají — ze strachu. auto-invest dělá pravý opak.</p>
              <p>Pro každý nástroj v portfoliu sledujeme, jak daleko je jeho cena od historického maxima (ATH). Čím větší propad, tím vyšší váha při dalším nákupu.</p>
              <p>Výsledek? Přirozeně nakupuješ více, když jsou věci levné — a méně, když jsou drahé.</p>
            </div>
          </div>

          {/* Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 bg-slate-50">
              <p className="text-sm font-semibold text-slate-700">Alokace dle propadu od ATH</p>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-400 uppercase border-b border-slate-100">
                  <th className="text-left px-5 py-3 font-medium">Nástroj</th>
                  <th className="text-right px-5 py-3 font-medium">Propad od ATH</th>
                  <th className="text-right px-5 py-3 font-medium">Násobič</th>
                  <th className="text-right px-5 py-3 font-medium">Alokace</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {instruments.map((i) => (
                  <tr key={i.name}>
                    <td className="px-5 py-3.5 font-semibold text-slate-800">{i.name}</td>
                    <td className={`px-5 py-3.5 text-right font-medium ${i.color}`}>{i.drop}</td>
                    <td className="px-5 py-3.5 text-right">
                      <span className={`${i.bg} ${i.color} text-xs font-medium px-2 py-0.5 rounded`}>{i.mult}</span>
                    </td>
                    <td className="px-5 py-3.5 text-right font-medium text-slate-700">{i.alloc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-5 py-3 border-t border-slate-100">
              <p className="text-xs text-slate-400">* Vyšší propad = vyšší váha při nákupu</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// --- Platforms ---
function Platforms() {
  const ref = useFadeIn();
  return (
    <section className="bg-slate-50">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12 md:py-16 text-center">
        <div ref={ref} className="landing-fade">
          <h2 className="text-lg font-semibold text-slate-700 mb-8">Funguje s těmito platformami</h2>
          <div className="flex flex-col sm:flex-row gap-5 justify-center">
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex-1 max-w-xs mx-auto sm:mx-0">
              <img src="/trading212-logo.jpg" alt="Trading212" className="h-8 w-auto mx-auto block object-contain mb-3" />
              <p className="text-sm text-slate-500">ETF a akcie</p>
              <p className="text-xs text-slate-400 mt-2">Diverzifikovaná ETF portfolia</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex-1 max-w-xs mx-auto sm:mx-0">
              <img src="/coinmate-logo.jpg" alt="Coinmate" className="h-8 w-auto mx-auto block object-contain mb-3" />
              <p className="text-sm text-slate-500">Bitcoin</p>
              <p className="text-xs text-slate-400 mt-2">Bitcoin nákupy v CZK</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// --- Stats ---
function Stats() {
  const ref = useFadeIn();
  const stats = [
    { value: "10+", label: "portfoliových nástrojů" },
    { value: "2",   label: "podporované burzy" },
    { value: "100%", label: "automatické" },
    { value: "0 Kč", label: "poplatek za aplikaci" },
  ];

  return (
    <section className="bg-white">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12 md:py-16">
        <div ref={ref} className="landing-fade grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {stats.map((s) => (
            <div key={s.label}>
              <div className="text-3xl md:text-4xl font-bold text-blue-900 mb-1">{s.value}</div>
              <div className="text-sm text-slate-500">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// --- FAQ ---
function FAQ() {
  const ref = useFadeIn();
  const [open, setOpen] = useState<number | null>(null);

  const items = [
    {
      q: "Je auto-invest bezpečný?",
      a: "Používáme pouze API klíče s oprávněním k obchodování — žádný výběr prostředků přes naše API není možný. Přihlašuješ se přes Google účet.",
    },
    {
      q: "Kolik to stojí?",
      a: "auto-invest je zdarma. Platíš pouze standardní poplatky svých brokerů (Trading212 a Coinmate).",
    },
    {
      q: "Jaké ETF jsou v portfoliu?",
      a: "Výběr nástrojů odpovídá tvému nastavení pí v Trading212. Standardně VWCE, CSPX, EMIM, XNAQ, VERG a další.",
    },
    {
      q: "Co se stane, když selže nákup?",
      a: "Dostaneš e-mail s upozorněním. Objednávky sledujeme 14 dní — pokud se neplní, označíme run jako FAILED.",
    },
    {
      q: "Funguje to i pro Bitcoin?",
      a: "Ano. Přes Coinmate nakupujeme BTC automaticky spolu s ETF v jednom cyklu.",
    },
  ];

  return (
    <section id="faq" className="bg-slate-50">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-16 md:py-20">
        <div ref={ref} className="landing-fade text-center mb-10">
          <p className="text-xs font-semibold tracking-widest text-blue-600 uppercase mb-3">Časté otázky</p>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-900">Máš otázky? Máme odpovědi.</h2>
        </div>
        <div className="space-y-2">
          {items.map((item, i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <button
                className="w-full text-left px-5 py-4 flex items-center justify-between gap-4"
                onClick={() => setOpen(open === i ? null : i)}
              >
                <span className="font-medium text-slate-800 text-sm">{item.q}</span>
                <svg
                  className={`w-4 h-4 text-slate-400 flex-shrink-0 transition-transform ${open === i ? "rotate-180" : ""}`}
                  fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7"/>
                </svg>
              </button>
              {open === i && (
                <div className="px-5 pb-4 text-sm text-slate-600 leading-relaxed border-t border-slate-100 pt-3">
                  {item.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// --- Final CTA ---
function FinalCTA() {
  const ref = useFadeIn();
  return (
    <section className="bg-blue-900">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 md:py-20 text-center">
        <div ref={ref} className="landing-fade">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Začni investovat automaticky ještě dnes.
          </h2>
          <p className="text-blue-200 mb-8 text-lg">
            Žádná kreditní karta. Žádná složitá nastavení. Stačí Google účet.
          </p>
          <a
            href={APP_URL}
            className="inline-flex items-center gap-1 bg-white text-blue-900 font-semibold px-8 py-3.5 rounded-md hover:bg-blue-50 transition-colors text-sm"
          >
            Vyzkoušet zdarma →
          </a>
          <p className="text-blue-300 text-xs mt-4">
            Přihlášení přes Google · Bezplatné · Kdykoliv zrušíš
          </p>
        </div>
      </div>
    </section>
  );
}

// --- Footer ---
function Footer() {
  return (
    <footer className="bg-white border-t border-slate-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-slate-500">
        <span>auto-invest © 2025</span>
        <a href={APP_URL} className="text-blue-900 hover:underline font-medium">
          Přejít do aplikace →
        </a>
      </div>
    </footer>
  );
}

// --- Landing page styles injected via a style tag in the component ---
const landingStyles = `
  html { scroll-behavior: smooth; }
  .landing-fade {
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.6s ease, transform 0.6s ease;
  }
  .landing-visible {
    opacity: 1;
    transform: translateY(0);
  }
  .typewriter-cursor {
    display: inline-block;
    margin-left: 2px;
    animation: blink 0.75s step-end infinite;
  }
  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }
`;

// --- Main Landing export ---
export function Landing() {
  return (
    <>
      <style>{landingStyles}</style>
      <Navbar />
      <main>
        <Hero />
        <Problem />
        <HowItWorks />
        <Features />
        <Strategy />
        <Platforms />
        <Stats />
        <FAQ />
        <FinalCTA />
      </main>
      <Footer />
    </>
  );
}
