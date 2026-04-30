"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { Wind, BarChart2, Activity, Brain, Menu, X, LogOut, User, History } from "lucide-react";
import { isLoggedIn, removeToken, decodeToken } from "@/lib/auth";

const NAV = [
  { href: "/",         label: "Dashboard", icon: BarChart2 },
  { href: "/optimize", label: "Optimize",  icon: Brain },
  { href: "/simulate", label: "Simulate",  icon: Activity },
  { href: "/predict",  label: "Predict",   icon: Wind },
];

export default function Navbar() {
  const pathname = usePathname();
  const router   = useRouter();
  const [open,    setOpen]    = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [email,   setEmail]   = useState("");

  useEffect(() => {
    setLoggedIn(isLoggedIn());
    const d = decodeToken();
    if (d) setEmail(d.email);
  }, [pathname]);

  const logout = () => {
    removeToken();
    document.cookie = "aqi_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    setLoggedIn(false);
    router.push("/login");
  };

  return (
    <nav className="sticky top-0 z-50 glass border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-teal/20 flex items-center justify-center group-hover:bg-teal/30 transition-colors">
              <Wind className="w-5 h-5 text-teal" />
            </div>
            <span className="font-bold text-white hidden sm:block">
              AQI <span className="text-teal">Optimizer</span>
            </span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {NAV.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                  ${pathname === href
                    ? "bg-teal/15 text-teal"
                    : "text-slate hover:text-white hover:bg-white/5"
                  }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}
          </div>

          {/* Auth */}
          <div className="hidden md:flex items-center gap-2">
            {loggedIn ? (
              <>
                <Link href="/history" className="flex items-center gap-1 text-slate hover:text-teal text-sm px-3 py-2 rounded-lg hover:bg-white/5 transition-all">
                  <History className="w-4 h-4" /> History
                </Link>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5">
                  <User className="w-4 h-4 text-teal" />
                  <span className="text-xs text-slate max-w-[120px] truncate">{email}</span>
                </div>
                <button onClick={logout} className="flex items-center gap-1 text-danger/80 hover:text-danger text-sm px-3 py-2 rounded-lg hover:bg-danger/10 transition-all">
                  <LogOut className="w-4 h-4" /> Logout
                </button>
              </>
            ) : (
              <Link href="/login" className="btn-primary text-sm">Login</Link>
            )}
          </div>

          {/* Mobile hamburger */}
          <button className="md:hidden p-2 rounded-lg hover:bg-white/5" onClick={() => setOpen(!open)}>
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Mobile menu */}
        {open && (
          <div className="md:hidden py-3 border-t border-white/5 animate-fade-in">
            {NAV.map(({ href, label, icon: Icon }) => (
              <Link key={href} href={href} onClick={() => setOpen(false)}
                className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm ${pathname === href ? "text-teal bg-teal/10" : "text-slate hover:text-white"}`}>
                <Icon className="w-4 h-4" />{label}
              </Link>
            ))}
            <div className="border-t border-white/5 mt-2 pt-2">
              {loggedIn ? (
                <button onClick={logout} className="w-full text-left px-4 py-3 text-danger text-sm flex items-center gap-2">
                  <LogOut className="w-4 h-4" /> Logout
                </button>
              ) : (
                <Link href="/login" onClick={() => setOpen(false)} className="block px-4 py-3 text-teal text-sm">Login / Register</Link>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
