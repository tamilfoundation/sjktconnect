"use client";

/**
 * School edit form — tabbed layout (Sprint 19, 2026-04-28).
 *
 * Five tabs: Core / Contact / Leaders / Support / Images. Tab id is
 * persisted in the URL hash so deep-links work and browser back
 * navigates between tabs.
 *
 * The Confirm Data flow was removed — MOE data is the source of
 * truth, nothing for school admins to confirm. See decisions.md
 * Sprint 19 entry.
 */

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { SchoolEditData } from "@/lib/types";
import { updateSchool } from "@/lib/api";
import TabBar from "@/components/edit_tabs/TabBar";
import CoreTab from "@/components/edit_tabs/CoreTab";
import ContactTab from "@/components/edit_tabs/ContactTab";
import LeadersTab from "@/components/edit_tabs/LeadersTab";
import SupportTab from "@/components/edit_tabs/SupportTab";
import ImagesTab from "@/components/edit_tabs/ImagesTab";

interface SchoolEditFormProps {
  school: SchoolEditData;
  isSuperAdmin: boolean;
}

// Fields that can be PATCH'd to /schools/<moe>/edit/. Anything not
// in this set is read-only (MOE source) and excluded from the diff.
const WRITABLE_FIELDS: (keyof SchoolEditData)[] = [
  "name_tamil",
  "address",
  "postcode",
  "city",
  "email",
  "phone",
  "fax",
  "enrolment",
  "preschool_enrolment",
  "special_enrolment",
  "teacher_count",
  "session_count",
  "session_type",
  "bank_name",
  "bank_account_name",
  "bank_account_number",
  // GPS only writable when isSuperAdmin (filter applied at save time).
  "gps_lat",
  "gps_lng",
];

const TAB_IDS = ["core", "contact", "leaders", "support", "images"] as const;
type TabId = (typeof TAB_IDS)[number];

export default function SchoolEditForm({ school, isSuperAdmin }: SchoolEditFormProps) {
  const t = useTranslations("schoolEdit");
  const tc = useTranslations("common");

  const [formData, setFormData] = useState<SchoolEditData>(school);
  const [activeTab, setActiveTab] = useState<TabId>("core");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  // Sync tab to URL hash so deep-links + browser back work.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const hash = window.location.hash.replace("#", "");
    if ((TAB_IDS as readonly string[]).includes(hash)) {
      setActiveTab(hash as TabId);
    }
    const onHashChange = () => {
      const next = window.location.hash.replace("#", "");
      if ((TAB_IDS as readonly string[]).includes(next)) {
        setActiveTab(next as TabId);
      }
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  function selectTab(id: string) {
    setActiveTab(id as TabId);
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", `#${id}`);
    }
  }

  function handleChange(key: keyof SchoolEditData, value: string | number) {
    setFormData((prev) => ({ ...prev, [key]: value }));
  }

  const tabs = useMemo(
    () => [
      { id: "core", label: t("tabCore") },
      { id: "contact", label: t("tabContact") },
      { id: "leaders", label: t("tabLeaders") },
      { id: "support", label: t("tabSupport") },
      { id: "images", label: t("tabImages") },
    ],
    [t]
  );

  // Leaders + Images don't have a Save button; the rest do.
  const tabHasSave = activeTab === "core" || activeTab === "contact" || activeTab === "support";

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");

    const updates: Record<string, unknown> = {};
    for (const key of WRITABLE_FIELDS) {
      // GPS is admin-gated even on the writable list.
      if ((key === "gps_lat" || key === "gps_lng") && !isSuperAdmin) continue;
      if (formData[key] !== school[key]) {
        updates[key] = formData[key];
      }
    }

    if (Object.keys(updates).length === 0) {
      setError(t("noChanges"));
      setSaving(false);
      return;
    }

    try {
      const result = await updateSchool(school.moe_code, updates);
      setSuccess(t("changesSaved"));
      setFormData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("failedSave"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <TabBar tabs={tabs} active={activeTab} onChange={selectTab} />

      {(success || error) && (
        <div
          className={
            success
              ? "bg-green-50 border border-green-200 text-green-800 rounded-lg p-3 mb-4 text-sm"
              : "bg-red-50 border border-red-200 text-red-800 rounded-lg p-3 mb-4 text-sm"
          }
        >
          {success || error}
        </div>
      )}

      <form onSubmit={handleSave}>
        <div role="tabpanel">
          {activeTab === "core" && <CoreTab data={formData} onChange={handleChange} />}
          {activeTab === "contact" && (
            <ContactTab data={formData} isSuperAdmin={isSuperAdmin} onChange={handleChange} />
          )}
          {activeTab === "leaders" && (
            <LeadersTab
              moeCode={formData.moe_code}
              initialLeaders={formData.leaders}
              onLeadersChange={(leaders) => setFormData((prev) => ({ ...prev, leaders }))}
            />
          )}
          {activeTab === "support" && <SupportTab data={formData} onChange={handleChange} />}
          {activeTab === "images" && <ImagesTab moeCode={formData.moe_code} />}
        </div>

        {tabHasSave && (
          <div className="mt-8 pt-6 border-t border-gray-200 flex items-center justify-end gap-3">
            <Link
              href={`/school/${school.moe_code}`}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              {tc("cancel")}
            </Link>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? t("saving") : t("saveChanges")}
            </button>
          </div>
        )}
      </form>
    </div>
  );
}
