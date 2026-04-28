"use client";

/**
 * Leaders tab — read-only listing of the 4 SchoolLeader rows.
 *
 * Sprint 19 ships this as read-only. Inline CRUD (add/edit/delete
 * leaders) is on the backlog — needs new permission-scoped endpoints
 * + serializers in community/leaders/. For now, school admins
 * contact us by email to update.
 */

import { useTranslations } from "next-intl";
import { SchoolLeaderData } from "@/lib/types";

interface LeadersTabProps {
  leaders: SchoolLeaderData[];
}

export default function LeadersTab({ leaders }: LeadersTabProps) {
  const t = useTranslations("schoolEdit");

  return (
    <div className="space-y-4">
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
        {t("leadersComingSoon")}
      </div>

      {leaders.length === 0 ? (
        <p className="text-sm text-gray-500 italic py-4">{t("noLeadersYet")}</p>
      ) : (
        <div className="divide-y divide-gray-100 border border-gray-200 rounded-lg bg-white">
          {leaders.map((leader, idx) => (
            <div key={`${leader.role}-${idx}`} className="px-4 py-3 flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wider text-gray-500 font-semibold">
                  {leader.role_display}
                </p>
                <p className="text-sm text-gray-900 mt-0.5">{leader.name}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
