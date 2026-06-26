"use client";

/**
 * Leaders tab — inline CRUD for the 4 fixed SchoolLeader roles
 * (Sprint 20).
 *
 * Pattern: each of the 4 roles is a "slot." If a leader exists for
 * that slot, render an inline editor (name + phone + email + Remove).
 * If not, render a "+ Add {Role}" button that swaps in an empty
 * editor in the same spot.
 *
 * Save model: a single "Save changes" button at the tab footer
 * (consistent with Core/Contact/Support tabs). All accumulated
 * creates / updates / deletes flush in parallel on save. Local
 * state is the source of truth between renders.
 *
 * Phone + email are private (visible only to school admins) —
 * SchoolEditSerializer.get_leaders returns the admin shape, gated
 * by IsProfileAuthenticated + the page-level role check.
 */

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations, useLocale } from "next-intl";
import { SchoolLeaderAdminData } from "@/lib/types";
import {
  createSchoolLeader,
  updateSchoolLeader,
  deleteSchoolLeader,
  revalidateSchoolPage,
  LeaderRole,
} from "@/lib/api";
import {
  PHONE_PATTERN_HTML,
  emailError,
  isValidEmail,
  isValidPhone,
  phoneError,
} from "@/lib/validation";

const ROLE_ORDER: LeaderRole[] = [
  "board_chair",
  "headmaster",
  "pta_chair",
  "alumni_chair",
];

const ROLE_LABEL_KEY: Record<LeaderRole, string> = {
  board_chair: "roleBoardChair",
  headmaster: "roleHeadmaster",
  pta_chair: "rolePtaChair",
  alumni_chair: "roleAlumniChair",
};

interface SlotState {
  /** Persisted server-side id, present for existing leaders only. */
  id?: number;
  name: string;
  phone: string;
  email: string;
  /** True when the user explicitly clicked Remove on an existing slot. */
  removed: boolean;
  /** True when the slot was empty in the initial load and the user clicked + Add. */
  freshlyAdded: boolean;
}

interface LeadersTabProps {
  moeCode: string;
  initialLeaders: SchoolLeaderAdminData[];
  /** Lifts the latest leaders array up to the parent so the form's formData stays in sync. */
  onLeadersChange?: (leaders: SchoolLeaderAdminData[]) => void;
  /**
   * Sprint 28: the canonical school slug (e.g.
   * `kg-simee-ipoh-abd2166`) — passed by the parent SchoolEditForm
   * so revalidate-after-save invalidates the LITERAL slug URL the
   * user is about to navigate to. The dynamic-segment form of
   * revalidatePath doesn't work in our Next 16 setup.
   */
  slug?: string;
}

