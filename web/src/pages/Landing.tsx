import { AlertTriangle, BarChart2, Globe, Network, Percent, RefreshCw, ShieldCheck, Smartphone, TrendingDown, Zap } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import logo from "@/assets/logo.png";

const APP_URL = "https://auto-invest-web.vercel.app/app";

// --- Typewriter hook ---
const TYPEWRITER_OPTIONS = ["Effortlessly.", "Rationally.", "Stress-free.", "Automatically.", "Regularly."];

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
                    <img src={logo} alt="auto-invest" className="h-8 w-auto" />
                    <span className="font-semibold text-blue-900 text-sm">auto-invest</span>
                </a>

                {/* Desktop nav */}
                <div className="hidden md:flex items-center gap-8">
                    <a href="#how-it-works" className="text-sm text-slate-600 hover:text-blue-900 transition-colors">How it works</a>
                    <a href="#features" className="text-sm text-slate-600 hover:text-blue-900 transition-colors">Features</a>
                    <a href="#strategy" className="text-sm text-slate-600 hover:text-blue-900 transition-colors">Strategy</a>
                    <a href="#faq" className="text-sm text-slate-600 hover:text-blue-900 transition-colors">FAQ</a>
                </div>

                {/* CTA + mobile menu button */}
                <div className="flex items-center gap-3">
                    <a
                        href={APP_URL}
                        className="hidden sm:inline-flex text-sm text-slate-600 hover:text-blue-900 transition-colors font-medium"
                    >
                        Log in
                    </a>
                    <a
                        href={APP_URL}
                        className="hidden sm:inline-flex items-center gap-1 bg-blue-900 text-white text-sm font-medium px-4 py-2 rounded-md hover:bg-blue-800 transition-colors"
                    >
                        Start investing →
                    </a>
                    <button
                        className="md:hidden p-2 text-slate-600"
                        onClick={() => setMenuOpen(!menuOpen)}
                        aria-label="Menu"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            {menuOpen
                                ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                : <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                            }
                        </svg>
                    </button>
                </div>
            </div>

            {/* Mobile menu */}
            {menuOpen && (
                <div className="md:hidden border-t border-slate-200 bg-white px-4 py-4 flex flex-col gap-4">
                    <a href="#how-it-works" className="text-sm text-slate-600" onClick={() => setMenuOpen(false)}>How it works</a>
                    <a href="#features" className="text-sm text-slate-600" onClick={() => setMenuOpen(false)}>Features</a>
                    <a href="#strategy" className="text-sm text-slate-600" onClick={() => setMenuOpen(false)}>Strategy</a>
                    <a href="#faq" className="text-sm text-slate-600" onClick={() => setMenuOpen(false)}>FAQ</a>
                    <a href={APP_URL} className="text-sm text-slate-600">Log in</a>
                    <a href={APP_URL} className="inline-flex items-center gap-1 bg-blue-900 text-white text-sm font-medium px-4 py-2 rounded-md w-fit">
                        Start investing →
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
                        <Zap className="w-3 h-3" /> Automated investing
                    </div>
                    <h1 className="text-4xl md:text-5xl font-bold text-slate-900 leading-tight mb-4">
                        Start investing<br />
                        <span className="text-blue-900">{typedText}</span><span className="typewriter-cursor text-blue-900">|</span>
                    </h1>
                    <p className="text-slate-600 text-lg mb-8 leading-relaxed">
                        Connect your brokers, define your schedule, and auto-invest executes your strategy automatically — disciplined, consistent, and designed to take advantage of lower prices.
                    </p>
                    <div className="flex flex-col sm:flex-row gap-3 mb-8">
                        <a
                            href={APP_URL}
                            className="inline-flex items-center justify-center gap-1 bg-blue-900 text-white font-medium px-6 py-3 rounded-md hover:bg-blue-800 transition-colors text-sm"
                        >
                            Try for free →
                        </a>
                        <a
                            href="#how-it-works"
                            className="inline-flex items-center justify-center gap-1 border border-slate-300 text-slate-700 font-medium px-6 py-3 rounded-md hover:bg-slate-50 transition-colors text-sm"
                        >
                            How does it work?
                        </a>
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-500">
                        <span className="flex items-center gap-1.5"><RefreshCw className="w-3.5 h-3.5" /> Fully automatic</span>
                        <span className="text-slate-300">·</span>
                        <span className="flex items-center gap-1.5"><Network className="w-3.5 h-3.5" /> Multi-broker</span>
                        <span className="text-slate-300">·</span>
                        <span className="flex items-center gap-1.5"><Percent className="w-3.5 h-3.5" /> No fees</span>
                    </div>
                </div>

                {/* Right: dashboard mockup */}
                <div className="flex-1 flex justify-center lg:justify-end w-full max-w-md">
                    <div className="bg-white rounded-xl border border-slate-200 shadow-lg overflow-hidden w-full" style={{ borderTop: "3px solid #1e3a8a" }}>
                        <div className="px-5 pt-5 pb-4 border-b border-slate-100">
                            <p className="text-xs text-slate-500 mb-1">Next investment</p>
                            <p className="text-2xl font-bold text-slate-900">2 500 Kč</p>
                            <p className="text-xs text-slate-400 mt-1">scheduled for Friday</p>
                        </div>
                        <div className="px-5 py-4">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="text-xs text-slate-400 uppercase">
                                        <th className="text-left pb-2 font-medium">Instrument</th>
                                        <th className="text-right pb-2 font-medium">Amount</th>
                                        <th className="text-right pb-2 font-medium">Status</th>
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
                                <span className="text-xs text-slate-500">Automatically every Friday at 09:00</span>
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
        { icon: <AlertTriangle className="w-6 h-6 text-amber-500" />, title: "You forget", desc: "You want to invest every month, but on payday you forget or keep putting it off." },
        { icon: <TrendingDown className="w-6 h-6 text-red-500" />, title: "You invest emotionally", desc: "When markets fall, you're afraid to buy. When they rise, you regret not buying sooner." },
        { icon: <BarChart2 className="w-6 h-6 text-blue-500" />, title: "You don't know how to allocate", desc: "You don't know how much to put in ETF, how much in BTC, or when to add more to what's dropped." },
    ];

    return (
        <section id="problem" className="bg-slate-50">
            <div className="max-w-4xl mx-auto px-4 sm:px-6 py-16 md:py-20 text-center">
                <div ref={ref} className="landing-fade">
                    <p className="text-xs font-semibold tracking-widest text-blue-600 uppercase mb-3">Problem</p>
                    <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-12">
                        Investing manually? Nobody sticks with it long-term.
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
        { n: "1", title: "Connect your accounts", desc: "Enter your API keys from Trading212 and Coinmate. No password — just trading access." },
        { n: "2", title: "Set up your investment plan", desc: "Choose an amount and interval (daily, weekly, monthly). We'll take care of the rest." },
        { n: "3", title: "Watch your portfolio grow", desc: "Every purchase is visible in a clean dashboard. Stats, charts, history — all in one place." },
    ];

    return (
        <section id="how-it-works" className="bg-white">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 md:py-20 text-center">
                <div ref={ref} className="landing-fade">
                    <p className="text-xs font-semibold tracking-widest text-blue-600 uppercase mb-3">How it works</p>
                    <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-12">
                        Set it up once. Invest automatically.
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
        { icon: <Zap className="w-5 h-5 text-blue-600" />, title: "Automatic execution", desc: "Investments run exactly on your schedule, without any intervention on your part." },
        { icon: <TrendingDown className="w-5 h-5 text-blue-600" />, title: "Smart ATH-based allocation", desc: "More money where the price is below its all-time high. Take advantage of lower prices when others hesitate." },
        {
            icon: <Globe className="w-5 h-5 text-blue-600" />,
            title: "Multi-Broker",
            desc: "ETFs, stocks, and Bitcoin across multiple brokers — all executed under one strategy."
        },
        { icon: <BarChart2 className="w-5 h-5 text-blue-600" />, title: "Analytics dashboard", desc: "Investment charts over time, portfolio breakdown, order history — all clearly laid out." },
        {
            icon: <ShieldCheck className="w-5 h-5 text-blue-600" />,
            title: "Auto Self-Custody",
            desc: "BTC is automatically withdrawn to your hardware wallet once your balance exceeds your threshold."
        },
        { icon: <Smartphone className="w-5 h-5 text-blue-600" />, title: "PWA app", desc: "Add auto-invest to your phone's home screen as a native app." },
    ];

    return (
        <section id="features" className="bg-slate-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 md:py-20 text-center">
                <div ref={ref} className="landing-fade">
                    <p className="text-xs font-semibold tracking-widest text-blue-600 uppercase mb-3">Features</p>
                    <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-12">
                        Everything you need for automated investing
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
        { name: "BTC", drop: "-48%", mult: "1.7×", alloc: "45%", color: "text-red-500", bg: "bg-red-50" },
    ];

    return (
        <section id="strategy" className="bg-white">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 md:py-20">
                <div ref={ref} className="landing-fade grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                    {/* Text */}
                    <div>
                        <p className="text-xs font-semibold tracking-widest text-blue-600 uppercase mb-3">Strategy</p>
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-6">
                            Buy more when prices are down
                        </h2>
                        <div className="space-y-4 text-slate-600 leading-relaxed">
                            <p>Most people buy less when markets fall — out of fear. Auto-invest does the opposite.</p>

                            <p>For each instrument in the portfolio, we track how far its price is from its all-time high (ATH). The larger the drop, the higher the weight on the next purchase.</p>

                            <p className="border-l-[3px] border-blue-600 pl-3 text-slate-700 font-medium">
                                You always invest{" "}
                                <span className="italic font-semibold text-blue-600">exactly</span>
                                {" "}the total amount you configured.
                            </p>

                            <p>The system simply redistributes that amount — allocating more to assets that are cheaper and less to those near their highs.</p>
                        </div>
                    </div>

                    {/* Table */}
                    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                        <div className="px-5 py-4 border-b border-slate-100 bg-slate-50">
                            <p className="text-sm font-semibold text-slate-700">Allocation by drop from ATH</p>
                        </div>
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-xs text-slate-400 uppercase border-b border-slate-100">
                                    <th className="text-left px-5 py-3 font-medium">Instrument</th>
                                    <th className="text-right px-5 py-3 font-medium">Drop from ATH</th>
                                    <th className="text-right px-5 py-3 font-medium">Multiplier</th>
                                    <th className="text-right px-5 py-3 font-medium">Allocation</th>
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
                            <p className="text-xs text-slate-400">* Larger drop = higher weight at purchase</p>
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
                    <h2 className="text-lg font-semibold text-slate-700 mb-8">Works with these platforms</h2>
                    <div className="flex flex-col sm:flex-row gap-5 justify-center">
                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex-1 max-w-xs mx-auto sm:mx-0">
                            <img src="/trading212-logo.jpg" alt="Trading212" className="h-8 w-auto mx-auto block object-contain mb-3" />
                            <p className="text-sm text-slate-500">ETFs & stocks</p>
                            <p className="text-xs text-slate-400 mt-2">Very low fees, EU-regulated</p>
                        </div>
                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex-1 max-w-xs mx-auto sm:mx-0">
                            <img src="/coinmate-logo.jpg" alt="Coinmate" className="h-8 w-auto mx-auto block object-contain mb-3" />
                            <p className="text-sm text-slate-500">Bitcoin</p>
                            <p className="text-xs text-slate-400 mt-2">Czech-based, excellent customer support</p>
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
        { value: "10+", label: "portfolio instruments" },
        { value: "2", label: "supported brokers" },
        { value: "100%", label: "automatic" },
        { value: "0 Kč", label: "fees" },
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
            q: "Is auto-invest secure?",
            a: "Auto-invest connects to platforms using API keys to execute trades on your behalf. Your funds always remain on your broker's account — auto-invest never holds custody of your assets. For Bitcoin, the system can optionally withdraw funds to your preconfigured hardware wallet once a balance threshold is reached.",
        },
        {
            q: "How much does it cost?",
            a: "Auto-invest is funded through a subscription model. The basic plan costs €4.99 per month. We do not receive any commissions from brokers or exchanges. You can try the service with a 30-day free trial."
        },
        {
            q: "Is my money held by auto-invest?",
            a: "No. auto-invest never holds funds. All assets remain on your broker or exchange accounts. The software only sends trading instructions through official APIs.",
        },
        {
            q: "Why not just use the platform’s built-in recurring investment?",
            a: "Auto-invest coordinates multiple platforms and asset classes under one strategy and applies the same logic across all of them — removing the need to manually manage investments across different platforms.",
        },
        {
            q: "Can I change my strategy later?",
            a: "Yes. You can modify asset weights, schedules, or the total amount at any time. The new configuration will be applied during the next execution cycle.",
        },
        {
            q: "How often does it invest?",
            a: "You choose the schedule. The most frequent option is: Everyday"
        }
    ];

    return (
        <section id="faq" className="bg-slate-50">
            <div className="max-w-2xl mx-auto px-4 sm:px-6 py-16 md:py-20">
                <div ref={ref} className="landing-fade text-center mb-10">
                    <p className="text-xs font-semibold tracking-widest text-blue-600 uppercase mb-3">FAQ</p>
                    <h2 className="text-3xl md:text-4xl font-bold text-slate-900">Got questions? We've got answers.</h2>
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
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
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
                        Start investing automatically today.
                    </h2>
                    <p className="text-blue-200 mb-8 text-lg">
                        Create an account with a 30-day free trial.
                    </p>
                    <a
                        href={APP_URL}
                        className="inline-flex items-center gap-1 bg-white text-blue-900 font-semibold px-8 py-3.5 rounded-md hover:bg-blue-50 transition-colors text-sm"
                    >
                        Start your free trial →
                    </a>
                    <p className="text-blue-300 text-xs mt-4">
                        30-day free trial · Cancel anytime
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
            <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 flex items-center justify-center text-sm text-slate-500">
                <span>auto-invest © {new Date().getFullYear()}</span>
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
