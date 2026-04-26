"use client";

import { useEffect, useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import {
  deleteSchoolImage,
  fetchSchoolImages,
  pinSchoolImage,
  reorderSchoolImages,
  updateImageCaption,
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

  const handlePin = async (imageId: number) => {
    try {
      setError(null);
      await pinSchoolImage(moeCode, imageId);
      // Optimistic local update — exactly one image is_primary at a time.
      setImages((prev) =>
        prev.map((img) => ({ ...img, is_primary: img.id === imageId })),
      );
      setSuccessMessage("Hero photo updated.");
    } catch {
      setError("Failed to set hero photo.");
    }
  };

  // Caption editing — one image at a time.
  const [editingCaptionFor, setEditingCaptionFor] = useState<number | null>(null);
  const [captionDraft, setCaptionDraft] = useState("");
  const [captionSaving, setCaptionSaving] = useState(false);

  const startEditCaption = (image: SchoolImageData) => {
    setEditingCaptionFor(image.id);
    setCaptionDraft(image.caption || "");
    setError(null);
    setSuccessMessage(null);
  };

  const cancelEditCaption = () => {
    setEditingCaptionFor(null);
    setCaptionDraft("");
  };

  const saveCaption = async (imageId: number) => {
    setCaptionSaving(true);
    setError(null);
    try {
      const result = await updateImageCaption(moeCode, imageId, captionDraft.slice(0, 200));
      setImages((prev) =>
        prev.map((img) =>
          img.id === imageId ? { ...img, caption: result.caption } : img,
        ),
      );
      setEditingCaptionFor(null);
      setCaptionDraft("");
      setSuccessMessage("Caption saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save caption.");
    } finally {
      setCaptionSaving(false);
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
                <span
                  className="absolute top-2 right-2 px-2 py-0.5 bg-primary-600 text-white text-xs rounded inline-flex items-center gap-1"
                  title="Hero photo"
                >
                  <span aria-hidden>★</span> Hero
                </span>
              )}
            </div>

            {/* Caption row */}
            <div className="px-3 pt-3 pb-1">
              {editingCaptionFor === image.id ? (
                <div className="space-y-2">
                  <textarea
                    value={captionDraft}
                    onChange={(e) => setCaptionDraft(e.target.value.slice(0, 200))}
                    rows={2}
                    placeholder="Add a short caption (max 200 chars)"
                    className="w-full text-xs border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                  <div className="flex items-center gap-2 justify-between">
                    <span className="text-[10px] text-gray-400">
                      {captionDraft.length}/200
                    </span>
                    <div className="flex gap-1">
                      <button
                        onClick={() => saveCaption(image.id)}
                        disabled={captionSaving}
                        className="px-2 py-1 text-xs font-medium text-white bg-primary-600 hover:bg-primary-700 rounded disabled:opacity-50"
                      >
                        {captionSaving ? "Saving…" : "Save"}
                      </button>
                      <button
                        onClick={cancelEditCaption}
                        disabled={captionSaving}
                        className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => startEditCaption(image)}
                  className="w-full text-left text-xs text-gray-600 hover:text-gray-900 italic truncate"
                  title="Click to edit caption"
                >
                  {image.caption || (
                    <span className="text-gray-400 not-italic">+ Add caption</span>
                  )}
                </button>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between p-3 gap-2">
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
              <div className="flex gap-1">
                <button
                  onClick={() => handlePin(image.id)}
                  disabled={image.is_primary}
                  className="px-3 py-1 text-sm text-primary-700 hover:bg-primary-50 rounded disabled:opacity-40 disabled:cursor-not-allowed"
                  title="Make this the school's hero photo"
                >
                  {image.is_primary ? "★ Hero" : "Make hero"}
                </button>
                <button
                  onClick={() => handleDelete(image.id)}
                  className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded"
                >
                  {t("deleteImage")}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
