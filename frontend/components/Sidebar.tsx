"use client";

import React from "react";
import { X } from "lucide-react";

interface SidebarProps {
  path: string;
  setPath: (path: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ path, setPath, isOpen, onClose }: SidebarProps) {
  const navItem = (href: string, label: string) => {
    const isActive = path === href;
    return (
      <button
        key={href}
        type="button"
        onClick={() => {
          setPath(href);
          onClose(); // Automatically close drawer upon selecting an item
        }}
        style={{
          color: isActive ? "#1e40af" : "#ffffff",
          backgroundColor: isActive ? "#ffffff" : "transparent",
        }}
        className={`w-full flex items-center gap-3 px-3.5 py-2.5 my-1 text-sm rounded-lg transition-colors font-semibold text-left cursor-pointer focus:outline-none ${
          isActive
            ? "bg-white !text-[#1e40af] font-bold shadow-md"
            : "!text-white hover:bg-white/15"
        }`}
      >
        <span style={{ color: isActive ? "#1e40af" : "#ffffff" }}>{label}</span>
      </button>
    );
  };

  return (
    <>
      {/* Dark semi-transparent backdrop overlay */}
      {isOpen && (
        <div
          className="bg-black/50 fixed inset-0 z-40 transition-opacity duration-300"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Collapsible Drawer Sidebar */}
      <aside
        className={`fixed top-0 left-0 h-screen w-64 z-50 transform transition-transform duration-300 ease-in-out flex flex-col bg-[#1e40af] border-r border-blue-900/50 shadow-2xl overflow-y-auto ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Supervisory navigation drawer"
      >
        {/* Drawer Header with Close Icon */}
        <div className="p-4 border-b border-white/15 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-white/20 border border-white/30 flex items-center justify-center text-white font-bold text-sm shadow-xs">
              SA
            </div>
            <span className="text-white font-bold text-base tracking-tight">SAT-SA</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-white hover:bg-white/15 transition-colors focus:outline-none focus:ring-2 focus:ring-white/40 cursor-pointer"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>

        {/* Navigation Categories & Links */}
        <nav className="p-3 flex-1" aria-label="Primary navigation">
          {/* Section: Analytics */}
          <div className="pt-3 pb-2 px-2.5 flex items-center gap-2">
            <span className="w-1.5 h-4 bg-white/80 rounded-full inline-block" />
            <span
              style={{ color: "#ffffff" }}
              className="text-white text-[15px] font-extrabold tracking-wide uppercase"
            >
              Analytics
            </span>
          </div>
          {navItem("/", "Dashboard Overview")}
          {navItem("/data-ingestion", "Data Ingestion")}

          <div className="h-px bg-white/20 my-3 mx-2" />

          {/* Section: Supervisory Views */}
          <div className="pt-2 pb-2 px-2.5 flex items-center gap-2">
            <span className="w-1.5 h-4 bg-white/80 rounded-full inline-block" />
            <span
              style={{ color: "#ffffff" }}
              className="text-white text-[15px] font-extrabold tracking-wide uppercase"
            >
              Supervisory Views
            </span>
          </div>
          {navItem("/execution-gaps", "Execution Gaps")}
          {navItem("/negative-space", "Negative Space")}
          {navItem("/peer-comparison", "Peer Comparison")}

          <div className="h-px bg-white/20 my-3 mx-2" />

          {/* Section: Records */}
          <div className="pt-2 pb-2 px-2.5 flex items-center gap-2">
            <span className="w-1.5 h-4 bg-white/80 rounded-full inline-block" />
            <span
              style={{ color: "#ffffff" }}
              className="text-white text-[15px] font-extrabold tracking-wide uppercase"
            >
              Records
            </span>
          </div>
          {navItem("/audit-reports", "Audit Reports")}
        </nav>
      </aside>
    </>
  );
}

export default Sidebar;
