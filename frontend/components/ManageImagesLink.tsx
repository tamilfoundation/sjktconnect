"use client";

import { useEffect, useState } from "react";
import { Link } from "@/i18n/navigation";
import { fetchMe } from "@/lib/api";

interface ManageImagesLinkProps {
  moeCode: string;
}

/**
 * Renders a "Manage images" button for SUPERADMIN or this school's bound admin.
 * Routes to /dashboard/images?school=<moe>, where the image manager handles
 * pin/reorder/delete. Hidden for everyone else.
 */
export default function ManageImagesLink({ moeCode }: ManageImagesLinkProps) {
  const [canManage, setCanManage] = useState(false);

  useEffect(() => {
    fetchMe()
      .then((user) => {
        if (!user) return;
        const isSuper = user.role === "SUPERADMIN";
        const isAdmin = user.admin_school?.moe_code === moeCode;
        if (isSuper || isAdmin) setCanManage(true);
      })
      .catch(() => { /* hide silently on error */ });
  }, [moeCode]);

  if (!canManage) return null;

  return (
    <Link
      href={`/dashboard/images?school=${moeCode}`}
      className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/90 hover:bg-white text-gray-800 text-xs font-medium rounded-lg shadow-sm border border-gray-200"
      title="Manage this school's images — pin hero, reorder, delete"
    >
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
      Manage images
    </Link>
  );
}
