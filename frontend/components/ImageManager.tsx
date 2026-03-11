"use client";

import { useEffect, useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import {
  fetchSchoolImages,
  reorderSchoolImages,
  deleteSchoolImage,
} from "@/lib/api";
import { SchoolImageData } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function resolveImageUrl(url: string): string {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `${API_URL}${url.startsWith("/") ? "" : "/"}${url}`;
}

const SOURCE_LABELS: Record<string, string> = {
  SATELLITE: "Satellite",
  PLACES: "Places",
  STREET_VIEW: "Street View",
  MANUAL: "Manual",
  COMMUNITY: "Community",
};

interface ImageManagerProps {
  moeCode: string;
}

export default function ImageManager({ moeCode }: ImageManagerProps) {
  const t = useTranslations("suggestions");
  const [images, setImages] = useState<SchoolImageData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [orderChanged, setOrderChanged] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadImages = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchSchoolImages(moeCode);
      setImages(data.sort((a, b) => a.position - b.position));
    } catch {
      setError("Failed to load images.");
    } finally {
      setLoading(false);
    }
  }, [moeCode]);

  useEffect(() => {
    loadImages();
  }, [loadImages]);

  const moveUp = (index: number) => {
    if (index === 0) return;
    const newImages = [...images];
    [newImages[index - 1], newImages[index]] = [
      newImages[index],
      newImages[index - 1],
    ];
    setImages(newImages);
    setOrderChanged(true);
    setSuccessMessage(null);
  };

  const moveDown = (index: number) => {
    if (index === images.length - 1) return;
    const newImages = [...images];
    [newImages[index], newImages[index + 1]] = [
      newImages[index + 1],
      newImages[index],
    ];
    setImages(newImages);
    setOrderChanged(true);
    setSuccessMessage(null);
  };

  const handleSaveOrder = async () => {
    try {
      setSaving(true);
      setError(null);
      const order = images.map((img) => img.id);
      await reorderSchoolImages(moeCode, order);
      setOrderChanged(false);
      setSuccessMessage(t("orderSaved"));
    } catch {
      setError("Failed to save order.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (imageId: number) => {
    if (!window.confirm(t("confirmDelete"))) return;
    try {
      setError(null);
      await deleteSchoolImage(moeCode, imageId);
      setImages((prev) => prev.filter((img) => img.id !== imageId));
      setSuccessMessage(null);
    } catch {
      setError("Failed to delete image.");
    }
  };

  if (loading) {
    return (
      <div className="text-center py-12 text-gray-500">Loading...</div>
    );
  }

  if (error && images.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 mb-4">{error}</p>
        <button
          onClick={loadImages}
          className="text-sm text-primary-600 hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  if (images.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        {t("noImages")}
      </div>
    );
  }

  return (
    <div>
      {/* Header bar */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-600">
          {t("imageCount", { count: images.length })}
        </span>
        {orderChanged && (
          <button
            onClick={handleSaveOrder}
            disabled={saving}
            className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : t("saveOrder")}
          </button>
        )}
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded-lg">
          {error}
        </div>
      )}
      {successMessage && (
        <div className="mb-4 p-3 bg-green-50 text-green-700 text-sm rounded-lg">
          {successMessage}
        </div>
      )}

      {/* Image grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {images.map((image, index) => (
          <div
            key={image.id}
            className="bg-white rounded-xl border border-gray-200 overflow-hidden"
          >
            {/* Image */}
            <div className="aspect-video bg-gray-100 relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={resolveImageUrl(image.image_url)}
                alt={`School image ${index + 1}`}
                className="w-full h-full object-cover"
              />
              {/* Source badge */}
              <span className="absolute top-2 left-2 px-2 py-0.5 bg-black/60 text-white text-xs rounded">
                {SOURCE_LABELS[image.source] || image.source}
              </span>
              {image.is_primary && (
                <span className="absolute top-2 right-2 px-2 py-0.5 bg-primary-600 text-white text-xs rounded">
                  Primary
                </span>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between p-3">
              <div className="flex gap-1">
                <button
                  onClick={() => moveUp(index)}
                  disabled={index === 0}
                  className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded disabled:opacity-30 disabled:cursor-not-allowed"
                  title={t("moveUp")}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
                <button
                  onClick={() => moveDown(index)}
                  disabled={index === images.length - 1}
                  className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded disabled:opacity-30 disabled:cursor-not-allowed"
                  title={t("moveDown")}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>
              <button
                onClick={() => handleDelete(image.id)}
                className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded"
              >
                {t("deleteImage")}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
