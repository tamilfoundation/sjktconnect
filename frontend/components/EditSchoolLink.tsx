"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchMe } from "@/lib/api";

interface EditSchoolLinkProps {
  moeCode: string;
}

export default function EditSchoolLink({ moeCode }: EditSchoolLinkProps) {
  const [canEdit, setCanEdit] = useState(false);

  useEffect(() => {
    fetchMe().then((user) => {
      if (user && user.school_moe_code === moeCode) {
        setCanEdit(true);
      }
    });
  }, [moeCode]);

  if (!canEdit) return null;

  return (
    <Link
      href={`/school/${moeCode}/edit`}
      className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
      </svg>
      Edit School Data
    </Link>
  );
}
