"use client";

/**
 * Contact tab — address + phones + email + GPS coordinates.
 *
 * GPS lat/lng are gated to SUPERADMIN. School admins see them as
 * read-only with a "verified by Google Places" badge so they don't
 * accidentally override the Sprint 5.4 batch verification.
 */

import { useTranslations } from "next-intl";
import { SchoolEditData } from "@/lib/types";
import {
  PHONE_PATTERN_HTML,
  emailError,
  phoneError,
} from "@/lib/validation";
import { ReadOnlyField, EditableField } from "./FieldRow";

interface ContactTabProps {
  data: SchoolEditData;
  isSuperAdmin: boolean;
  onChange: (key: keyof SchoolEditData, value: string | number) => void;
}

export default function ContactTab({ data, isSuperAdmin, onChange }: ContactTabProps) {
  const t = useTranslations("schoolEdit");

  return (
    <div className="space-y-8">
      <section>
        <p className="text-xs uppercase tracking-wider text-blue-700 font-semibold mb-3">
          {t("editableDetails")}
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <EditableField
            label={t("address")}
            value={data.address}
            onChange={(v) => onChange("address", v)}
            fullWidth
          />
          <EditableField
            label={t("postcode")}
            value={data.postcode}
            onChange={(v) => onChange("postcode", v)}
          />
          <EditableField
            label={t("city")}
            value={data.city}
            onChange={(v) => onChange("city", v)}
          />
          <EditableField
            label={t("email")}
            value={data.email}
            onChange={(v) => onChange("email", v)}
            type="email"
            error={emailError(String(data.email ?? ""), t)}
          />
          <EditableField
            label={t("phone")}
            value={data.phone}
            onChange={(v) => onChange("phone", v)}
            type="tel"
            pattern={PHONE_PATTERN_HTML}
            patternTitle={t("validationPhone")}
            placeholder="04-966 3429"
            error={phoneError(String(data.phone ?? ""), t)}
          />
          <EditableField
            label={t("fax")}
            value={data.fax}
            onChange={(v) => onChange("fax", v)}
            type="tel"
            pattern={PHONE_PATTERN_HTML}
            patternTitle={t("validationPhone")}
            placeholder="04-966 3430"
            error={phoneError(String(data.fax ?? ""), t)}
          />
        </div>
      </section>

      <section>
        <p className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3">
          GPS
          {!isSuperAdmin && (
            <span className="ml-2 text-gray-400 font-normal normal-case">
              · {t("gpsAdminOnly")}
            </span>
          )}
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {isSuperAdmin ? (
            <>
              {/* Sprint 28 follow-up: round to 7 dp before sending to
                  match the DecimalField(max_digits=10, decimal_places=7)
                  schema. 7 dp ≈ 1cm precision — plenty for a school
                  location. Without rounding, a pasted Google Maps value
                  (15+ JS-double digits) gets a 400 from DRF. */}
              <EditableField
                label={t("gpsLat")}
                value={data.gps_lat ?? ""}
                onChange={(v) =>
                  onChange(
                    "gps_lat",
                    v === "" ? 0 : Number(Number(v).toFixed(7)),
                  )
                }
                type="number"
              />
              <EditableField
                label={t("gpsLng")}
                value={data.gps_lng ?? ""}
                onChange={(v) =>
                  onChange(
                    "gps_lng",
                    v === "" ? 0 : Number(Number(v).toFixed(7)),
                  )
                }
                type="number"
              />
            </>
          ) : (
            <>
              <ReadOnlyField label={t("gpsLat")} value={data.gps_lat} />
              <ReadOnlyField
                label={t("gpsLng")}
                value={data.gps_lng}
                badge={
                  data.gps_verified ? (
                    <span
                      title={t("gpsVerified")}
                      className="inline-flex items-center px-2 py-0.5 text-xs font-semibold bg-green-100 text-green-800 rounded"
                    >
                      ✓
                    </span>
                  ) : null
                }
              />
            </>
          )}
        </div>
      </section>
    </div>
  );
}
