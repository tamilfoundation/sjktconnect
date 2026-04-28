"use client";

/**
 * Pill-button tab navigator for the school edit page. Active tab is
 * a filled blue pill; inactive tabs are ghost buttons. Tab id is
 * stored in the URL hash so deep-links and browser back work.
 */

interface Tab {
  id: string;
  label: string;
}

interface TabBarProps {
  tabs: Tab[];
  active: string;
  onChange: (id: string) => void;
}

export default function TabBar({ tabs, active, onChange }: TabBarProps) {
  return (
    <nav
      role="tablist"
      aria-label="School data sections"
      className="flex flex-wrap gap-2 mb-6 p-1 bg-gray-50 rounded-full border border-gray-200 w-fit"
    >
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={
              isActive
                ? "px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-full shadow-sm"
                : "px-5 py-2 text-gray-600 text-sm font-medium rounded-full hover:bg-white hover:text-gray-900 transition-colors"
            }
          >
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
}