export default function LeadersTab({
  moeCode,
  initialLeaders,
  onLeadersChange,
  slug,
}: LeadersTabProps) {
  const t = useTranslations("schoolEdit");
  const router = useRouter();
  const locale = useLocale();

  // Bootstrap one slot per role from the server-shape leaders array.
  const [slots, setSlots] = useState<Record<LeaderRole, SlotState | null>>(
    () => buildSlotsFromLeaders(initialLeaders)
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Re-bootstrap if the parent reloads (e.g. after a Save round-trip
  // bumps the leaders list with new ids).
  useEffect(() => {
    setSlots(buildSlotsFromLeaders(initialLeaders));
  }, [initialLeaders]);

  function patchSlot(role: LeaderRole, patch: Partial<SlotState>) {
    setSlots((prev) => {
      const current = prev[role];
      if (!current) return prev;
      return { ...prev, [role]: { ...current, ...patch } };
    });
  }

  function addSlot(role: LeaderRole) {
    setSlots((prev) => ({
      ...prev,
      [role]: {
        name: "",
        phone: "",
        email: "",
        removed: false,
        freshlyAdded: true,
      },
    }));
  }

  function removeSlot(role: LeaderRole) {
    setSlots((prev) => {
      const current = prev[role];
      if (!current) return prev;
      // Existing leader: mark removed (we delete on save).
      // Freshly-added empty row: just discard (no DB row to delete).
      if (current.id) {
        return { ...prev, [role]: { ...current, removed: true } };
      }
      return { ...prev, [role]: null };
    });
  }

  // Compute the "diff" against initial state to know what to flush.
  const pendingChanges = useMemo(
    () => computePendingChanges(initialLeaders, slots),
    [initialLeaders, slots]
  );

  const hasChanges = pendingChanges.length > 0;

  async function handleSave() {
    if (!hasChanges) {
      setError(t("noChanges"));
      setSuccess("");
      return;
    }
    // Sprint 26 bug #1: refuse to save if any pending slot has an
    // invalid phone or email. Inline errors already render on the
    // individual rows, but a final guard prevents an unsaved-row
    // submit from reaching the API.
    for (const role of ROLE_ORDER) {
      const slot = slots[role];
      if (!slot || slot.removed) continue;
      if (!isValidPhone(slot.phone) || !isValidEmail(slot.email)) {
        setError(t("validationFixBeforeSave"));
        setSuccess("");
        return;
      }
    }
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      // Sequential is simpler than parallel and stays correct under the
      // unique-active-role constraint (deletes must commit before
      // re-creates of the same role).
      const updated: SchoolLeaderAdminData[] = [];
      // Carry over unchanged existing leaders.
      const initialById = new Map(initialLeaders.map((l) => [l.id, l]));
      const touched = new Set<number>();

      for (const change of pendingChanges) {
        if (change.kind === "delete" && change.id) {
          await deleteSchoolLeader(moeCode, change.id);
          touched.add(change.id);
        } else if (change.kind === "create") {
          const created = await createSchoolLeader(moeCode, change.role, {
            name: change.name,
            phone: change.phone,
            email: change.email,
          });
          updated.push(created);
        } else if (change.kind === "update" && change.id) {
          const next = await updateSchoolLeader(moeCode, change.id, {
            name: change.name,
            phone: change.phone,
            email: change.email,
          });
          updated.push(next);
          touched.add(change.id);
        }
      }

      // Carry over leaders that weren't touched.
      for (const leader of initialById.values()) {
        if (!touched.has(leader.id)) {
          updated.push(leader);
        }
      }

      const sorted = updated.sort((a, b) => a.role.localeCompare(b.role));
      setSuccess(t("leadersSaved"));
      onLeadersChange?.(sorted);
      // Sprint 27 #4: same ISR cache invalidation as Core/Contact
      // tabs. The public school page caches the leaders list for up
      // to 24h; without this call a freshly-added Board Chairman
      // wouldn't reach the School Leadership card until tomorrow.
      try {
        await revalidateSchoolPage(moeCode, slug);
      } catch {
        // Best-effort — see SchoolEditForm comment.
      }
      router.refresh();
      // Navigate to slug if known (parent passed it), else bare-code
      // (which will 301 to slug — extra hop but still correct).
      router.push(
        slug
          ? `/${locale}/school/${slug}`
          : `/${locale}/school/${moeCode}`,
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : t("leadersFailedSave");
      // Translate the backend's slot-taken code into the locale string.
      setError(msg.includes("role_taken") || msg.toLowerCase().includes("already")
        ? t("leadersSlotTaken")
        : msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-600">{t("leadersIntro")}</p>

      {success && (
        <div className="bg-green-50 border border-green-200 text-green-800 rounded-lg p-3 text-sm">
          {success}
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-3 text-sm">
          {error}
        </div>
      )}

      <div className="space-y-4">
        {ROLE_ORDER.map((role) => {
          const slot = slots[role];
          const roleLabel = t(ROLE_LABEL_KEY[role]);
          if (!slot || slot.removed) {
            return (
              <div
                key={role}
                className="border border-dashed border-gray-300 rounded-lg p-4 text-center bg-gray-50"
              >
                <button
                  type="button"
                  onClick={() => {
                    // If marked-removed, restore to empty editable state.
                    if (slot?.removed) {
                      patchSlot(role, { removed: false, name: "", phone: "", email: "" });
                    } else {
                      addSlot(role);
                    }
                  }}
                  className="text-sm font-medium text-blue-600 hover:text-blue-700"
                >
                  {t("addLeader", { role: roleLabel })}
                </button>
              </div>
            );
          }
          return (
            <LeaderRow
              key={role}
              role={role}
              roleLabel={roleLabel}
              slot={slot}
              onChange={(patch) => patchSlot(role, patch)}
              onRemove={() => removeSlot(role)}
            />
          );
        })}
      </div>

      <div className="pt-4 border-t border-gray-200 flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !hasChanges}
          className="px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? t("leadersSaving") : t("saveChanges")}
        </button>
      </div>
    </div>
  );
}

// --- Helpers ---

function buildSlotsFromLeaders(
  leaders: SchoolLeaderAdminData[]
): Record<LeaderRole, SlotState | null> {
  const out: Record<LeaderRole, SlotState | null> = {
    board_chair: null,
    headmaster: null,
    pta_chair: null,
    alumni_chair: null,
  };
  for (const leader of leaders) {
    if (leader.role in out) {
      out[leader.role as LeaderRole] = {
        id: leader.id,
        name: leader.name,
        phone: leader.phone || "",
        email: leader.email || "",
        removed: false,
        freshlyAdded: false,
      };
    }
  }
  return out;
}

type PendingChange =
  | { kind: "create"; role: LeaderRole; name: string; phone: string; email: string }
  | { kind: "update"; id: number; role: LeaderRole; name: string; phone: string; email: string }
  | { kind: "delete"; id: number; role: LeaderRole };

function computePendingChanges(
  initial: SchoolLeaderAdminData[],
  slots: Record<LeaderRole, SlotState | null>
): PendingChange[] {
  const changes: PendingChange[] = [];
  const byRole = new Map(initial.map((l) => [l.role as LeaderRole, l]));

  for (const role of ROLE_ORDER) {
    const slot = slots[role];
    const existing = byRole.get(role);

    if (!slot) {
      // No slot: nothing to do (it was empty initially OR we discarded a freshly-added empty row).
      continue;
    }

    if (slot.removed && existing) {
      changes.push({ kind: "delete", id: existing.id, role });
      continue;
    }

    if (!existing && !slot.removed) {
      // Skip empty new slots — user clicked Add but didn't enter a name.
      if (!slot.name.trim()) continue;
      changes.push({
        kind: "create",
        role,
        name: slot.name.trim(),
        phone: slot.phone.trim(),
        email: slot.email.trim(),
      });
      continue;
    }

    if (existing && !slot.removed) {
      const same =
        existing.name === slot.name &&
        (existing.phone || "") === slot.phone &&
        (existing.email || "") === slot.email;
      if (!same) {
        // If the user blanked the name on an existing leader, treat it as a delete.
        if (!slot.name.trim()) {
          changes.push({ kind: "delete", id: existing.id, role });
        } else {
          changes.push({
            kind: "update",
            id: existing.id,
            role,
            name: slot.name.trim(),
            phone: slot.phone.trim(),
            email: slot.email.trim(),
          });
        }
      }
    }
  }

  return changes;
}

interface LeaderRowProps {
  role: LeaderRole;
  roleLabel: string;
  slot: SlotState;
  onChange: (patch: Partial<SlotState>) => void;
  onRemove: () => void;
}

function LeaderRow({ role, roleLabel, slot, onChange, onRemove }: LeaderRowProps) {
  const t = useTranslations("schoolEdit");
  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-wider font-semibold text-blue-700">
          {roleLabel}
        </p>
        <button
          type="button"
          onClick={() => {
            if (slot.id && !window.confirm(t("leaderRemoveConfirm"))) return;
            onRemove();
          }}
          className="text-xs text-red-600 hover:text-red-700 font-medium"
        >
          {t("leaderRemove")}
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div>
          <label htmlFor={`leader-${role}-name`} className="block text-xs text-gray-600 mb-1">
            {t("leaderName")}
          </label>
          <input
            id={`leader-${role}-name`}
            type="text"
            value={slot.name}
            onChange={(e) => onChange({ name: e.target.value })}
            className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div>
          <label htmlFor={`leader-${role}-phone`} className="block text-xs text-gray-600 mb-1">
            {t("leaderPhone")}
          </label>
          <input
            id={`leader-${role}-phone`}
            type="tel"
            value={slot.phone}
            placeholder="04-966 3429"
            pattern={PHONE_PATTERN_HTML}
            title={t("validationPhone")}
            aria-invalid={phoneError(slot.phone, t) ? true : undefined}
            onChange={(e) => onChange({ phone: e.target.value })}
            className={`w-full px-3 py-2 bg-white border rounded-lg text-sm focus:ring-2 ${
              phoneError(slot.phone, t)
                ? "border-red-400 focus:ring-red-500 focus:border-red-500"
                : "border-gray-300 focus:ring-blue-500 focus:border-blue-500"
            }`}
          />
          {phoneError(slot.phone, t) && (
            <p className="mt-1 text-xs text-red-600">{phoneError(slot.phone, t)}</p>
          )}
        </div>
        <div>
          <label htmlFor={`leader-${role}-email`} className="block text-xs text-gray-600 mb-1">
            {t("leaderEmail")}
          </label>
          <input
            id={`leader-${role}-email`}
            type="email"
            value={slot.email}
            aria-invalid={emailError(slot.email, t) ? true : undefined}
            onChange={(e) => onChange({ email: e.target.value })}
            className={`w-full px-3 py-2 bg-white border rounded-lg text-sm focus:ring-2 ${
              emailError(slot.email, t)
                ? "border-red-400 focus:ring-red-500 focus:border-red-500"
                : "border-gray-300 focus:ring-blue-500 focus:border-blue-500"
            }`}
          />
          {emailError(slot.email, t) && (
            <p className="mt-1 text-xs text-red-600">{emailError(slot.email, t)}</p>
          )}
        </div>
      </div>
    </div>
  );
}
